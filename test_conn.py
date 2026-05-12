import requests
import json

url = "https://api.hyperliquid-testnet.xyz/info"
payload = {"type": "metaAndAssetCtxs"}
try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success!")
        # print(response.json())
except Exception as e:
    print(f"Failed: {e}")
