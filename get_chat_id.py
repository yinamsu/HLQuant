import requests

TOKEN = "8615697956:AAHpP1KjNDMeLcSctG5yleathSbIRcvu-Ss"
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    response = requests.get(url)
    data = response.json()
    if data.get("result"):
        last_msg = data["result"][-1]
        chat_id = last_msg["message"]["chat"]["id"]
        chat_title = last_msg["message"]["chat"].get("title", "Private Chat")
        print(f"Room Found: {chat_title}")
        print(f"CHAT_ID: {chat_id}")
    else:
        print("No messages found yet. Please send a message to @HLQunatbot first!")
except Exception as e:
    print(f"Error occurred: {e}")
