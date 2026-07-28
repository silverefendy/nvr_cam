"""
ONVIF Camera Discovery Service

Strategi scan berlapis:
  1. WS-Discovery UDP multicast (port 3702) — deteksi kamera yang aktif broadcast
  2. Port scan + ONVIF probe per host — port standar (80, 8000, 8080)
     DAN port Dahua (37777, 37778) untuk kamera/NVR Dahua
  3. Cek port RTSP 554 terbuka sebagai indikator tambahan

UDP multicast dijalankan di thread pool (run_in_executor) agar tidak
memblokir event loop — ini penting karena recvfrom() bersifat blocking.

Dahua port notes:
  - 37777 = Dahua SDK/proprietary protocol (NVR to camera)
  - 37778 = Dahua RTSP alternatif
  Kita probe ONVIF HTTP di port 80 meski RTSP-nya di 37778.
  Port 37777/37778 dipakai untuk deteksi keberadaan device Dahua saja.

Docker/Windows note:
  Di Docker Desktop (Windows), network_mode: host tidak efektif.
  Subnet lokal dideteksi via host.docker.internal (extra_hosts di compose)
  agar scan diarahkan ke LAN fisik, bukan Docker bridge (172.x.x.x).
"""

import asyncio
import socket
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from ipaddress import ip_network
import aiohttp
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Thread pool khusus untuk operasi UDP blocking
_UDP_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ws-disc")

# Port ONVIF standar
ONVIF_HTTP_PORTS = [80, 8000, 8080]

# Port Dahua SDK/RTSP alternatif — dipakai untuk deteksi, bukan ONVIF probe
DAHUA_DETECT_PORTS = [37777, 37778]

# Semua port yang di-scan untuk keberadaan device
ALL_SCAN_PORTS = ONVIF_HTTP_PORTS + DAHUA_DETECT_PORTS

# Hostname Docker untuk akses host machine (dikonfigurasi via extra_hosts di compose)
DOCKER_HOST_ALIAS = "host.docker.internal"


@dataclass
class DiscoveredCamera:
    ip: str
    port: int
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    onvif_url: Optional[str] = None
    mac_address: Optional[str] = None
    onvif_support: bool = False
    dahua_sdk: bool = False          # True jika terdeteksi via port 37777/37778
    suggested_rtsp_main: Optional[str] = None
    suggested_rtsp_sub: Optional[str] = None


class ONVIFScanner:
    DISCOVERY_MULTICAST = "239.255.255.250"
    DISCOVERY_PORT = 3702

    # WS-Discovery probe — mencari NetworkVideoTransmitter (kamera ONVIF)
    PROBE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">
  <s:Header>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
    <wsa:MessageID>urn:uuid:{uuid}</wsa:MessageID>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
  </s:Header>
  <s:Body>
    <d:Probe>
      <d:Types xmlns:dn="http://www.onvif.org/ver10/network/wsdl">dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </s:Body>
</s:Envelope>"""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def scan_network(
        self,
        network: Optional[str] = None,
        ports: List[int] = None,
    ) -> List[DiscoveredCamera]:
        if ports is None:
            ports = ALL_SCAN_PORTS  # include Dahua ports

        cameras: Dict[str, DiscoveredCamera] = {}

        # --- Langkah 1: WS-Discovery multicast (di thread pool agar tidak block) ---
        try:
            discovered = await asyncio.get_event_loop().run_in_executor(
                _UDP_EXECUTOR,
                self._ws_discovery_blocking,
            )
            for cam in discovered:
                cameras[cam.ip] = cam
            logger.info(f"WS-Discovery multicast: {len(discovered)} kamera ditemukan")
        except Exception as e:
            logger.warning(f"WS-Discovery gagal: {e}")

        # --- Langkah 2: Port scan + ONVIF/Dahua probe ---
        if network is None:
            network = self._get_local_subnet()

        if network:
            logger.info(f"Port scan {network} di port {ports}")
            scanned = await self._port_scan(network, ports)
            for cam in scanned:
                if cam.ip not in cameras:
                    cameras[cam.ip] = cam
                else:
                    # Merge: tambahkan info yang belum ada
                    existing = cameras[cam.ip]
                    if not existing.manufacturer and cam.manufacturer:
                        existing.manufacturer = cam.manufacturer
                    if not existing.model and cam.model:
                        existing.model = cam.model
                    if not existing.onvif_url and cam.onvif_url:
                        existing.onvif_url = cam.onvif_url
                    if not existing.rtsp_url and cam.rtsp_url:
                        existing.rtsp_url = cam.rtsp_url
                    if cam.dahua_sdk:
                        existing.dahua_sdk = True
                    if cam.suggested_rtsp_main:
                        existing.suggested_rtsp_main = cam.suggested_rtsp_main
                    if cam.suggested_rtsp_sub:
                        existing.suggested_rtsp_sub = cam.suggested_rtsp_sub

        logger.info(f"Total kamera unik ditemukan: {len(cameras)}")
        return list(cameras.values())

    # ─────────────────────────────────────────────────────────────────────────
    # WS-Discovery (blocking — dijalankan di executor)
    # ─────────────────────────────────────────────────────────────────────────

    def _ws_discovery_blocking(self) -> List[DiscoveredCamera]:
        """
        Kirim WS-Discovery probe ke multicast dan tunggu respons.
        Bersifat blocking — harus dipanggil via run_in_executor.
        """
        cameras: List[DiscoveredCamera] = []
        message = self.PROBE_TEMPLATE.format(uuid=str(uuid.uuid4()))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
        sock.settimeout(self.timeout)

        try:
            sock.sendto(message.encode(), (self.DISCOVERY_MULTICAST, self.DISCOVERY_PORT))
            while True:
                try:
                    data, (src_ip, _) = sock.recvfrom(65535)
                    cam = self._parse_probe_match(data, src_ip)
                    if cam and not any(c.ip == cam.ip for c in cameras):
                        cameras.append(cam)
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"WS-Discovery recvfrom error: {e}")
        except Exception as e:
            logger.warning(f"WS-Discovery socket error: {e}")
        finally:
            sock.close()

        return cameras

    def _parse_probe_match(self, data: bytes, src_ip: str) -> Optional[DiscoveredCamera]:
        """Parse XML respons WS-Discovery ProbeMatch."""
        try:
            root = ET.fromstring(data)
            ns = {
                's': 'http://www.w3.org/2003/05/soap-envelope',
                'd': 'http://schemas.xmlsoap.org/ws/2005/04/discovery',
            }
            match = root.find('.//d:ProbeMatch', ns)
            if match is None:
                return None

            xaddrs_el = match.find('d:XAddrs', ns)
            xaddrs = xaddrs_el.text.strip() if xaddrs_el is not None and xaddrs_el.text else None

            port = 80
            onvif_url = None
            if xaddrs:
                first_xaddr = xaddrs.split()[0]
                onvif_url = first_xaddr
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(first_xaddr)
                    if parsed.port:
                        port = parsed.port
                except Exception:
                    pass

            return DiscoveredCamera(
                ip=src_ip,
                port=port,
                onvif_url=onvif_url,
                onvif_support=True,
            )
        except ET.ParseError as e:
            logger.debug(f"WS-Discovery XML parse error dari {src_ip}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Port scan + ONVIF/Dahua probe
    # ─────────────────────────────────────────────────────────────────────────

    async def _port_scan(self, network: str, ports: List[int]) -> List[DiscoveredCamera]:
        """Scan semua host di network, cek port secara paralel."""
        net = ip_network(network, strict=False)
        hosts = list(net.hosts())
        if len(hosts) > 254:
            hosts = hosts[:254]

        semaphore = asyncio.Semaphore(50)

        async def _probe_host(ip_str):
            """Probe satu host: cek ONVIF ports dulu, lalu Dahua ports."""
            async with semaphore:
                # Cek ONVIF port standar
                for port in ONVIF_HTTP_PORTS:
                    result = await self._probe_onvif(ip_str, port)
                    if result:
                        return result

                # Cek Dahua SDK/RTSP port
                for port in DAHUA_DETECT_PORTS:
                    if await self._check_tcp_port(ip_str, port, timeout=1.5):
                        return self._build_dahua_camera(ip_str, port)

                return None

        tasks = [_probe_host(str(host)) for host in hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        cameras = []
        seen_ips = set()
        for r in results:
            if isinstance(r, DiscoveredCamera) and r.ip not in seen_ips:
                cameras.append(r)
                seen_ips.add(r.ip)
        return cameras

    async def _check_tcp_port(self, ip: str, port: int, timeout: float = 1.5) -> bool:
        """Cek apakah TCP port terbuka."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _build_dahua_camera(self, ip: str, detected_port: int) -> DiscoveredCamera:
        """
        Bangun DiscoveredCamera untuk device Dahua yang terdeteksi via
        port 37777 atau 37778.

        Dahua NVR/kamera dengan port 37777 (SDK) atau 37778 (RTSP alt):
        - ONVIF tetap di port 80
        - RTSP main: port 554 (standar) atau 37778 (alt)
        - Format URL Dahua: rtsp://user:pass@IP:554/cam/realmonitor?channel=1&subtype=0
        """
        is_sdk_port = detected_port == 37777
        rtsp_port = 554 if is_sdk_port else detected_port  # 37778 bisa langsung jadi RTSP

        suggested_main = f"rtsp://admin:@{ip}:{rtsp_port}/cam/realmonitor?channel=1&subtype=0"
        suggested_sub  = f"rtsp://admin:@{ip}:{rtsp_port}/cam/realmonitor?channel=1&subtype=1"

        return DiscoveredCamera(
            ip=ip,
            port=detected_port,
            manufacturer="Dahua",
            onvif_support=True,   # Dahua punya ONVIF di port 80
            dahua_sdk=True,
            rtsp_url=suggested_main,
            suggested_rtsp_main=suggested_main,
            suggested_rtsp_sub=suggested_sub,
        )

    async def _probe_onvif(self, ip: str, port: int) -> Optional[DiscoveredCamera]:
        """
        Cek apakah host:port punya ONVIF device service.
        Coba beberapa path umum yang dipakai kamera Dahua/Hikvision.
        """
        paths = [
            "/onvif/device_service",
            "/onvif/Device",
            "/onvif/device",
            "/device_service",
        ]

        timeout = aiohttp.ClientTimeout(connect=1.5, total=3)
        for path in paths:
            url = f"http://{ip}:{port}{path}"
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status in (200, 400, 401, 405):
                            info = await self._get_device_info(ip, port, path)
                            return info or DiscoveredCamera(
                                ip=ip, port=port,
                                onvif_url=url,
                                onvif_support=True,
                            )
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                break
            except Exception:
                continue
        return None

    async def _get_device_info(self, ip: str, port: int, path: str) -> Optional[DiscoveredCamera]:
        """
        Kirim GetDeviceInformation tanpa auth (anonim) ke ONVIF service.
        Banyak kamera Dahua mengembalikan info dasar tanpa autentikasi.
        """
        soap_body = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <tds:GetDeviceInformation xmlns:tds="http://www.onvif.org/ver10/device/wsdl"/>
  </s:Body>
</s:Envelope>"""
        url = f"http://{ip}:{port}{path}"
        timeout = aiohttp.ClientTimeout(total=3)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    data=soap_body,
                    headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                ) as resp:
                    if resp.status in (200, 400, 401):
                        body = await resp.text()
                        if resp.status == 200:
                            return self._parse_device_info_xml(ip, port, url, body)
                        return DiscoveredCamera(
                            ip=ip, port=port,
                            onvif_url=url,
                            onvif_support=True,
                        )
        except Exception as e:
            logger.debug(f"GetDeviceInformation gagal {ip}:{port}: {e}")
        return None

    def _parse_device_info_xml(self, ip: str, port: int, onvif_url: str, xml_text: str) -> DiscoveredCamera:
        """Parse respons GetDeviceInformation SOAP."""
        cam = DiscoveredCamera(ip=ip, port=port, onvif_url=onvif_url, onvif_support=True)
        try:
            root = ET.fromstring(xml_text)
            for el in root.iter():
                tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
                if tag == 'Manufacturer' and el.text:
                    cam.manufacturer = el.text.strip()
                elif tag == 'Model' and el.text:
                    cam.model = el.text.strip()
        except Exception as e:
            logger.debug(f"Parse DeviceInfo XML error: {e}")
        return cam

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_host_ip_via_docker_alias(self) -> Optional[str]:
        """
        Resolve IP host machine via host.docker.internal.
        Hanya bekerja jika extra_hosts dikonfigurasi di docker-compose.yml.
        Ini adalah cara yang reliable untuk mendapat IP host dari dalam container Docker.
        """
        try:
            host_ip = socket.gethostbyname(DOCKER_HOST_ALIAS)
            # Validasi: bukan loopback dan bukan Docker bridge
            if not host_ip.startswith('127.') and not host_ip.startswith('172.'):
                logger.info(f"Subnet terdeteksi via {DOCKER_HOST_ALIAS}: {host_ip}")
                return host_ip
        except Exception as e:
            logger.debug(f"Gagal resolve {DOCKER_HOST_ALIAS}: {e}")
        return None

    def _get_local_subnet(self) -> Optional[str]:
        """
        Deteksi subnet lokal dengan prioritas:
        1. host.docker.internal — IP host machine (paling akurat di Docker)
        2. netifaces — scan semua interface, skip Docker bridge (172.x)
        3. Routing trick — fallback terakhir

        Di Docker Desktop (Windows/Mac), container berjalan di bridge network
        (172.x.x.x). Kita butuh IP host (10.x atau 192.168.x) agar scan
        diarahkan ke subnet yang berisi kamera fisik.
        """
        # Prioritas 1: host.docker.internal (paling akurat di Docker)
        host_ip = self._get_host_ip_via_docker_alias()
        if host_ip:
            subnet = f"{host_ip.rsplit('.', 1)[0]}.0/24"
            logger.info(f"Menggunakan subnet dari host.docker.internal: {subnet}")
            return subnet

        # Prioritas 2: netifaces (scan interface, skip Docker bridge)
        candidates = []
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
                for addr in addrs:
                    ip = addr.get('addr', '')
                    netmask = addr.get('netmask', '255.255.255.0')
                    # Skip loopback dan Docker bridge
                    if ip.startswith('127.') or ip.startswith('172.'):
                        continue
                    candidates.append((ip, netmask))
        except ImportError:
            logger.debug("netifaces tidak tersedia, skip")

        if candidates:
            ip, _ = candidates[0]
            subnet = f"{ip.rsplit('.', 1)[0]}.0/24"
            logger.info(f"Menggunakan subnet dari netifaces: {subnet}")
            return subnet

        # Prioritas 3: routing trick fallback
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            if not local_ip.startswith('172.') and not local_ip.startswith('127.'):
                subnet = f"{local_ip.rsplit('.', 1)[0]}.0/24"
                logger.info(f"Menggunakan subnet dari routing trick: {subnet}")
                return subnet
            else:
                logger.warning(
                    f"IP lokal {local_ip} terdeteksi sebagai Docker bridge atau loopback. "
                    "Tidak bisa otomatis deteksi subnet kamera. "
                    "Isi field 'Network CIDR' secara manual di UI."
                )
        except Exception as e:
            logger.warning(f"Gagal deteksi subnet lokal: {e}")

        return None


# ─────────────────────────────────────────────────────────────────────────────
# Convenience function — dipanggil dari router
# ─────────────────────────────────────────────────────────────────────────────

async def discover_cameras(
    network: Optional[str] = None,
    timeout: float = 5.0,
) -> List[Dict[str, Any]]:
    scanner = ONVIFScanner(timeout=timeout)
    cameras = await scanner.scan_network(network=network)
    return [
        {
            "ip": cam.ip,
            "port": cam.port,
            "manufacturer": cam.manufacturer,
            "model": cam.model,
            "name": cam.name,
            "rtsp_url": cam.rtsp_url,
            "onvif_url": cam.onvif_url,
            "mac_address": cam.mac_address,
            "onvif_support": cam.onvif_support,
            "dahua_sdk": cam.dahua_sdk,
            "suggested_rtsp_main": cam.suggested_rtsp_main,
            "suggested_rtsp_sub": cam.suggested_rtsp_sub,
        }
        for cam in cameras
    ]
