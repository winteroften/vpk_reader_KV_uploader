import requests
import json

class CloudflareKV:
    def __init__(self, account_id, namespace_id, api_token):
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def write_key_value(self, key, value):
        url = f"{self.base_url}/values/{key}"
        headers = self.headers.copy()
        headers["Content-Type"] = "text/plain"
        response = requests.put(url, headers=headers, data=value.encode('utf-8'))
        return response.status_code == 200, response.json() if response.status_code != 200 else {}
        
    def write_bulk(self, key_values):
        url = f"{self.base_url}/bulk"
        payload = [{"key": k, "value": v} for k, v in key_values.items()]
        response = requests.put(url, headers=self.headers, json=payload)
        return response.status_code == 200, response.json()

    def list_keys(self):
        url = f"{self.base_url}/keys?limit=1000"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return True, response.json().get("result", [])
        return False, response.json()

    def get_value(self, key):
        url = f"{self.base_url}/values/{key}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return True, response.text
        return False, response.text

    def delete_key(self, key):
        url = f"{self.base_url}/values/{key}"
        response = requests.delete(url, headers=self.headers)
        return response.status_code == 200, response.json() if response.status_code != 200 else {}
