import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def find_real_matches():
    info = Info(constants.MAINNET_API_URL)
    all_mids = info.all_mids()
    result = info.spot_meta_and_asset_ctxs()
    
    meta = result[0]
    contexts = result[1]
    
    print(f"{'Spot Name':<15} | {'Spot Price':<12} | {'Possible Perp Symbol'}")
    print("-" * 60)
    
    matches = {}
    for i, pair in enumerate(meta['universe']):
        spot_name = pair['name']
        spot_px = float(contexts[i].get('midPx') or 0)
        
        if spot_px == 0: continue
        
        # 모든 선물 종목과 가격 비교
        for perp_sym, perp_px in all_mids.items():
            perp_px = float(perp_px)
            if perp_px == 0: continue
            
            gap = abs(perp_px - spot_px) / spot_px * 100
            if gap < 1.0: # 가격 오차가 1% 미만인 것만!
                print(f"{spot_name:<15} | {spot_px:<12.6f} | MATCH: {perp_sym} ({gap:.2f}%)")
                matches[perp_sym] = spot_name

    print(f"\n--- Verified Matches ---")
    print(json.dumps(matches, indent=4))

if __name__ == "__main__":
    asyncio.run(find_real_matches())
