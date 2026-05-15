import asyncio
from hyperliquid_api import HyperliquidAPI
from strategy import DeltaNeutralStrategy
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    strategy = DeltaNeutralStrategy(api=api)
    
    perp_data = await api.get_all_perp_data()
    spot_data = await api.get_all_spot_data()
    
    if 'HYPE' in perp_data and 'HYPE' in spot_data:
        p = perp_data['HYPE']
        s = spot_data['HYPE']
        
        funding = p['funding']
        apy = funding * 3 * 365 * 100
        premium = (p['midPrice'] - s['midPrice']) / s['midPrice'] * 100
        
        print(f"--- HYPE Analysis ---")
        print(f"Current APY: {apy:.2f}% (Threshold: 10%)")
        print(f"Premium: {premium:.4f}% (Threshold: > -0.1%)")
        print(f"Perp Price: {p['midPrice']}")
        print(f"Spot Price: {s['midPrice']}")
        
        if apy < 10:
            print(">> REASON: APY is too low.")
        elif premium < -0.1:
            print(">> REASON: Premium is too negative (Backwadation).")
        else:
            print(">> REASON: Other (Balance or Slot limit).")
    else:
        print("HYPE not found in data.")

    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
