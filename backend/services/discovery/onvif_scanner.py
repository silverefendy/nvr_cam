"""
ONVIF Camera Discovery Service

Strategi scan berlapis:
  1. WS-Discovery UDP multicast (port 3702) — deteksi kamera yang aktif broadcast
  2. Port scan + ONVIF probe per host (port 80, 8000, 8080) — untuk kamera Dahua
     yang tidak respond multicast tapi punya ONVIF service di port HTTP biasa
  3. Cek port RTSP 554 terbuka sebagai indikator tambahan

UDP multicast dijalankan di thread pool (run_in_executor) agar tidak
memblokir event loop — ini penting karena recvfrom() bersifat blocking.
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
            ports = [80, 8000, 8080]

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

        # --- Langkah 2: Port scan + ONVIF probe ---
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

            # Ambil port dari XAddrs jika ada (e.g. http://192.168.1.10:8080/onvif/device_service)
            port = 80
            onvif_url = None
            if xaddrs:
                # Pakai URL pertama jika ada beberapa (spasi-delimited)
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
    # Port scan + ONVIF probe
    # ─────────────────────────────────────────────────────────────────────────

    async def _port_scan(self, network: str, ports: List[int]) -> List[DiscoveredCamera]:
        """Scan semua host di network, cek port ONVIF secara paralel."""
        net = ip_network(network, strict=False)
        hosts = list(net.hosts())
        # Batasi ke 254 host (1 subnet /24)
        if len(hosts) > 254:
            hosts = hosts[:254]

        # Batasi konkurensi agar tidak flood network
        semaphore = asyncio.Semaphore(50)

        async def _probe_with_sem(ip, port):
            async with semaphore:
                return await self._probe_onvif(str(ip), port)

        tasks = [
            _probe_with_sem(host, port)
            for host in hosts
            for port in ports
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        cameras = []
        seen_ips = set()
        for r in results:
            if isinstance(r, DiscoveredCamera) and r.ip not in seen_ips:
                cameras.append(r)
                seen_ips.add(r.ip)
        return cameras

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
                    # ONVIF: GET akan mengembalikan 400/405 tapi host ada; POST tanpa auth = 401/400
                    async with session.get(url) as resp:
                        if resp.status in (200, 400, 401, 405):
                            # Port open + path ada → coba GetDeviceInformation
                            info = await self._get_device_info(ip, port, path)
                            return info or DiscoveredCamera(
                                ip=ip, port=port,
                                onvif_url=url,
                                onvif_support=True,
                            )
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                # Port closed atau timeout — stop coba path lain di port ini
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
                        # 401 = kamera ada tapi butuh auth
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
            # Cari tag tanpa namespace prefix untuk kompatibilitas
            for el in root.iter():
                tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
                if tag == 'Manufacturer' and el.text:
                    cam.manufacturer = el.text.strip()
                elif tag == 'Model' and el.text:
                    cam.model = el.text.strip()
                elif tag == 'FirmwareVersion' and el.text:
                    pass  # bisa disimpan nanti jika perlu
        except Exception as e:
            logger.debug(f"Parse DeviceInfo XML error: {e}")
        return cam

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_local_subnet(self) -> Optional[str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return f"{local_ip.rsplit('.', 1)[0]}.0/24"
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
        }
        for cam in cameras
    ]
