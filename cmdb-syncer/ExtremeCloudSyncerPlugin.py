#!/usr/bin/env python3
"""
ExtremeCloudIQ Syncer Plugin for CMDBSyncer

This plugin integrates with the ExtremeCloudIQ API to synchronize device data into the CMDBSyncer inventory.
It supports authentication via username/password to obtain a 24-hour valid Bearer token and fetches devices
with pagination. Interface synchronization is included as a commented placeholder, pending a specific API endpoint.
"""
import requests
import json
import time
import datetime
from typing import Dict, List, Optional
from application import app, logger
from application.models.host import Host
from application.modules.debug import ColorCodes
from .base import BaseAccount, BaseObject, BasePlugin

class ExtremeCloudAccount(BaseAccount):
    """
    Account class for ExtremeCloudIQ API configuration and authentication
    """
    def __init__(self, account: dict):
        super().__init__(account)
        self.api_url = account.get('api_url', 'https://api.extremecloudiq.com')
        self.username = account.get('username')
        self.password = account.get('password')
        self.verify_ssl = not app.config.get('DISABLE_SSL_ERRORS', False)
        self._auth_token = None
        self._token_expiry = 0  # Timestamp when token expires

    def get_auth_token(self) -> str:
        """
        Fetch authentication token from ExtremeCloudIQ API using username/password.
        Caches the token for 24 hours with a 60-second buffer before expiry.

        Returns:
            str: The Bearer token for API authentication.

        Raises:
            Exception: If the token cannot be retrieved or the response is invalid.
        """
        current_time = time.time()
        if self._auth_token and self._token_expiry > current_time + 60:
            logger.debug(f"{ColorCodes.OKGREEN}Using cached ExtremeCloud Auth Token{ColorCodes.ENDC}")
            return self._auth_token

        logger.info(f"{ColorCodes.OKGREEN}Requesting new ExtremeCloud Auth Token{ColorCodes.ENDC}")
        url = f"{self.api_url}{ExtremeCloudAPI._API_PATH_LOGIN}"
        headers = {'Content-Type': 'application/json'}
        payload = {"username": self.username, "password": self.password}

        try:
            response = requests.post(url, headers=headers, json=payload, verify=self.verify_ssl, timeout=30)
            response.raise_for_status()
            response_json = response.json()
            token = response_json.get('access_token')
            if not token:
                raise Exception(f"Auth Token (access_token) not found in response: {response_json}")

            self._auth_token =所在的
            self._token_expiry = current_time + 24 * 3600  # Token valid for 24 hours
            return token

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ExtremeCloud Auth Token: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'No response'}")
            raise Exception(f"Connection Problem or Authentication Failed: {e}") from e

    def _make_headers(self) -> Dict[str, str]:
        """Create headers with Bearer token for API requests."""
        return {
            'Authorization': f'Bearer {self.get_auth_token()}',
            'Content-Type': 'application/json'
        }

    def _make_api_request(self, method: str, path: str, params: Optional[Dict] = None,
                          json_data: Optional[Dict] = None, max_retries: int = 2) -> requests.Response:
        """
        Make an API request to ExtremeCloudIQ, handling token renewal on 401 errors and rate-limiting.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST').
            path (str): API endpoint path (e.g., '/devices').
            params (Optional[Dict]): Query parameters for the request.
            json_data (Optional[Dict]): JSON data for the request body.
            max_retries (int): Number of retries for 401 or 429 errors.

        Returns:
            requests.Response: The response object from the API call.

        Raises:
            requests.exceptions.RequestException: If the API request fails after retries.
            Exception: For unexpected errors during request or token handling.
        """
        url = f"{self.api_url}{path}"
        
        for attempt in range(max_retries + 1):
            headers = self._make_headers()
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    verify=self.verify_ssl,
                    timeout=60
                )

                if response.status_code == 401 and attempt < max_retries:
                    logger.info(f"{ColorCodes.WARNING}Received 401, renewing token (attempt {attempt+1}/{max_retries+1}){ColorCodes.ENDC}")
                    self._auth_token = None  # Force token refresh
                    continue
                elif response.status_code == 429 and attempt < max_retries:
                    logger.warning(f"Rate limit (429) hit, retrying after delay (attempt {attempt+1}/{max_retries+1})")
                    time.sleep(2 ** attempt * 5)  # Exponential backoff: 5s, 10s, 20s
                    continue
                
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                logger.error(f"API request to {path} failed (attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt * 5)  # Exponential backoff
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error in API request to {path}: {e}")
                raise

class ExtremeCloudDevice(BaseObject):
    """
    Device object for ExtremeCloudIQ devices
    """
    def __init__(self, account: ExtremeCloudAccount, data: dict):
        super().__init__(account, data)
        self.hostname = data.get('hostname', '')
        self.ip = data.get('ip_address', '')
        self.mac = ExtremeCloudAPI._format_mac_address(data.get('mac_address', ''))
        self.serial = data.get('serial_number', '')
        self.device_type = data.get('product_type', '')
        self.location = self._format_location(data.get('locations', []))
        self.status = 'up' if data.get('connected', False) else 'down'
        self.uptime = ExtremeCloudAPI._calculate_uptime(data.get('system_up_time'))
        self.sync_id = str(data.get('id', ''))

    @staticmethod
    def _format_location(locations: List[Dict]) -> str:
        """Extract the first location name from the locations list."""
        if locations and isinstance(locations, list) and len(locations) > 0:
            return locations[0].get('name', '')
        return ''

    def get_identifier(self) -> str:
        """Return unique identifier for the device (serial or hostname)."""
        return self.serial or self.hostname

    def as_dict(self) -> Dict:
        """Return device data as dictionary for CMDBSyncer inventory."""
        inventory = {
            'hostname': self.hostname,
            'ip': self.ip,
            'mac': self.mac,
            'serial': self.serial,
            'device_type': self.device_type,
            'location': self.location,
            'status': self.status,
            'uptime': self.uptime,
            'manufacturer': 'extreme_networks'
        }
        for attr in [
            'create_time', 'update_time', 'org_id', 'service_tag',
            'device_function', 'software_version', 'device_admin_state',
            'last_connect_time', 'network_policy_name', 'primary_ntp_server_address',
            'primary_dns_server_address', 'subnet_mask', 'default_gateway',
            'ipv6_address', 'ipv6_netmask', 'simulated', 'display_version',
            'active_clients', 'location_id', 'country_code', 'description',
            'config_mismatch', 'managed_by', 'thread0_eui64', 'thread0_ext_mac',
            'mgt_vlan', 'visible'
        ]:
            if attr in self.data:
                inventory[f'{ExtremeCloudAPI._INVENTORY_PREFIX}{attr}'] = self.data[attr]
        return inventory

class ExtremeCloudAPI(BasePlugin):
    """
    Plugin class for ExtremeCloudIQ integration with CMDBSyncer
    """
    # Constants for API paths and inventory prefix
    _INVENTORY_PREFIX = 'extremecloud_'
    _API_PATH_LOGIN = '/login'
    _API_PATH_DEVICES = '/devices'
    _API_PATH_INTERFACES_BASE = '/devices/'  # Base path for potential interface endpoint

    def __init__(self):
        super().__init__()
        self.name = 'extremecloud'
        self.account_class = ExtremeCloudAccount
        self.object_class = ExtremeCloudDevice

    @staticmethod
    def _format_mac_address(mac: str) -> str:
        """Format a MAC address from a 12-character string to XX:XX:XX:XX:XX:XX."""
        if mac and len(mac) == 12:
            return ':'.join(mac[i:i+2] for i in range(0, len(mac), 2)).upper()
        return mac.upper() if mac else ''

    @staticmethod
    def _calculate_uptime(timestamp_ms: Optional[float]) -> Optional[str]:
        """
        Calculate uptime from a timestamp (in milliseconds) to a string
        in the format 'X days, HH:MM:SS' or None/error string on failure.
        """
        if not isinstance(timestamp_ms, (int, float)):
            return None
        try:
            current_time_ms = int(time.time() * 1000)
            uptime_ms = current_time_ms - int(timestamp_ms)
            if uptime_ms < 0:
                return "Timestamp is in the future"
            uptime_delta = datetime.timedelta(milliseconds=uptime_ms)
            days = uptime_delta.days
            if days > 2000:
                return "offline"
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{days} days, {hours:02}:{minutes:02}:{seconds:02}"
        except OverflowError:
            return "Uptime too large for timedelta"
        except TypeError:
            return None

    def fetch_objects(self, account: ExtremeCloudAccount) -> List[ExtremeCloudDevice]:
        """
        Fetch devices from ExtremeCloudIQ API with pagination.
        """
        logger.info(f"{ColorCodes.OKGREEN}Starting ExtremeCloudIQ Device Sync{ColorCodes.ENDC}")
        page = 0
        page_size = 100
        all_devices = []
        total_fetched = 0

        while True:
            try:
                params = {'page': page, 'limit': page_size}
                response = account._make_api_request('GET', self._API_PATH_DEVICES, params=params)
                data = response.json()
                devices = data.get('data', [])
                
                if not isinstance(devices, list):
                    logger.warning(f"Expected a list of devices, got: {type(devices)}. Response: {data}")
                    break

                if not devices:
                    logger.info(f"No devices found on page {page}, stopping pagination")
                    break

                all_devices.extend([ExtremeCloudDevice(account, device) for device in devices])
                total_fetched += len(devices)
                logger.info(f"Fetched {len(devices)} devices on page {page} (Total: {total_fetched})")

                if len(devices) < page_size:
                    break

                page += 1
                time.sleep(3)  # Avoid overwhelming the API

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching devices (page {page}): {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing devices (page {page}): {e}")
                break

        logger.info(f"Finished fetching {total_fetched} ExtremeCloudIQ devices")
        return all_devices

    def inventorize(self, account: ExtremeCloudAccount, rewrite_config: Optional[Dict] = None) -> List[Dict]:
        """
        Synchronize devices to CMDBSyncer inventory.
        """
        devices = self.fetch_objects(account)
        results = []
        
        for device in devices:
            hostname = device.hostname
            if not hostname:
                logger.warning(f"Skipping device without hostname: {device.data}")
                continue

            logger.info(f"{ColorCodes.HEADER}Processing device: {hostname}{ColorCodes.ENDC}")
            db_host = Host.get_host(hostname)
            inventory = device.as_dict()
            
            db_host.update_inventory(self._INVENTORY_PREFIX, inventory)
            db_host.sync_id = device.sync_id
            db_host.set_import_seen()
            do_save = db_host.set_account(account_dict=account.account)

            if do_save:
                db_host.save()
                results.append(inventory)
            else:
                logger.info(f"Object {hostname} owned by other source, not saved")

        return results

    """
    def get_interfaces(self, account: ExtremeCloudAccount) -> None:
        #Fetch and update interface information for devices.
        #Placeholder implementation, as the specific API endpoint is unknown.
        
        logger.info(f"{ColorCodes.OKGREEN}Starting ExtremeCloudIQ Interface Sync{ColorCodes.ENDC}")
        # Expected interface attributes (based on typical network device interfaces)
        interface_attributes = [
            'name', 'status', 'mac_address', 'speed', 'description',
            'admin_status', 'oper_status', 'mtu', 'vlan'
        ]

        for db_host in Host.objects(available=True, source_account_id=str(account.account['_id'])):
            if not db_host.sync_id:
                logger.warning(f"No device ID for {db_host.hostname}, skipping interface sync")
                continue

            try:
                # Placeholder for interface endpoint (e.g., /devices/{device_id}/interfaces)
                url = f"{self._API_PATH_INTERFACES_BASE}{db_host.sync_id}/interfaces"
                response = account._make_api_request('GET', url)
                interface_data = response.json().get('data', [])

                if not isinstance(interface_data, list):
                    logger.warning(f"Expected a list of interfaces for {db_host.hostname}, got: {type(interface_data)}")
                    continue

                interface_inventory = {}
                for iface in interface_data:
                    iface_id = iface.get('id')
                    if not iface_id:
                        logger.warning(f"Interface without ID for {db_host.hostname}, skipping: {iface}")
                        continue

                    # Format MAC address if present
                    mac = iface.get('mac_address')
                    if mac:
                        interface_inventory[f'{self._INVENTORY_PREFIX}interface_{iface_id}_mac'] = self._format_mac_address(mac)

                    # Map other interface attributes
                    for attr in interface_attributes:
                        if attr == 'mac_address':
                            continue  # Already handled
                        if attr in iface:
                            interface_inventory[f'{self._INVENTORY_PREFIX}interface_{iface_id}_{attr}'] = iface[attr]

                if interface_inventory:
                    db_host.update_inventory(f'{self._INVENTORY_PREFIX}interface_', interface_inventory)
                    db_host.save()
                    logger.info(f"Updated interfaces for {db_host.hostname}")
                else:
                    logger.info(f"No interface data for {db_host.hostname}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching interfaces for {db_host.hostname}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing interfaces for {db_host.hostname}: {e}")
    """