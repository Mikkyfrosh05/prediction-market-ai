import json
import os
from datetime import datetime, timezone

STATE_FILE = "risk_state.json"

STARTING_BALANCE = 100.00
MAX_TRADE = 2.00
MAX_DAILY_LOSS = 5.00


def today():
    return datetime.now(timezone.utc).date().isoformat()


def default_state():
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


def load_state():

    if os.path.exists(STATE_FILE):

        try:
            with open(STATE_FILE, "r") as file:
                state = json.load(file)

            if "balance" not in state:
                raise ValueError("Missing balance")

            # Preserve existing balances and migrate old state files.
            defaults = default_state()

            for key, value in defaults.items():
                state.setdefault(key, value)

            return state

        except (json.JSONDecodeError, OSError, ValueError):
            print("Warning: Risk state could not be loaded.")
            raise RuntimeError(
                "Risk state is invalid. Do not trade until it is checked."
            )

    state = default_state()
    save_state(state)

    return state


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

    try:
        stake = float(stake)
        estimated_fee = float(estimated_fee)
        estimated_slippage = float(estimated_slippage)

    except (ValueError, TypeError):
        return False, "Invalid trade values"

    if not all(
        map(
            lambda value: value == value and abs(value) != float("inf"),
            [stake, estimated_fee, estimated_slippage]
        )
    ):
        return False, "Trade values must be finite numbers"

    state = reset_daily_limits(load_state())

    if stake <= 0:
        return False, "Invalid trade amount"

    if stake > MAX_TRADE:
        return False, "Trade exceeds maximum trade limit"

    if estimated_fee < 0 or estimated_slippage < 0:
        return False, "Invalid fee or slippage estimate"

    total_cost = stake + estimated_fee + estimated_slippage

    if total_cost > state["balance"]:
        return False, "Insufficient virtual balance"

    # Include existing open-trade exposure.
    total_exposure = (
        state["daily_loss"]
        + state["reserved"]
        + total_cost
    )

    if total_exposure > MAX_DAILY_LOSS:
        return False, "Daily loss/exposure limit reached"

    return True, "Trade approved by risk manager"


def calculate_position_size(
    requested_amount,
    estimated_fee=0.00,
    estimated_slippage=0.00
):

    try:
        requested_amount = float(requested_amount)

    except (ValueError, TypeError):
        return 0.00

    state = reset_daily_limits(load_state())

    position = min(
        requested_amount,
        MAX_TRADE,
        state["balance"]
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


def reserve_trade(
    stake,
    estimated_fee=0.00,
    estimated_slippage=0.00
):

    approved, reason = can_trade(
        stake,
        estimated_fee,
        estimated_slippage
    )

    if not approved:
        return {"error": reason}

    state = reset_daily_limits(load_state())

    stake = float(stake)
    estimated_fee = float(estimated_fee)
    estimated_slippage = float(estimated_slippage)

    total_cost = stake + estimated_fee + estimated_slippage

    if total_cost > state["balance"]:
        return {"error": "Insufficient virtual balance"}

    # Deduct the full cost immediately.
    state["balance"] = round(
        state["balance"] - total_cost, 4
    )

    # Track funds committed to open trades.
    state["reserved"] = round(
        state["reserved"] + total_cost, 4
    )

    save_state(state)

    return {
        "success": True,
        "reserved": round(total_cost, 4),
        "balance": round(state["balance"], 4)
    }


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
        return {"error": "Invalid settlement values"}

    total_reserved = stake + fees + slippage

    if state["reserved"] + 0.0001 < total_reserved:
        return {"error": "Insufficient reserved funds"}

    # Release the reservation.
    state["reserved"] = round(
        max(0.00, state["reserved"] - total_reserved), 4
    )

    # Add the payout. Stake and costs were already deducted.
    state["balance"] = round(
        state["balance"] + payout, 4
    )

    net_profit = payout - total_reserved

    state["total_profit"] = round(
        state["total_profit"] + net_profit, 4
    )

    state["total_fees"] = round(
        state["total_fees"] + fees, 4
    )

    state["total_slippage"] = round(
        state["total_slippage"] + slippage, 4
    )

    state["trade_count"] += 1

    if net_profit > 0:
        state["wins"] += 1

    elif net_profit < 0:
        state["losses"] += 1

    # Daily net loss: wins reduce accumulated daily losses.
    state["daily_loss"] = round(
        max(0.00, state["daily_loss"] - net_profit), 4
    )

    save_state(state)

    return {
        "success": True,
        "net_profit": round(net_profit, 4),
        "balance": round(state["balance"], 4),
        "reserved": round(state["reserved"], 4),
        "daily_loss": round(state["daily_loss"], 4)
    }


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

    state["balance"] = round(
        state["balance"] + net_profit, 4
    )

    state["total_profit"] = round(
        state["total_profit"] + net_profit, 4
    )

    state["total_fees"] = round(
        state["total_fees"] + fees, 4
    )

    state["total_slippage"] = round(
        state["total_slippage"] + slippage, 4
    )

    state["trade_count"] += 1

    if net_profit > 0:
        state["wins"] += 1

    elif net_profit < 0:
        state["losses"] += 1

    state["daily_loss"] = round(
        max(0.00, state["daily_loss"] - net_profit), 4
    )

    save_state(state)

    return {
        "net_profit": round(net_profit, 4),
        "balance": round(state["balance"], 4),
        "daily_loss": round(state["daily_loss"], 4)
    }


def get_status():

    state = reset_daily_limits(load_state())

    total_trades = state["trade_count"]

    win_rate = (
        state["wins"] / total_trades * 100
        if total_trades > 0
        else 0
    )

    return {
        "mode": "PAPER",
        "balance": round(state["balance"], 2),
        "reserved": round(state["reserved"], 2),
        "available_balance": round(state["balance"], 2),
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
    print("Real trading: DISABLED")
