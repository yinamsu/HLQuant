import requests
url = "https://api.hyperliquid-testnet.xyz/info"
payload = {"type": "clearinghouseState", "user": "0xEa9C16f84997cA68e1E589DF6955F826b5b02FBD"}
response = requests.post(url, json=payload)
print(response.json())
