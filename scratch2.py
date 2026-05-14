import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv
load_dotenv(override=True)

async def test():
    api = HyperliquidAPI(is_testnet=True)
    # Get spot data to find current price
    spot_data = await api.get_all_spot_data()
    # Find a valid spot symbol, e.g., HYPE/USDC
    symbol = 'HYPE/USDC'
    if symbol not in spot_data.values():
        # Just pick the first one
        symbol = list(spot_data.values())[0].get('spot_name')
        
    print(f"Testing IOC buy on {symbol} at very low price to ensure 0 fill.")
    # Place buy order at 10% of market price
    res = await api.place_order(symbol, 1, 0.001, True, is_perp=False)
    print('RESPONSE:', res)

asyncio.run(test())
