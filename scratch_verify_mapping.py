import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    spot_data = await api.get_all_spot_data()
    print("ETH Spot Data:", spot_data.get('ETH'))
    print("BNB Spot Data:", spot_data.get('BNB'))
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
