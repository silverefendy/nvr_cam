"""
ONVIF Camera Discovery Service

Scans the local network for ONVIF-compatible IP cameras.
Uses ONVIF protocol discovery to find cameras and retrieve their capabilities.
"""

import asyncio
import socket
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from ipaddress import ip_network, IPv4Network
import aiohttp
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredCamera:
    """Represents a discovered ONVIF camera."""
    ip: str
    port: int
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    onvif_url: Optional[str] = None
    mac_address: Optional[str] = None


class ONVIFScanner:
    """
    Scanner for discovering ONVIF cameras on the local network.
    
    Uses WS-Discovery protocol to find ONVIF devices.
    """
    
    # ONVIF discovery multicast address and port
    DISCOVERY_MULTICAST = "239.255.255.250"
    DISCOVERY_PORT = 3702
    
    # WS-Discovery probe message
    PROBE_MESSAGE = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Header xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
        <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
        <wsa:MessageID>urn:uuid:{uuid}</wsa:MessageID>
        <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    </s:Header>
    <s:Body>
        <Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
            <Types xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">d:NetworkVideoTransmitter</Types>
    </Probe>
    </s:Body>
</s:Envelope>"""
    
    def __init__(self, timeout: float = 5.0):
        """
        Initialize the ONVIF scanner.
        
        Args:
            timeout: Discovery timeout in seconds
        """
        self.timeout = timeout
    
    async def scan_network(
        self,
        network: Optional[str] = None,
        ports: List[int] = None
    ) -> List[DiscoveredCamera]:
        """
        Scan the network for ONVIF cameras.
        
        Args:
            network: Network CIDR (e.g., "192.168.1.0/24"). If None, uses local subnet.
            ports: List of ports to scan. If None, uses common ONVIF ports.
        
        Returns:
            List of discovered cameras
        """
        if ports is None:
            ports = [80, 8000, 8080, 554, 8554]
        
        cameras = []
        
        # Try WS-Discovery first (multicast)
        try:
            discovered = await self._ws_discovery()
            cameras.extend(discovered)
            logger.info(f"WS-Discovery found {len(discovered)} cameras")
        except Exception as e:
            logger.warning(f"WS-Discovery failed: {e}")
        
        # Fall back to port scanning if no cameras found or network specified
        if not cameras or network:
            if network is None:
                network = self._get_local_subnet()
            
            if network:
                logger.info(f"Scanning network {network} on ports {ports}")
                scanned = await self._port_scan(network, ports)
                cameras.extend(scanned)
        
        # Deduplicate cameras by IP
        unique_cameras = {}
        for cam in cameras:
            if cam.ip not in unique_cameras:
                unique_cameras[cam.ip] = cam
            else:
                # Merge information if we have more details
                existing = unique_cameras[cam.ip]
                if not existing.manufacturer and cam.manufacturer:
                    existing.manufacturer = cam.manufacturer
                if not existing.model and cam.model:
                    existing.model = cam.model
                if not existing.rtsp_url and cam.rtsp_url:
                    existing.rtsp_url = cam.rtsp_url
        
        return list(unique_cameras.values())
    
    async def _ws_discovery(self) -> List[DiscoveredCamera]:
        """
        Perform WS-Discovery multicast probe.
        
        Returns:
            List of discovered cameras
        """
        cameras = []
        uuid = self._generate_uuid()
        message = self.PROBE_MESSAGE.format(uuid=uuid)
        
        # Create UDP socket for multicast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
        try:
            # Send probe to multicast address
            sock.sendto(message.encode(), (self.DISCOVERY_MULTICAST, self.DISCOVERY_PORT))
            
            # Listen for responses
            sock.settimeout(self.timeout)
            
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    camera = self._parse_discovery_response(data, addr[0])
                    if camera:
                        cameras.append(camera)
                except socket.timeout:
                    break
        finally:
            sock.close()
        
        return cameras
    
    async def _port_scan(self, network: str, ports: List[int]) -> List[DiscoveredCamera]:
        """
        Scan network ports for potential ONVIF cameras.
        
        Args:
            network: Network CIDR
            ports: List of ports to scan
        
        Returns:
            List of discovered cameras
        """
        cameras = []
        net = ip_network(network, strict=False)
        
        # Limit scan to reasonable number of hosts
        hosts = list(net.hosts())
        if len(hosts) > 256:
            hosts = hosts[:256]
        
        tasks = []
        for host in hosts:
            for port in ports:
                tasks.append(self._check_onvif_endpoint(str(host), port))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, DiscoveredCamera):
                cameras.append(result)
        
        return cameras
    
    async def _check_onvif_endpoint(self, ip: str, port: int) -> Optional[DiscoveredCamera]:
        """
        Check if a host:port has an ONVIF service.
        
        Args:
            ip: IP address
            port: Port number
        
        Returns:
            DiscoveredCamera if ONVIF service found, None otherwise
        """
        common_paths = [
            "/onvif/device_service",
            "/onvif/device",
            "/device_service",
            "/onvif/Device",
        ]
        
        for path in common_paths:
            url = f"http://{ip}:{port}{path}"
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            # Try to get device info via GetDeviceInformation
                            camera = await self._get_device_info(url)
                            if camera:
                                camera.ip = ip
                                camera.port = port
                                return camera
            except Exception:
                continue
        
        return None
    
    async def _get_device_info(self, onvif_url: str) -> Optional[DiscoveredCamera]:
        """
        Get device information from ONVIF service.
        
        Args:
            onvif_url: ONVIF service URL
        
        Returns:
            DiscoveredCamera with device info
        """
        # GetDeviceInformation SOAP request
        get_device_info = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Body>
        <td:GetDeviceInformation xmlns:td="http://www.onvif.org/ver10/device/wsdl"/>
    </s:Body>
</s:Envelope>"""
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                async with session.post(
                    onvif_url,
                    data=get_device_info,
                    headers={"Content-Type": "application/soap+xml"}
                ) as response:
                    if response.status == 200:
                        xml = await response.text()
                        return self._parse_device_info(xml, onvif_url)
        except Exception as e:
            logger.debug(f"Failed to get device info from {onvif_url}: {e}")
        
        return None
    
    def _parse_device_info(self, xml: str, onvif_url: str) -> Optional[DiscoveredCamera]:
        """
        Parse GetDeviceInformation response.
        
        Args:
            xml: XML response
            onvif_url: ONVIF service URL
        
        Returns:
            DiscoveredCamera with parsed info
        """
        try:
            root = ET.fromstring(xml)
            namespaces = {
                'td': 'http://www.onvif.org/ver10/device/wsdl',
                's': 'http://www.w3.org/2003/05/soap-envelope'
            }
            
            manufacturer = root.findtext('.//td:Manufacturer', namespaces=namespaces)
            model = root.findtext('.//td:Model', namespaces=namespaces)
            name = root.findtext('.//td:Name', namespaces=namespaces)
            
            camera = DiscoveredCamera(
                ip="",  # Will be set by caller
                port=0,  # Will be set by caller
                manufacturer=manufacturer,
                model=model,
                name=name,
                onvif_url=onvif_url
            )
            
            return camera
        except Exception as e:
            logger.debug(f"Failed to parse device info: {e}")
            return None
    
    def _parse_discovery_response(self, data: bytes, source_ip: str) -> Optional[DiscoveredCamera]:
        """
        Parse WS-Discovery response.
        
        Args:
            data: Response data
            source_ip: Source IP address
        
        Returns:
            DiscoveredCamera if valid response
        """
        try:
            root = ET.fromstring(data)
            namespaces = {
                's': 'http://www.w3.org/2003/05/soap-envelope',
                'd': 'http://schemas.xmlsoap.org/ws/2005/04/discovery',
                'wsa': 'http://schemas.xmlsoap.org/ws/2004/08/addressing',
                'dn': 'http://www.onvif.org/ver10/network/wsdl'
            }
            
            # Check if this is a ProbeMatch response
            if root.find('.//d:ProbeMatch', namespaces) is None:
                return None
            
            # Extract XAddrs (endpoint addresses)
            xaddrs = root.findtext('.//d:XAddrs', namespaces)
            if xaddrs:
                # Parse the ONVIF service URL
                camera = DiscoveredCamera(
                    ip=source_ip,
                    port=0,
                    onvif_url=xaddrs.strip()
                )
                return camera
        except Exception as e:
            logger.debug(f"Failed to parse discovery response: {e}")
        
        return None
    
    def _get_local_subnet(self) -> Optional[str]:
        """
        Get the local subnet CIDR.
        
        Returns:
            Network CIDR string or None
        """
        try:
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Assume /24 subnet
            return f"{local_ip.rsplit('.', 1)[0]}.0/24"
        except Exception as e:
            logger.warning(f"Failed to get local subnet: {e}")
            return None
    
    def _generate_uuid(self) -> str:
        """Generate a random UUID string."""
        import uuid
        return str(uuid.uuid4())


async def discover_cameras(network: Optional[str] = None, timeout: float = 5.0) -> List[Dict[str, Any]]:
    """
    Convenience function to discover cameras.
    
    Args:
        network: Network CIDR to scan
        timeout: Discovery timeout in seconds
    
    Returns:
        List of camera dictionaries
    """
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
        }
        for cam in cameras
    ]
