"""
Hyperliquid Spot-Perp Mapping Deep Research
============================================
Goal: Understand the EXACT data structure of spot markets
      to build a bulletproof mapping.

Key questions:
1. What does spot_meta() return exactly?
2. How do token indices relate to market names?  
3. Why does the same token name appear in multiple markets?
4. What is the CORRECT way to link perp symbols to spot markets?
"""
import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def deep_research():
    info = Info(constants.MAINNET_API_URL)
    
    # ============================================
    # PHASE 1: Raw structure dump
    # ============================================
    spot_meta = info.spot_meta()
    tokens_list = spot_meta['tokens']
    universe = spot_meta['universe']
    
    # Perp symbols for cross-referencing
    perp_meta = info.meta()
    perp_symbols = {asset['name'] for asset in perp_meta['universe']}
    
    # Spot prices
    spot_result = info.spot_meta_and_asset_ctxs()
    spot_ctxs = spot_result[1]
    
    # Perp prices
    all_mids = info.all_mids()
    
    # Token index lookup
    token_map = {t['index']: t for t in tokens_list}
    
    print("=" * 80)
    print("PHASE 1: Spot Market Structure Analysis")
    print("=" * 80)
    print(f"Total tokens defined: {len(tokens_list)}")
    print(f"Total spot pairs (universe): {len(universe)}")
    print(f"Total perp symbols: {len(perp_symbols)}")
    
    # ============================================
    # PHASE 2: Find ALL USDC-quoted spot pairs where
    #          base token name matches a perp symbol
    # ============================================
    print("\n" + "=" * 80)
    print("PHASE 2: Name-matched pairs (base token name == perp symbol)")
    print("=" * 80)
    
    # Group by base token name to find duplicates
    name_to_pairs = {}
    
    for i, pair in enumerate(universe):
        toks = pair.get('tokens', [])
        if len(toks) < 2:
            continue
        
        base = token_map.get(toks[0])
        quote = token_map.get(toks[1])
        if not base or not quote:
            continue
        
        base_name = base['name']
        quote_name = quote['name']
        market_id = pair['name']
        spot_px = float(spot_ctxs[i].get('midPx') or 0)
        
        if quote_name != 'USDC':
            continue
        
        if base_name not in name_to_pairs:
            name_to_pairs[base_name] = []
        
        name_to_pairs[base_name].append({
            'market_id': market_id,
            'spot_px': spot_px,
            'base_index': toks[0],
            'base_decimals': base.get('szDecimals', 0),
            'is_perp_match': base_name in perp_symbols,
        })
    
    # ============================================
    # PHASE 3: For each perp-matched name, show ALL
    #          spot markets and identify the RIGHT one
    # ============================================
    print("\n" + "=" * 80)
    print("PHASE 3: Detailed analysis of perp-matched tokens")
    print("=" * 80)
    
    verified_mapping = {}
    conflicts = []
    
    for name, pairs in sorted(name_to_pairs.items()):
        if name not in perp_symbols:
            continue
        
        perp_px = float(all_mids.get(name, 0))
        
        if len(pairs) == 1:
            # Only one USDC market for this token - simple case
            p = pairs[0]
            if p['spot_px'] > 0 and perp_px > 0:
                gap = abs(perp_px - p['spot_px']) / p['spot_px'] * 100
                if gap < 3.0:
                    verified_mapping[name] = p['market_id']
                    print(f"[OK]   {name:<10} -> {p['market_id']:<12} | Perp ${perp_px:.4f} vs Spot ${p['spot_px']:.4f} | Gap {gap:.2f}%")
                else:
                    print(f"[FAIL] {name:<10} -> {p['market_id']:<12} | Perp ${perp_px:.4f} vs Spot ${p['spot_px']:.4f} | Gap {gap:.2f}% (TOO HIGH)")
                    conflicts.append(name)
            else:
                print(f"[SKIP] {name:<10} -> {p['market_id']:<12} | No price data")
        else:
            # MULTIPLE USDC markets for the same token name - DANGER ZONE
            print(f"\n[MULTI] {name} has {len(pairs)} USDC markets! Perp price: ${perp_px:.4f}")
            best_match = None
            best_gap = 999999
            
            for p in pairs:
                if p['spot_px'] > 0 and perp_px > 0:
                    gap = abs(perp_px - p['spot_px']) / p['spot_px'] * 100
                    marker = ""
                    if gap < 3.0:
                        if gap < best_gap:
                            best_gap = gap
                            best_match = p
                        marker = " <-- CANDIDATE"
                    print(f"        {p['market_id']:<12} | Spot ${p['spot_px']:.4f} | Gap {gap:.2f}%{marker}")
                else:
                    print(f"        {p['market_id']:<12} | No price")
            
            if best_match and best_gap < 3.0:
                verified_mapping[name] = best_match['market_id']
                print(f"  => Selected: {best_match['market_id']} (gap {best_gap:.2f}%)")
            else:
                print(f"  => NO SAFE MATCH FOUND")
                conflicts.append(name)
    
    # ============================================
    # PHASE 4: Summary
    # ============================================
    print("\n" + "=" * 80)
    print("PHASE 4: Final Verified Mapping")
    print("=" * 80)
    
    for sym, mid in sorted(verified_mapping.items()):
        perp_px = float(all_mids.get(sym, 0))
        print(f"  {sym:<12} -> {mid:<12} (Perp ${perp_px:.4f})")
    
    print(f"\nTotal verified: {len(verified_mapping)}")
    print(f"Conflicts (excluded): {conflicts}")
    
    # Save
    with open("spot_mapping_researched.json", "w") as f:
        json.dump(verified_mapping, f, indent=4)
    print(f"\nSaved to spot_mapping_researched.json")

if __name__ == "__main__":
    asyncio.run(deep_research())
