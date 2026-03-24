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
        # Value must be sent as raw string/bytes if using PUT directly, or as a JSON list if using bulk
        # We'll use the single PUT endpoint for simplicity
        # PUT /accounts/:account_identifier/storage/kv/namespaces/:namespace_identifier/values/:key_name
        headers = self.headers.copy()
        # the value should be string/binary, no need to be json
        headers["Content-Type"] = "text/plain"
        response = requests.put(url, headers=headers, data=value.encode('utf-8'))
        return response.status_code == 200, response.json() if response.status_code != 200 else {}
        
    def write_bulk(self, key_values):
        url = f"{self.base_url}/bulk"
        payload = [{"key": k, "value": v} for k, v in key_values.items()]
        response = requests.put(url, headers=self.headers, json=payload)
        return response.status_code == 200, response.json()
