import asyncio
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def estimate_profit():
    info = Info(constants.MAINNET_API_URL)
    # meta와 contexts를 가져오는 정확한 메서드 (get_ 없이)
    result = info.meta_and_asset_ctxs()
    
    meta = result[0]
    contexts = result[1]
    
    opportunities = []
    for i, universe in enumerate(meta['universe']):
        symbol = universe['name']
        ctx = contexts[i]
        
        if 'funding' in ctx:
            funding = float(ctx['funding'])
            apy = funding * 24 * 365 * 100
            
            if apy >= 7.5:
                opportunities.append({
                    'symbol': symbol,
                    'apy': apy
                })
    
    opportunities.sort(key=lambda x: x['apy'], reverse=True)
    
    print(f"\n--- Current Market Opportunities (APY >= 7.5%) ---")
    top_n = 3
    total_apy = 0
    
    for i, opp in enumerate(opportunities[:10]):
        print(f"{i+1}. {opp['symbol']}: {opp['apy']:.2f}%")
        if i < top_n:
            total_apy += opp['apy']
            
    avg_apy = total_apy / top_n if opportunities else 0
    
    print(f"\n--- Monthly Profit Estimation ($50 Capital) ---")
    print(f"Target Avg APY: {avg_apy:.2f}%")
    
    # 현실적인 월 수익률 계산
    # 수수료(진입/청산), 슬리피지, 펀딩비 하락 가능성, 노는 자금 감안하여 60% 효율 가정
    efficiency = 0.6 
    monthly_rate = (avg_apy / 100 / 12) * efficiency
    monthly_profit_usd = 50 * monthly_rate
    
    print(f"Estimated Monthly Profit: ${monthly_profit_usd:.2f}")
    print(f"Expected ROI: {monthly_rate*100:.2f}% per month")
    print(f"Annual ROI (Compound): {(1 + monthly_rate)**12 * 100 - 100:.2f}%")

if __name__ == "__main__":
    asyncio.run(estimate_profit())
