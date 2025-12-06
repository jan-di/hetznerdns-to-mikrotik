"""
Hetzner Cloud API client
"""

import requests


class HetznerApi:
    """
    Hetzner Cloud API client
    """

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.v1_base_url = "https://api.hetzner.cloud/v1"
        self.client = requests.Session()
        self.client.headers.update({"Authorization": f"Bearer {self.api_token}"})

    def list_zones_v1(self, page: int = 1, per_page: int = 100):
        """
        List DNS zones

        See also https://docs.hetzner.cloud/reference/cloud#zones-list-zones
        """
        req = self.client.get(f"{self.v1_base_url}/zones", params={"page": page, "per_page": per_page})
        req.raise_for_status()

        return req.json()

    def list_rrsets_v1(self, zone_name_or_id: str, page: int = 1, per_page: int = 100):
        """
        List RRsets for a given zone

        See also https://docs.hetzner.cloud/reference/cloud#zone-rrsets-list-rrsets
        """
        req = self.client.get(
            f"{self.v1_base_url}/zones/{zone_name_or_id}/rrsets", params={"page": page, "per_page": per_page}
        )
        req.raise_for_status()

        return req.json()
