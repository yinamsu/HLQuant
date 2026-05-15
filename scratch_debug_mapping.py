import asyncio
from hyperliquid_api import HyperliquidAPI
import os
import json

async def main():
    api = HyperliquidAPI(is_testnet=False)
    
    if os.path.exists("spot_mapping.json"):
        with open("spot_mapping.json", "r") as f:
            print("Mapping Content:", f.read())
            
    spot_data = await api.get_all_spot_data()
    print("Spot Data Symbols:", list(spot_data.keys()))
    if 'HYPE' in spot_data:
        print("HYPE Data:", spot_data['HYPE'])
    else:
        print("HYPE MISSING from spot_data")
        
    perp_data = await api.get_all_perp_data()
    if 'HYPE' in perp_data:
        print("HYPE Perp Data found")
    else:
        print("HYPE Perp MISSING")
        
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
