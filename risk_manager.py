import json
import os
from datetime import datetime, timezone

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

            required = [
                "balance",
                "reserved",
                "daily_loss",
                "trade_count"
            ]

            if all(key in state for key in required):
                return state

        except (json.JSONDecodeError, OSError):
            print("Warning: Risk state could not be loaded.")

    return {
        "balance": STARTING_BALANCE,
        "reserved": 0.00,
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
    if state.get("date") != today():
        state["date"] = today()
        state["daily_loss"] = 0.00
        save_state(state)

    return state


def can_trade(stake, estimated_fee=0.00, estimated_slippage=0.00):
    state = reset_daily_limits(load_state())

    stake = float(stake)
    fee = float(estimated_fee)
    slippage = float(estimated_slippage)

    if stake <= 0:
        return False, "Invalid trade amount"

    if stake > MAX_TRADE:
        return False, "Maximum trade limit exceeded"

    if fee < 0 or slippage < 0:
        return False, "Invalid cost estimate"

    total_cost = stake + fee + slippage

    available = state["balance"] - state["reserved"]

    if total_cost > available:
        return False, "Insufficient virtual balance"

    if state["daily_loss"] >= MAX_DAILY_LOSS:
        return False, "Daily loss limit reached"

    if state["daily_loss"] + total_cost > MAX_DAILY_LOSS:
        return False, "Trade exceeds remaining daily risk limit"

    return True, "Trade approved"


def reserve_trade(stake, estimated_fee=0.00, estimated_slippage=0.00):
    approved, reason = can_trade(
        stake,
        estimated_fee,
        estimated_slippage
    )

    if not approved:
        return False, reason

    state = reset_daily_limits(load_state())

    amount = (
        float(stake)
        + float(estimated_fee)
        + float(estimated_slippage)
    )

    state["balance"] -= amount
    state["reserved"] += amount

    save_state(state)

    return True, "Virtual funds reserved"


def settle_reserved_trade(
    stake,
    payout,
    fees=0.00,
    slippage=0.00
):
    state = reset_daily_limits(load_state())

    stake = float(stake)
    payout = float(payout)
    fees = float(fees)
    slippage = float(slippage)

    if min(stake, payout, fees, slippage) < 0:
        return False, "Invalid settlement values"

    reserved_amount = stake + fees + slippage

    if reserved_amount > state["reserved"] + 0.000001:
        return False, "Reserved amount mismatch"

    state["reserved"] -= reserved_amount

    # Return the gross payout to available virtual funds.
    state["balance"] += payout

    net_profit = payout - stake - fees - slippage

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

    return True, {
        "net_profit": round(net_profit, 4),
        "balance": round(state["balance"], 2),
        "daily_loss": round(state["daily_loss"], 2)
    }


def get_status():
    state = reset_daily_limits(load_state())

    total = state["trade_count"]

    win_rate = (
        state["wins"] / total * 100
        if total else 0
    )

    return {
        "mode": "PAPER",
        "balance": round(state["balance"], 2),
        "reserved": round(state["reserved"], 2),
        "available_balance": round(
            state["balance"] - state["reserved"], 2
        ),
        "maximum_trade": MAX_TRADE,
        "daily_loss": round(state["daily_loss"], 2),
        "maximum_daily_loss": MAX_DAILY_LOSS,
        "trades": total,
        "wins": state["wins"],
        "losses": state["losses"],
        "win_rate": round(win_rate, 2),
        "total_profit": round(state["total_profit"], 2),
        "total_fees": round(state["total_fees"], 2),
        "total_slippage": round(state["total_slippage"], 2)
    }


if __name__ == "__main__":
    print("PAPER TRADING RISK MANAGER")
    print("-------------------------")

    for key, value in get_status().items():
        print(f"{key}: {value}")

    print("\nReal trading: DISABLED")
