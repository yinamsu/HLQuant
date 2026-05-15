import asyncio
from hyperliquid_api import HyperliquidAPI
import pandas as pd

async def main():
    api = HyperliquidAPI(is_testnet=False)
    
    # 1. 데이터 수집
    perp_data = await api.get_all_perp_data()
    spot_meta, asset_ctxs = api.info.spot_meta_and_asset_ctxs()
    
    # 2. 토큰 맵 구축
    tokens = spot_meta['tokens']
    
    market_list = []
    
    # 3. 모든 현물 페어 탐색
    for i, pair in enumerate(spot_meta['universe']):
        token_indices = pair.get('tokens', [])
        if not token_indices: continue
        
        base_token = tokens[token_indices[0]]
        symbol = base_token['name']
        spot_name = pair['name']
        spot_px = asset_ctxs[i].get('midPx')
        
        if not spot_px: continue
        spot_px = float(spot_px)
        
        # 4. 선물이 존재하는지 확인
        if symbol in perp_data:
            p = perp_data[symbol]
            perp_px = p['midPrice']
            funding = p['funding']
            apy = funding * 3 * 365 * 100
            
            # 프리미엄 (선물-현물)
            premium = (perp_px - spot_px) / spot_px * 100
            
            market_list.append({
                "Symbol": symbol,
                "SpotID": spot_name,
                "APY": apy,
                "Premium": premium,
                "Spot Price": spot_px,
                "Perp Price": perp_px
            })

    # 5. 결과 출력
    df = pd.DataFrame(market_list)
    if not df.empty:
        df = df.sort_values(by="APY", ascending=False)
        print("--- [Hyperliquid Intra-Exchange Arbitrage Market Analysis] ---")
        print(df.to_string(index=False))
    else:
        print("No matching Spot-Perp pairs found.")

    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
