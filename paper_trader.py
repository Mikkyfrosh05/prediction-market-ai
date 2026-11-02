import json
import os
import uuid
from datetime import datetime, timezone

from risk_manager import (
    load_state,
    can_trade,
    reserve_trade,
    settle_reserved_trade,
    get_status as get_risk_status
)


class PaperTrader:

    def __init__(self):

        self.filename = "paper_trades.json"
        self.trades = []

        self.load_data()

    def load_data(self):

        if os.path.exists(self.filename):

            try:
                with open(self.filename, "r") as file:
                    data = json.load(file)

                self.trades = data.get("trades", [])

            except (json.JSONDecodeError, OSError, TypeError):
                print("Warning: Could not load previous paper trades.")

        else:
            self.save_data()

    def save_data(self):

        data = {
            "mode": "PAPER",
            "trades": self.trades
        }

        temporary_file = self.filename + ".tmp"

        with open(temporary_file, "w") as file:
            json.dump(data, file, indent=4)

        os.replace(temporary_file, self.filename)

    def open_trade(
        self,
        market_id,
        title,
        side,
        price,
        stake=2.00,
        estimated_fee=0.00,
        estimated_slippage=0.00
    ):

        side = str(side).upper()

        if side not in ["UP", "DOWN"]:
            return {"error": "Invalid side. Use UP or DOWN."}

        try:
            price = float(price)
            stake = float(stake)
            estimated_fee = float(estimated_fee)
            estimated_slippage = float(estimated_slippage)

        except (ValueError, TypeError):
            return {"error": "Invalid trade values."}

        if not 0 < price < 1:
            return {"error": "Invalid market price."}

        if stake <= 0:
            return {"error": "Stake must be greater than zero."}

        if estimated_fee < 0 or estimated_slippage < 0:
            return {"error": "Invalid fee or slippage estimate."}

        if any(
            trade.get("market_id") == market_id
            and trade.get("status") in ["OPEN", "SETTLED"]
            for trade in self.trades
        ):
            return {
                "error": "A trade already exists for this market."
            }

        approved, reason = can_trade(
            stake,
            estimated_fee,
            estimated_slippage
        )

        if not approved:
            return {"error": reason}

        reservation = reserve_trade(
            stake,
            estimated_fee,
            estimated_slippage
        )

        if reservation is False:
            return {
                "error": "Risk manager could not reserve funds."
            }

        if isinstance(reservation, dict) and reservation.get("error"):
            return reservation

        trade = {
            "trade_id": str(uuid.uuid4()),
            "market_id": str(market_id),
            "title": title,
            "side": side,
            "entry_price": price,
            "stake": round(stake, 4),
            "shares": round(stake / price, 8),
            "estimated_fee": round(estimated_fee, 4),
            "estimated_slippage": round(estimated_slippage, 4),
            "reserved_total": round(
                stake + estimated_fee + estimated_slippage, 4
            ),
            "status": "OPEN",
            "opened_at": datetime.now(timezone.utc).isoformat()
        }

        self.trades.append(trade)

        try:
            self.save_data()

        except OSError:
            print(
                "CRITICAL: Trade reservation succeeded, "
                "but trade file could not be saved."
            )
            return {
                "error": "Trade file could not be saved. "
                         "Check risk_state.json before continuing."
            }

        return trade

    def settle_trade(self, market_id, outcome):

        outcome = str(outcome).upper()

        if outcome not in ["UP", "DOWN"]:
            return {
                "error": "Invalid outcome. Use UP or DOWN."
            }

        for trade in self.trades:

            if (
                str(trade.get("market_id")) == str(market_id)
                and trade.get("status") == "OPEN"
            ):

                if trade["side"] == outcome:
                    payout = trade["shares"]
                else:
                    payout = 0.0

                fees = trade["estimated_fee"]
                slippage = trade["estimated_slippage"]

                settlement = settle_reserved_trade(
                    stake=trade["stake"],
                    payout=payout,
                    fees=fees,
                    slippage=slippage
                )

                if settlement is False:
                    return {
                        "error": "Risk manager could not settle trade."
                    }

                if isinstance(settlement, dict) and settlement.get("error"):
                    return settlement

                trade["status"] = "SETTLED"
                trade["outcome"] = outcome
                trade["payout"] = round(payout, 4)
                trade["profit"] = round(
                    payout - trade["stake"] - fees - slippage,
                    4
                )
                trade["settled_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )

                self.save_data()

                return trade

        return {"error": "Open trade not found."}

    def get_status(self):

        settled = [
            trade for trade in self.trades
            if trade.get("status") == "SETTLED"
        ]

        total_profit = sum(
            trade.get("profit", 0)
            for trade in settled
        )

        open_trades = sum(
            trade.get("status") == "OPEN"
            for trade in self.trades
        )

        risk_status = get_risk_status()

        return {
            "mode": "PAPER",
            "balance": risk_status["balance"],
            "reserved": risk_status.get("reserved", 0),
            "total_trades": len(self.trades),
            "open_trades": open_trades,
            "settled_trades": len(settled),
            "wins": risk_status["wins"],
            "losses": risk_status["losses"],
            "win_rate": risk_status["win_rate"],
            "realized_profit": round(total_profit, 4),
            "real_trading": False
        }


if __name__ == "__main__":

    bot = PaperTrader()

    print("=" * 45)
    print("BTC UP/DOWN PAPER TRADING ACCOUNT")
    print("=" * 45)

    for key, value in bot.get_status().items():
        print(f"{key}: {value}")

    print("=" * 45)
    print("Real trading: DISABLED")
