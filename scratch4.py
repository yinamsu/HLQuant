import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    api = HyperliquidAPI(is_testnet=True)
    # 0xEa9C16f84997cA68e1E589DF6955F826b5b02FBD
    # Try with exact case
    state = api.info.user_state("0xEa9C16f84997cA68e1E589DF6955F826b5b02FBD")
    print("Mixed case balance:", state.get('marginSummary', {}).get('accountValue'))
    
    # Try with lower case
    state2 = api.info.user_state("0xea9c16f84997ca68e1e589df6955f826b5b02fbd")
    print("Lower case balance:", state2.get('marginSummary', {}).get('accountValue'))
    await api.close()

asyncio.run(test())
