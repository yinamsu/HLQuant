import asyncio
import os
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    balance = await api.get_balance()
    print(f"Total Balance (Mainnet): {balance}")
    
    user_state = await api.get_user_state()
    perp_withdrawable = user_state.get('marginSummary', {}).get('withdrawable', 0.0)
    print(f"Perp Withdrawable: {perp_withdrawable}")
    
    spot_state = api.info.spot_user_state(api.wallet_address)
    print(f"Spot Balances: {spot_state.get('balances', [])}")
    
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
