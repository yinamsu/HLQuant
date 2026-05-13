import asyncio
import logging
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def test_mapping():
    load_dotenv()
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    api = HyperliquidAPI(is_testnet=False)
    print("Fetching universal spot mapping...")
    data = await api.get_all_spot_data()
    
    targets = ['BTC', 'ETH', 'SOL', 'HYPE', 'PURR', 'AI16Z']
    print("\n--- Mapping Results ---")
    for t in targets:
        mapping = data.get(t)
        if mapping:
            print(f"[{t}] -> Universe Name: {mapping['spot_name']} | Price: {mapping['midPrice']}")
        else:
            print(f"[{t}] -> Not Found in Spot Market")

if __name__ == "__main__":
    asyncio.run(test_mapping())
