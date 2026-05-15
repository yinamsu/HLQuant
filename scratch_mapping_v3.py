"""
Hyperliquid Spot-Perp Mapping v3 (FINAL)
==========================================
Based on official docs:
- spot_meta['universe'] 의 각 pair는 고유한 인덱스(=@번호)를 가짐
- pair['tokens'] = [base_token_index, quote_token_index]
- 토큰 이름과 선물 심볼이 같으면 매핑 후보
- BUT: 리매핑이 존재 (예: BTC -> UBTC)
- 따라서: 이름 매칭 + 가격 검증 = 둘 다 통과해야만 인정

핵심 차별점 vs 이전 시도:
- 이전: 가격만으로 ALL vs ALL 교차 매칭 (충돌 다수)
- 이번: 토큰 이름으로 1차 필터 + 가격으로 2차 검증 + 중복 시 최적 선택
"""
import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def build_final_mapping():
    info = Info(constants.MAINNET_API_URL)
    
    # === DATA LOADING ===
    perp_meta = info.meta()
    perp_symbols = {asset['name']: i for i, asset in enumerate(perp_meta['universe'])}
    all_mids = info.all_mids()
    
    spot_result = info.spot_meta_and_asset_ctxs()
    spot_meta, spot_ctxs = spot_result
    tokens = {t['index']: t for t in spot_meta['tokens']}
    
    # === STEP 1: Build reverse index ===
    # For each perp symbol, find ALL USDC spot pairs where base token name matches
    # (considering potential remaps like BTC->UBTC)
    
    # Known remappings from docs (UI name -> L1 name)
    # These are cases where the perp symbol differs from the spot token name
    KNOWN_REMAPS = {
        'BTC': 'UBTC',
        'ETH': 'UETH', 
        'SOL': 'USOL',
        # Add more as discovered
    }
    
    candidates = {}  # perp_symbol -> list of (pair_index, spot_pair_name, spot_price)
    
    for pair_idx, pair in enumerate(spot_meta['universe']):
        toks = pair.get('tokens', [])
        if len(toks) < 2:
            continue
        
        base = tokens.get(toks[0])
        quote = tokens.get(toks[1])
        if not base or not quote or quote['name'] != 'USDC':
            continue
        
        base_name = base['name']
        spot_px = float(spot_ctxs[pair_idx].get('midPx') or 0)
        pair_name = pair['name']  # This is "PURR/USDC" or "@{pair_idx}"
        
        if spot_px == 0:
            continue
        
        # Check if base token matches any perp symbol (direct or remapped)
        for perp_sym in perp_symbols:
            perp_px = float(all_mids.get(perp_sym, 0))
            if perp_px == 0:
                continue
                
            # Direct match: token name == perp symbol
            is_name_match = (base_name == perp_sym)
            
            # Remap match: known UI remap
            remap_target = KNOWN_REMAPS.get(perp_sym)
            is_remap_match = (remap_target and base_name == remap_target)
            
            # k-prefix match: kSHIB on perp = SHIB on spot (but 1000x)
            is_k_match = (perp_sym.startswith('k') and base_name == perp_sym[1:])
            
            if is_name_match or is_remap_match or is_k_match:
                if perp_sym not in candidates:
                    candidates[perp_sym] = []
                candidates[perp_sym].append({
                    'pair_idx': pair_idx,
                    'pair_name': pair_name,
                    'base_name': base_name,
                    'spot_px': spot_px,
                    'perp_px': perp_px,
                    'match_type': 'direct' if is_name_match else ('remap' if is_remap_match else 'k-prefix'),
                })
    
    # === STEP 2: Select best match with price verification ===
    verified = {}
    
    print(f"{'Perp':<12} | {'Spot ID':<12} | {'L1 Name':<10} | {'Perp$':<12} | {'Spot$':<12} | {'Gap%':<8} | {'Status'}")
    print("-" * 90)
    
    for perp_sym, cands in sorted(candidates.items()):
        if len(cands) == 1:
            c = cands[0]
            gap = abs(c['perp_px'] - c['spot_px']) / c['spot_px'] * 100
            
            if c['match_type'] == 'k-prefix':
                # k-prefix: perp price should be ~1000x spot price
                k_ratio = c['perp_px'] / c['spot_px'] if c['spot_px'] > 0 else 0
                if 900 < k_ratio < 1100:
                    verified[perp_sym] = c['pair_name']
                    print(f"{perp_sym:<12} | {c['pair_name']:<12} | {c['base_name']:<10} | {c['perp_px']:<12.4f} | {c['spot_px']:<12.6f} | k={k_ratio:.0f}x | OK (k)")
                else:
                    print(f"{perp_sym:<12} | {c['pair_name']:<12} | {c['base_name']:<10} | {c['perp_px']:<12.4f} | {c['spot_px']:<12.6f} | k={k_ratio:.0f}x | FAIL (k)")
            elif gap < 3.0:
                verified[perp_sym] = c['pair_name']
                print(f"{perp_sym:<12} | {c['pair_name']:<12} | {c['base_name']:<10} | {c['perp_px']:<12.4f} | {c['spot_px']:<12.4f} | {gap:<8.2f} | OK")
            else:
                print(f"{perp_sym:<12} | {c['pair_name']:<12} | {c['base_name']:<10} | {c['perp_px']:<12.4f} | {c['spot_px']:<12.4f} | {gap:<8.2f} | FAIL (price)")
        else:
            # Multiple candidates - pick best by price
            best = None
            best_gap = 999
            for c in cands:
                gap = abs(c['perp_px'] - c['spot_px']) / c['spot_px'] * 100
                if gap < best_gap:
                    best_gap = gap
                    best = c
            
            if best and best_gap < 3.0:
                verified[perp_sym] = best['pair_name']
                print(f"{perp_sym:<12} | {best['pair_name']:<12} | {best['base_name']:<10} | {best['perp_px']:<12.4f} | {best['spot_px']:<12.4f} | {best_gap:<8.2f} | OK (best of {len(cands)})")
            else:
                print(f"{perp_sym:<12} | {'???':<12} | {'???':<10} | {'???':<12} | {'???':<12} | {'???':<8} | FAIL (no match in {len(cands)})")
    
    # === STEP 3: Save ===
    with open("spot_mapping_final.json", "w") as f:
        json.dump(verified, f, indent=4)
    
    print(f"\nTotal verified: {len(verified)}")
    print(f"Saved to spot_mapping_final.json")

if __name__ == "__main__":
    asyncio.run(build_final_mapping())
