import os
import asyncio
from dotenv import load_dotenv
from hyperliquid_api import HyperliquidAPI

async def finalize_mapping():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    meta, _ = api.info.spot_meta_and_asset_ctxs()
    tokens = meta['tokens']
    universe = meta['universe']
    token_map = {t['index']: t for t in tokens}
    
    # 표준 퍼프 심볼 리스트
    standard_perps = ["BTC", "ETH", "SOL", "AVAX", "DYDX", "BNB", "LTC", "HYPE", "SOLV", "PURR"]
    mapping = {}
    
    print(f"{'Perp':<10} | {'Spot Univ':<10} | {'Token':<10} | {'Full Name'}")
    print("-" * 60)
    
    for symbol in standard_perps:
        best_univ = None
        best_token = None
        
        for u in universe:
            token_indices = u.get('tokens', [])
            if not token_indices: continue
            
            base_token = token_map.get(token_indices[0], {})
            t_name = base_token.get('name', '')
            f_name = base_token.get('fullName') or ''
            
            # 매칭 조건: 
            # 1. 이름이 정확히 일치 (HYPE, PURR)
            # 2. 유닛 이름 일치 (UBTC, UETH, USOL, UAVAX)
            # 3. 풀네임에 포함 (Bitcoin, Ethereum, Solana)
            match = False
            if t_name == symbol: match = True
            elif t_name == f"U{symbol}": match = True
            elif symbol == "BTC" and "Bitcoin" in f_name: match = True
            elif symbol == "ETH" and "Ethereum" in f_name: match = True
            elif symbol == "SOL" and "Solana" in f_name: match = True
            elif symbol == "AVAX" and ("Avalanche" in f_name or t_name == "AVAX0"): match = True
            
            if match:
                # USDC 페어인 유니버스를 우선 선택 (보통 유니버스 이름에 USDC가 있거나 토큰[1]이 USDC)
                quote_token = token_map.get(token_indices[1], {}) if len(token_indices) > 1 else {}
                if quote_token.get('name') == 'USDC':
                    best_univ = u['name']
                    best_token = t_name
                    best_full = f_name
                    break
        
        if best_univ:
            mapping[symbol] = best_univ
            print(f"{symbol:<10} | {best_univ:<10} | {best_token:<10} | {best_full}")

if __name__ == "__main__":
    asyncio.run(finalize_mapping())
