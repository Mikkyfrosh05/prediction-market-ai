import json
import os
from datetime import datetime, timezone

STARTING_BALANCE = 100.00

TRADES_FILE = "paper_trades.json"
RISK_FILE = "risk_state.json"
DECISIONS_FILE = "strategy_decisions.json"
OUTPUT_FILE = "performance.json"


def load_json(filename, default=None):
    if default is None:
        default = {}

    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"Could not read {filename}: {error}")


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def parse_date(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (ValueError, TypeError, AttributeError):
        return None


def calculate_drawdown(trades):
    settled = [
        trade for trade in trades
        if str(trade.get("status", "")).upper() == "SETTLED"
    ]

    settled.sort(
        key=lambda trade: (
            parse_date(trade.get("settled_at"))
            or datetime.min.replace(tzinfo=timezone.utc)
        )
    )

    balance = STARTING_BALANCE
    peak = STARTING_BALANCE
    maximum_drawdown = 0.0

    for trade in settled:
        balance += float(trade.get("profit", 0) or 0)
        peak = max(peak, balance)

        if peak > 0:
            drawdown = ((peak - balance) / peak) * 100
            maximum_drawdown = max(maximum_drawdown, drawdown)

    return round(maximum_drawdown, 4)


def calculate_daily_profit(trades):
    today = datetime.now(timezone.utc).date()
    daily_profit = 0.0

    for trade in trades:
        if str(trade.get("status", "")).upper() != "SETTLED":
            continue

        settled_at = parse_date(trade.get("settled_at"))

        if settled_at and settled_at.date() == today:
            daily_profit += float(trade.get("profit", 0) or 0)

    return round(daily_profit, 4)


def get_decisions(decisions_data):
    if isinstance(decisions_data, list):
        return decisions_data

    if isinstance(decisions_data, dict):
        for key in ["decisions", "history", "rejections"]:
            value = decisions_data.get(key)

            if isinstance(value, list):
                return value

        if decisions_data.get("reason"):
            return [decisions_data]

    return []


def build_public_trade_history(trades):
    history = []

    sorted_trades = sorted(
        trades,
        key=lambda trade: (
            parse_date(trade.get("opened_at"))
            or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True
    )

    for trade in sorted_trades[:20]:
        history.append({
            "title": trade.get("title", "BTC Market"),
            "side": trade.get("side", "UNKNOWN"),
            "entry_price": round(
                float(trade.get("entry_price", 0) or 0), 4
            ),
            "stake": round(
                float(trade.get("stake", 0) or 0), 4
            ),
            "profit": round(
                float(trade.get("profit", 0) or 0), 4
            ),
            "status": trade.get("status", "UNKNOWN"),
            "outcome": trade.get("outcome"),
            "opened_at": trade.get("opened_at"),
            "settled_at": trade.get("settled_at")
        })

    return history


def build_public_rejections(decisions):
    rejected = []

    for decision in decisions:
        if not isinstance(decision, dict):
            continue

        reason = (
            decision.get("reason")
            or decision.get("rejection_reason")
            or decision.get("message")
        )

        if not reason:
            continue

        status = str(decision.get("status", "")).upper()

        if status not in [
            "REJECTED",
            "SKIPPED",
            "NO_TRADE"
        ] and not decision.get("rejected", False):
            continue

        rejected.append({
            "direction": decision.get(
                "direction",
                decision.get("side", "UNKNOWN")
            ),
            "reason": str(reason),
            "timestamp": decision.get(
                "timestamp",
                decision.get("updated_at")
            )
        })

    return rejected[-20:][::-1]


def main():
    print("===================================")
    print("PAPER TRADING PERFORMANCE TRACKER")
    print("===================================")

    trade_data = load_json(
        TRADES_FILE,
        {"mode": "PAPER", "trades": []}
    )

    risk = load_json(RISK_FILE)

    decisions_data = load_json(
        DECISIONS_FILE,
        {}
    )

    if not isinstance(trade_data, dict):
        raise RuntimeError("Invalid paper_trades.json format.")

    if not isinstance(risk, dict):
        raise RuntimeError("Invalid risk_state.json format.")

    trades = trade_data.get("trades", [])

    if not isinstance(trades, list):
        raise RuntimeError("Trade history must be a list.")

    if str(trade_data.get("mode", "")).upper() != "PAPER":
        raise RuntimeError("Unexpected trading mode.")

    open_trades = [
        trade for trade in trades
        if str(trade.get("status", "")).upper() == "OPEN"
    ]

    settled_trades = [
        trade for trade in trades
        if str(trade.get("status", "")).upper() == "SETTLED"
    ]

    wins = [
        trade for trade in settled_trades
        if float(trade.get("profit", 0) or 0) > 0
    ]

    losses = [
        trade for trade in settled_trades
        if float(trade.get("profit", 0) or 0) < 0
    ]

    settled_count = len(settled_trades)

    win_rate = (
        len(wins) / settled_count * 100
        if settled_count else 0
    )

    total_profit = float(
        risk.get("total_profit", 0) or 0
    )

    total_fees = float(
        risk.get("total_fees", 0) or 0
    )

    total_slippage = float(
        risk.get("total_slippage", 0) or 0
    )

    decisions = get_decisions(decisions_data)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "mode": "PAPER",

        "account": {
            "starting_balance": STARTING_BALANCE,

            "balance": round(
                float(risk.get("balance", STARTING_BALANCE)), 4
            ),

            "net_profit": round(total_profit, 4),

            "daily_profit": calculate_daily_profit(trades),

            "reserved": round(
                float(risk.get("reserved", 0) or 0), 4
            )
        },

        "performance": {
            "total_trades": len(trades),

            "open_trades": len(open_trades),

            "settled_trades": settled_count,

            "wins": len(wins),

            "losses": len(losses),

            "win_rate": round(win_rate, 2),

            "maximum_drawdown_percent": calculate_drawdown(trades),

            "total_fees": round(total_fees, 4),

            "total_slippage": round(total_slippage, 4)
        },

        "trade_history": build_public_trade_history(trades),

        "rejected_signals": build_public_rejections(decisions)
    }

    save_json(OUTPUT_FILE, output)

    print("\nPERFORMANCE SUMMARY")
    print("Balance:", output["account"]["balance"])
    print("Net profit:", output["account"]["net_profit"])
    print("Win rate:", output["performance"]["win_rate"])
    print("Total trades:", output["performance"]["total_trades"])
    print("Open trades:", output["performance"]["open_trades"])
    print("Settled trades:", output["performance"]["settled_trades"])

    print("\nCreated:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
