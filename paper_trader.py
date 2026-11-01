import json
import os
from datetime import datetime


class PaperTrader:

    def __init__(self, starting_balance=100.0):

        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.trades = []

        self.filename = "paper_trades.json"

        self.load_data()

    def load_data(self):

        if os.path.exists(self.filename):

            try:
                with open(self.filename, "r") as file:
                    data = json.load(file)

                self.balance = data["balance"]
                self.trades = data["trades"]

            except (json.JSONDecodeError, KeyError):
                print("Could not load previous trading data.")

    def save_data(self):

        data = {
            "balance": self.balance,
            "trades": self.trades
        }

        with open(self.filename, "w") as file:
            json.dump(data, file, indent=4)

    def open_trade(self, market_id, title, side, price, stake):

        if side not in ["YES", "NO"]:
            return {"error": "Invalid trading side"}

        if not 0 < price < 1:
            return {"error": "Invalid market price"}

        if stake <= 0 or stake > self.balance:
            return {"error": "Insufficient balance"}

        shares = stake / price

        trade = {
            "market_id": market_id,
            "title": title,
            "side": side,
            "entry_price": price,
            "stake": stake,
            "shares": shares,
            "status": "OPEN",
            "opened_at": datetime.utcnow().isoformat()
        }

        self.balance -= stake
        self.trades.append(trade)

        self.save_data()

        return trade

    def settle_trade(self, market_id, outcome):

        if outcome not in ["YES", "NO"]:
            return {"error": "Invalid outcome"}

        for trade in self.trades:

            if (
                trade["market_id"] == market_id
                and trade["status"] == "OPEN"
            ):

                if trade["side"] == outcome:

                    payout = trade["shares"]

                else:

                    payout = 0.0

                profit = payout - trade["stake"]

                self.balance += payout

                trade["status"] = "SETTLED"
                trade["outcome"] = outcome
                trade["payout"] = round(payout, 4)
                trade["profit"] = round(profit, 4)

                self.save_data()

                return trade

        return {"error": "Open trade not found"}

    def get_status(self):

        settled = [
            trade for trade in self.trades
            if trade["status"] == "SETTLED"
        ]

        total_profit = sum(
            trade["profit"] for trade in settled
        )

        return {
            "balance": round(self.balance, 2),
            "total_trades": len(self.trades),
            "open_trades": sum(
                t["status"] == "OPEN" for t in self.trades
            ),
            "settled_trades": len(settled),
            "realized_profit": round(total_profit, 2)
        }


if __name__ == "__main__":

    bot = PaperTrader()

    print("PAPER TRADING ACCOUNT")
    print("---------------------")

    print(bot.get_status())
