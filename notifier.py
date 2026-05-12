import aiohttp
import logging
import os
from dotenv import load_dotenv

# .env 파일 로드 (시스템 환경 변수가 있더라도 .env 내용을 우선 적용)
load_dotenv(override=True)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        self.cmd_url = f"https://api.telegram.org/bot{self.token}/setMyCommands"

    async def set_commands(self):
        if not self.token: return
        
        commands = [
            {"command": "status", "description": "현재 봇 상태 및 시장 요약"},
            {"command": "balance", "description": "가상 장부 수익률 확인"},
            {"command": "positions", "description": "현재 보유 포지션 확인"},
            {"command": "help", "description": "명령어 도움말"}
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.cmd_url, json={"commands": commands}) as response:
                    if response.status == 200:
                        logging.info("Telegram commands menu set successfully")
                    else:
                        logging.error(f"Failed to set Telegram commands: {await response.text()}")
        except Exception as e:
            logging.error(f"Error setting Telegram commands: {e}")

    async def send_message(self, text):
        if not self.token or not self.chat_id:
            logging.warning("Telegram token or chat_id is missing in .env")
            return

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send Telegram message: {await response.text()}")
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")

    async def send_entry_notification(self, symbol, apy, spot_px, perp_px):
        text = (
            f"🚀 *[VIRTUAL ENTRY]*\n\n"
            f"• *Symbol*: {symbol}\n"
            f"• *APY*: {apy:.2f}%\n"
            f"• *Spot Buy*: {spot_px:.4f}\n"
            f"• *Perp Sell*: {perp_px:.4f}\n"
            f"• *Time*: {logging.Formatter('%(asctime)s').format(logging.LogRecord('', 0, '', 0, '', None, None))}"
        )
        await self.send_message(text)

    async def send_exit_notification(self, symbol, reason):
        text = (
            f"📉 *[VIRTUAL EXIT]*\n\n"
            f"• *Symbol*: {symbol}\n"
            f"• *Reason*: {reason}\n"
        )
        await self.send_message(text)
