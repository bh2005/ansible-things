#!/usr/bin/env python3
"""
ExtremeCloudIQ Syncer Plugin for CMDBSyncer
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
    Account class for ExtremeCloudIQ API configuration
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
        Fetch authentication token from ExtremeCloudIQ API using username/password
        """
        current_time = time.time()
        if self._auth_token and self._token_expiry > current_time + 60:  # Buffer of 60 seconds
            logger.debug(f"{ColorCodes.OKGREEN}Using cached ExtremeCloud Auth Token{ColorCodes.ENDC}")
            return self._auth_token

        logger.info(f"{ColorCodes.OKGREEN}Requesting new ExtremeCloud Auth Token{ColorCodes.ENDC}")
        url = f"{self.api_url}/login"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "username": self.username,
            "password": self.password
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=self.verify_ssl, timeout=30)
            response.raise_for_status()
            response_json = response.json()
            token = response_json.get('access_token')
            if not token:
                raise Exception(f"Auth Token (access_token) not found in response: {response_json}")

            self._auth_token = token
            self._token_expiry = current_time + 24 * 3600  # Token valid for 24 hours
            return token

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ExtremeCloud Auth Token: {e}")
            logger.error(f"Response text: {response.text if 'response' in locals() else 'No response'}")
            raise Exception(f"Connection Problem or Authentication Failed: {e}") from e

    def _make_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.get_auth_token()}',
            'Content-Type': 'application/json'
        }

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
        """Extract location name from locations list"""
        if locations and isinstance(locations, list) and len(locations) > 0:
            return locations[0].get('name', '')
        return ''

    def get_identifier(self) -> str:
        """Return unique identifier for the device"""
        return self.serial or self.hostname

    def as_dict(self) -> Dict:
        """Return device data as dictionary for CMDBSyncer inventory"""
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
                inventory[f'extremecloud_{attr}'] = self.data[attr]
        return inventory

class ExtremeCloudAPI(BasePlugin):
    """
    Plugin class for ExtremeCloudIQ integration
    """
    def __init__(self):
        super().__init__()
        self.name = 'extremecloud'
        self.account_class = ExtremeCloudAccount
        self.object_class = ExtremeCloudDevice

    @staticmethod
    def _format_mac_address(mac: str) -> str:
        """
        Format a MAC address from a 12-character string to XX:XX:XX:XX:XX:XX
        """
        if mac and len(mac) == 12:
            return ':'.join(mac[i:i+2] for i in range(0, len(mac), 2))
        return mac

    @staticmethod
    def _calculate_uptime(timestamp_ms: Optional[float]) -> Optional[str]:
        """
        Calculate uptime from a timestamp (in milliseconds) to a string
        in the format 'X days, HH:MM:SS' or None/error string on failure
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
        Fetch devices from ExtremeCloudIQ API with pagination
        """
        logger.info(f"{ColorCodes.OKGREEN}Starting ExtremeCloudIQ Device Sync{ColorCodes.ENDC}")
        url = f"{account.api_url}/devices"
        headers = account._make_headers()
        page = 0
        page_size = 100
        all_devices = []
        total_synced = 0

        while True:
            try:
                params = {'page': page, 'limit': page_size}
                response = requests.get(url, headers=headers, params=params, verify=account.verify_ssl, timeout=60)
                response.raise_for_status()
                data = response.json()
                devices = data.get('data', [])
                
                if not isinstance(devices, list):
                    logger.warning(f"Expected a list of devices, got: {type(devices)}. Response: {data}")
                    break

                if not devices:
                    logger.info(f"No devices found on page {page}, stopping pagination")
                    break

                all_devices.extend([ExtremeCloudDevice(account, device) for device in devices])
                total_synced += len(devices)
                logger.info(f"Synced {len(devices)} devices on page {page} (Total: {total_synced})")

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

        logger.info(f"Finished syncing {total_synced} ExtremeCloudIQ devices")
        return all_devices

    def inventorize(self, account: ExtremeCloudAccount, rewrite_config: Optional[Dict] = None) -> List[Dict]:
        """
        Synchronize devices to CMDBSyncer inventory
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
            
            db_host.update_inventory('extremecloud_', inventory)
            db_host.sync_id = device.sync_id
            db_host.set_import_seen()
            do_save = db_host.set_account(account_dict=account.account)

            if do_save:
                db_host.save()
                results.append(inventory)
            else:
                logger.info(f"Object {hostname} owned by other source, not saved")

        return results

    def get_interfaces(self, account: ExtremeCloudAccount) -> None:
        """
        Fetch and update interface information (placeholder, as API endpoint is unclear)
        """
        logger.info(f"{ColorCodes.OKGREEN}Starting ExtremeCloudIQ Interface Sync{ColorCodes.ENDC}")
        for db_host in Host.objects(available=True, source_account_id=str(account.account['_id'])):
            if not db_host.sync_id:
                logger.warning(f"No device ID for {db_host.hostname}, skipping interface sync")
                continue
            logger.info(f"Interface sync for {db_host.hostname} not implemented (no API endpoint)")
            # Implement actual interface fetching here if API supports it