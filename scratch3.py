import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    api = HyperliquidAPI(is_testnet=True)
    state = await api.get_user_state()
    print('KEYS:', state.keys())
    print('withdrawable:', state.get('withdrawable'))
    print('marginSummary:', state.get('marginSummary'))
    await api.close()

asyncio.run(test())
