
import asyncio
import logging
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def cleanup():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    api = HyperliquidAPI(is_testnet=False)
    
    print("--- 1. Closing LINK Perp Position ---")
    # Current size is -1.2 (Short). Need to Buy 1.2.
    # Get current price for LINK
    perp_data = await api.get_all_perp_data()
    if perp_data and 'LINK' in perp_data:
        px = perp_data['LINK']['midPrice']
        # Buy with slight slippage to ensure fill
        await api.place_order('LINK', 1.2, px * 1.02, True, is_perp=True)
    else:
        print("Failed to get LINK perp price")

    print("\n--- 2. Selling AVAX0 Spot Balance ---")
    # Current total is 0.00922049. 
    # AVAX0 is @226. szDecimals is 2.
    # 0.00922049 rounded to 2 decimals is 0.01. 
    # Wait, 0.009 is less than 0.01. Can we sell it? 
    # If szDecimals is 2, min size is 0.01.
    # Let's try to sell 0.01 if possible, or just leave it if it's "dust".
    # Actually, let's check szDecimals for @226 again.
    # [Spot] Pair: @226 (Index: 213) -> Base: AVAX0 (szDec: 2)
    # 0.009 is below the minimum trade size (0.01). It's dust.
    print("AVAX0 balance (0.00922) is below szDecimals (2) minimum (0.01). It is dust and will be left.")

    print("\n--- 3. Resetting paper_balance.json ---")
    import json
    with open("paper_balance.json", "w") as f:
        json.dump({"positions": {}, "total_realized_profit": 0.0}, f, indent=4)
    print("State reset successful.")

if __name__ == "__main__":
    asyncio.run(cleanup())
