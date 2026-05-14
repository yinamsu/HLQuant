import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    # 1. Check current balances
    balance_total = await api.get_balance()
    print(f"Initial Total Balance: {balance_total}")
    
    # 2. Check Perp balance specifically
    user_state = await api.get_user_state()
    perp_withdrawable = float(user_state.get('marginSummary', {}).get('withdrawable', 0.0))
    print(f"Initial Perp Withdrawable: {perp_withdrawable}")
    
    if perp_withdrawable < 10:
        print("Perp balance low. Transferring from Spot...")
        # Move 25 USDC to Perp
        res = await api.spot_user_transfer(25.0, to_perp=True)
        print("Transfer Result:", res)
    else:
        print("Perp balance already sufficient.")
    
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
