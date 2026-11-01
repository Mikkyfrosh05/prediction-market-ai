from config import CONFIG


class RiskManager:

    def __init__(self):

        self.balance = CONFIG["STARTING_BALANCE"]

        self.max_trade = CONFIG["MAX_TRADE"]

        self.max_daily_loss = CONFIG["MAX_DAILY_LOSS"]

        self.daily_pnl = 0.0

        self.total_trades = 0

    def can_trade(self):

        if self.daily_pnl <= -self.max_daily_loss:
            return False

        if self.balance <= 0:
            return False

        return True

    def calculate_position_size(self, market_price):

        if not self.can_trade():
            return 0.0

        if not isinstance(market_price, (int, float)):
            return 0.0

        if not 0 < market_price < 1:
            return 0.0

        position_size = min(
            self.max_trade,
            self.balance,
            self.max_daily_loss + self.daily_pnl
        )

        return max(0.0, round(position_size, 2))

    def record_result(self, pnl):

        if not isinstance(pnl, (int, float)):
            raise ValueError("Invalid trade result")

        self.daily_pnl += pnl
        self.balance += pnl
        self.total_trades += 1

    def get_status(self):

        return {
            "balance": round(self.balance, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_loss_limit": self.max_daily_loss,
            "total_trades": self.total_trades,
            "trading_allowed": self.can_trade()
        }


if __name__ == "__main__":

    manager = RiskManager()

    print("RISK MANAGEMENT STATUS")
    print("----------------------")

    print(manager.get_status())

    stake = manager.calculate_position_size(0.45)

    print("\nSuggested paper trade size:", stake)
