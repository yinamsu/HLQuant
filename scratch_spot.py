import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    api = HyperliquidAPI(is_testnet=True)
    state = api.info.spot_user_state("0xEa9C16f84997cA68e1E589DF6955F826b5b02FBD")
    print("Spot balances:", state.get('balances'))
    await api.close()

asyncio.run(test())
