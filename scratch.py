import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    api = HyperliquidAPI(is_testnet=True)
    res = await api.place_order('PURR/USDC', 1, 0.0001, True, is_perp=False)
    print('RESPONSE:', res)

asyncio.run(test())
