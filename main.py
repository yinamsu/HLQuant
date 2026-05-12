import asyncio
import logging
import logging.handlers
import sys

from hyperliquid_api import HyperliquidAPI
from strategy import DeltaNeutralStrategy
from notifier import TelegramNotifier

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler("bot.log", maxBytes=10*1024*1024, backupCount=5)
    ]
)

async def main():
    logging.info("=== Hyperliquid Delta Neutral Paper Trading Bot Started ===")
    
    api = HyperliquidAPI()
    strategy = DeltaNeutralStrategy()
    notifier = TelegramNotifier()
    
    await notifier.set_commands()
    await notifier.send_message("✅ *HLQuant Bot 가동 시작* (Paper Trading Mode)")
    
    try:
        while True:
            logging.info("시장 스캔 중...")
            
            # 1. 시장 데이터 가져오기
            perp_data = await api.get_all_perp_data()
            spot_data = await api.get_all_spot_data()
            
            if perp_data and spot_data is not None:
                # 2. 전략 로직 실행
                await strategy.execute_logic(perp_data, spot_data)
                
                # 현재 상태 출력 (옵션)
                pos_count = len(strategy.positions)
                logging.info(f"현재 보유 포지션 수: {pos_count}/3")
                for sym, details in strategy.positions.items():
                    logging.info(f" -> {sym}: 진입일시={details['entry_time']}, 진입APY={details['entry_apy']:.2f}%")
            else:
                logging.warning("데이터를 가져오는 데 실패했습니다. 다음 루프에서 재시도합니다.")
            
            # 3. 1분 대기 중 1초마다 텔레그램 명령어 확인 (실시간 응답성 개선)
            for _ in range(60): # 60 * 1초 = 60초
                await notifier.check_commands()
                await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logging.info("봇 종료 요청을 받았습니다.")
    except Exception as e:
        logging.error(f"예기치 못한 오류 발생: {e}", exc_info=True)
    finally:
        await api.close()
        logging.info("=== Bot Safely Stopped ===")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
