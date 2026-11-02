import json
import os
from datetime import datetime, timezone, date

STATE_FILE = "risk_state.json"

STARTING_BALANCE = 100.00
MAX_TRADE = 2.00
MAX_DAILY_LOSS = 5.00


def today():
    return datetime.now(timezone.utc).date().isoformat()


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as file:
                state = json.load(file)

            if "balance" in state and "daily_loss" in state:
                return state

        except (json.JSONDecodeError, OSError):
            print("Warning: Could not read risk state.")

    return {
        "balance": STARTING_BALANCE,
        "daily_loss": 0.00,
        "trade_count": 0,
        "wins": 0,
        "losses": 0,
        "date": today(),
        "total_profit": 0.00,
        "total_fees": 0.00,
        "total_slippage": 0.00
    }


def save_state(state):
    temporary_file = STATE_FILE + ".tmp"

    with open(temporary_file, "w") as file:
        json.dump(state, file, indent=4)

    os.replace(temporary_file, STATE_FILE)


def reset_daily_limits(state):
    current_date = today()

    if state.get("date") != current_date:
        state["date"] = current_date
        state["daily_loss"] = 0.00

        save_state(state)

    return state


def can_trade(
    stake,
    estimated_fee=0.00,
    estimated_slippage=0.00
):
    state = reset_daily_limits(load_state())

    stake = float(stake)
    estimated_fee = float(estimated_fee)
    estimated_slippage = float(estimated_slippage)

    if stake <= 0:
        return False, "Invalid trade amount"

    if stake > MAX_TRADE:
        return False, "Trade exceeds maximum trade limit"

    if estimated_fee < 0 or estimated_slippage < 0:
        return False, "Invalid fee or slippage estimate"

    total_cost = stake + estimated_fee + estimated_slippage

    if total_cost > state["balance"]:
        return False, "Insufficient virtual balance"

    if state["daily_loss"] >= MAX_DAILY_LOSS:
        return False, "Daily loss limit reached"

    if state["daily_loss"] + estimated_fee + estimated_slippage >= MAX_DAILY_LOSS:
        return False, "Trade costs would exceed daily loss limit"

    return True, "Trade approved by risk manager"


def calculate_position_size(
    requested_amount,
    estimated_fee=0.00,
    estimated_slippage=0.00
):
    state = reset_daily_limits(load_state())

    available_balance = state["balance"]

    position = min(
        float(requested_amount),
        MAX_TRADE,
        available_balance
    )

    if position <= 0:
        return 0.00

    approved, reason = can_trade(
        position,
        estimated_fee,
        estimated_slippage
    )

    if not approved:
        print("Position rejected:", reason)
        return 0.00

    return round(position, 2)


def record_result(
    profit,
    fees=0.00,
    slippage=0.00
):
    state = reset_daily_limits(load_state())

    profit = float(profit)
    fees = float(fees)
    slippage = float(slippage)

    net_profit = profit - fees - slippage

    state["balance"] += net_profit
    state["total_profit"] += net_profit
    state["total_fees"] += fees
    state["total_slippage"] += slippage
    state["trade_count"] += 1

    if net_profit > 0:
        state["wins"] += 1

    elif net_profit < 0:
        state["losses"] += 1
        state["daily_loss"] += abs(net_profit)

    save_state(state)

    return {
        "net_profit": round(net_profit, 4),
        "balance": round(state["balance"], 2),
        "daily_loss": round(state["daily_loss"], 2)
    }


def get_status():
    state = reset_daily_limits(load_state())

    total_trades = state["trade_count"]

    win_rate = (
        (state["wins"] / total_trades) * 100
        if total_trades > 0
        else 0
    )

    return {
        "mode": "PAPER",
        "balance": round(state["balance"], 2),
        "starting_balance": STARTING_BALANCE,
        "maximum_trade": MAX_TRADE,
        "daily_loss": round(state["daily_loss"], 2),
        "maximum_daily_loss": MAX_DAILY_LOSS,
        "trades": total_trades,
        "wins": state["wins"],
        "losses": state["losses"],
        "win_rate": round(win_rate, 2),
        "total_profit": round(state["total_profit"], 2),
        "total_fees": round(state["total_fees"], 2),
        "total_slippage": round(state["total_slippage"], 2)
    }


if __name__ == "__main__":
    print("=" * 45)
    print("PAPER TRADING RISK MANAGER")
    print("=" * 45)

    status = get_status()

    for key, value in status.items():
        print(f"{key}: {value}")

    print("=" * 45)

    approved, reason = can_trade(2.00)

    print("Test trade:", reason)
    print("Real trading: DISABLED")
