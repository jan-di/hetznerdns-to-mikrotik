import requests

class DnsApi:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.v1_base_url = 'https://dns.hetzner.com/api/v1'

    def get_zones_v1(self):
        req = requests.get(f'{self.v1_base_url}/zones', headers={'Auth-API-Token': self.api_key})
        req.raise_for_status()

        return req.json()
    
    def get_records_v1(self, zone_id: str):
        req = requests.get(f'{self.v1_base_url}/records', headers={'Auth-API-Token': self.api_key}, params={'zone_id': zone_id})
        req.raise_for_status()

        return req.json()
