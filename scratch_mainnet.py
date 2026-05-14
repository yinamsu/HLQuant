import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    api = HyperliquidAPI(is_testnet=False)  # Try Mainnet!
    state = await api.get_user_state()
    print("Mainnet balance:", state.get('marginSummary', {}).get('accountValue'))
    print("Mainnet positions:", len(state.get('assetPositions', [])))
    await api.close()

asyncio.run(test())
