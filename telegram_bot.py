import os
import requests


class TelegramBot:

    def __init__(self):

        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        self.api_url = (
            f"https://api.telegram.org/bot{self.token}"
            if self.token else None
        )

    def send_message(self, message):

        if not self.token or not self.chat_id:
            print("Telegram credentials are missing.")
            return False

        url = f"{self.api_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:

            response = requests.post(
                url,
                json=payload,
                timeout=15
            )

            response.raise_for_status()

            result = response.json()

            return result.get("ok", False)

        except requests.RequestException as error:

            print(f"Telegram error: {error}")

            return False

    def send_opportunity(self, opportunity):

        message = (
            "🚨 <b>NEW MARKET OPPORTUNITY</b>\n\n"
            f"Market: {opportunity['market_title']}\n"
            f"Position: {opportunity['side']}\n"
            f"Estimated edge: "
            f"{opportunity['estimated_edge']:.2%}\n\n"
            "⚠️ Paper trading signal only."
        )

        return self.send_message(message)

    def send_daily_report(self, status):

        message = (
            "📊 <b>DAILY TRADING REPORT</b>\n\n"
            f"Balance: ${status['balance']}\n"
            f"Daily P/L: ${status['daily_pnl']}\n"
            f"Total trades: {status['total_trades']}\n"
            f"Trading allowed: {status['trading_allowed']}"
        )

        return self.send_message(message)


if __name__ == "__main__":

    bot = TelegramBot()

    bot.send_message(
        "🤖 Prediction Market AI is online!\n"
        "Trading mode: PAPER"
    )
