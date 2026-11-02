import json
import os
import requests

from datetime import datetime, timezone

from paper_trader import PaperTrader


# ==========================================
# STRATEGY CONFIGURATION
# ==========================================

MIN_ELAPSED_SECONDS = 0

MIN_ENTRY_PRICE = 0.70

MAX_ELAPSED_SECONDS = 270

MIN_MOMENTUM_PERCENT = 0.05

PAPER_TRADE_AMOUNT = 2.00

# Live momentum confirmation
LIVE_MOMENTUM_REQUIRED_SECONDS = 30

LIVE_MOMENTUM_MIN_WINDOW = 25

LIVE_MOMENTUM_MAX_WINDOW = 40

LIVE_PRICE_MAX_AGE_SECONDS = 15

API_URL = "https://api.predict.fun"

PREDICT_API_KEY = os.getenv("PREDICT_API_KEY")


# ==========================================
# JSON FUNCTIONS
# ==========================================

def load_json(filename):

    with open(filename, "r") as file:
        return json.load(file)


# ==========================================
# EMA CALCULATION
# ==========================================

def calculate_ema(prices, period):

    multiplier = 2 / (period + 1)

    ema = prices[0]

    for price in prices[1:]:

        ema = (
            price * multiplier
        ) + (
            ema * (1 - multiplier)
        )

    return ema


# ==========================================
# MARKET STARTING PRICE
# ==========================================

def extract_start_price(data):

    if not isinstance(data, dict):
        return None

    candidates = [

        data.get("crypto_start_price"),

        data.get("start_price"),

        data.get("startPrice")

    ]

    for key in [
        "variantData",
        "variantDetails",
        "variant_data"
    ]:

        variant = data.get(key)

        if isinstance(variant, dict):

            candidates.extend([

                variant.get("startPrice"),

                variant.get("start_price"),

                variant.get("crypto_start_price")

            ])

    for value in candidates:

        if value is None:
            continue

        try:

            price = float(value)

            if price > 0:
                return price

        except (ValueError, TypeError):
            continue

    return None


def fetch_market_start_price(market_id):

    if not PREDICT_API_KEY:

        return None, "Predict.fun API key unavailable"

    url = f"{API_URL}/v1/markets/{market_id}"

    headers = {

        "x-api-key": PREDICT_API_KEY,

        "accept": "application/json"

    }

    try:

        response = requests.get(

            url,

            headers=headers,

            timeout=15

        )

        response.raise_for_status()

        data = response.json()

        possible_objects = [data]

        if isinstance(data, dict):

            for key in ["data", "market", "result"]:

                nested = data.get(key)

                if isinstance(nested, dict):
                    possible_objects.append(nested)

        for obj in possible_objects:

            price = extract_start_price(obj)

            if price is not None:

                return price, "PREDICT_FUN_LIVE_API"

        return None, "Starting price not published yet"

    except requests.RequestException as error:

        return None, f"Predict.fun API request failed: {error}"

    except (ValueError, TypeError) as error:

        return None, f"Invalid Predict.fun response: {error}"


def find_market_start_price(market, raw_market):

    price = extract_start_price(market)

    if price is not None:

        return price, "SAVED_ORDERBOOK_DATA"

    price = extract_start_price(raw_market)

    if price is not None:

        return price, "SAVED_MARKET_DATA"

    market_id = market.get("market_id")

    if not market_id:

        return None, "Market ID unavailable"

    print(
        f"Starting price missing for market {market_id}. "
        "Requesting fresh Predict.fun market data..."
    )

    price, source = fetch_market_start_price(market_id)

    if price is not None:

        print("Starting BTC price retrieved:", price)

        return price, source

    print("Starting price retrieval:", source)

    return None, source


# ==========================================
# LIVE MOMENTUM VALIDATION
# ==========================================

def validate_live_momentum(live_momentum):

    if not isinstance(live_momentum, dict):

        return False, "30-second live momentum data unavailable", {}

    if not live_momentum.get("available"):

        return False, live_momentum.get(
            "reason",
            "30-second momentum not available"
        ), {}

    direction = live_momentum.get("direction")

    if direction not in ["UP", "DOWN"]:

        return False, "Live BTC momentum is FLAT or invalid", {}

    try:

        movement = float(
            live_momentum["movement_percent"]
        )

        window = float(
            live_momentum["window_seconds"]
        )

        current_price = float(
            live_momentum["current_price"]
        )

        timestamp = int(
            live_momentum["current_timestamp"]
        )

    except (KeyError, ValueError, TypeError):

        return False, "Invalid live momentum measurements", {}

    if current_price <= 0:

        return False, "Invalid live BTC price", {}

    if not (
        LIVE_MOMENTUM_MIN_WINDOW
        <= window
        <= LIVE_MOMENTUM_MAX_WINDOW
    ):

        return False, (
            "Live momentum measurement window is outside "
            "the permitted range"
        ), {}

    now_ms = int(
        datetime.now(timezone.utc).timestamp() * 1000
    )

    age_seconds = (now_ms - timestamp) / 1000

    if age_seconds < -2:

        return False, "Live BTC timestamp is in the future", {}

    if age_seconds > LIVE_PRICE_MAX_AGE_SECONDS:

        return False, "Live BTC momentum data is stale", {}

    if direction == "UP" and movement <= 0:

        return False, "Invalid UP momentum measurement", {}

    if direction == "DOWN" and movement >= 0:

        return False, "Invalid DOWN momentum measurement", {}

    diagnostics = {

        "live_momentum_direction": direction,

        "live_momentum_percent": round(movement, 6),

        "live_momentum_window_seconds": round(window, 2),

        "live_momentum_current_price": current_price,

        "live_momentum_data_age_seconds": round(
            age_seconds,
            2
        )

    }

    return True, "30-second live momentum confirmed", diagnostics


# ==========================================
# CANDLE MOMENTUM ANALYSIS
# ==========================================

def analyse_momentum(candles, current_price=None):

    if len(candles) < 30:

        return None, "Not enough completed BTC candles", {}

    closes = [

        float(candle["close"])

        for candle in candles

    ]

    ema9 = calculate_ema(closes[-30:], 9)

    ema21 = calculate_ema(closes[-30:], 21)

    latest_close = closes[-1]

    previous_close = closes[-4]

    movement = (

        (latest_close - previous_close) / previous_close

    ) * 100

    live_difference = None

    if current_price is not None:

        live_difference = (

            (float(current_price) - latest_close) / latest_close

        ) * 100

    diagnostics = {

        "ema9": round(ema9, 2),

        "ema21": round(ema21, 2),

        "latest_completed_close": round(latest_close, 2),

        "three_candle_start_close": round(previous_close, 2),

        "three_candle_movement_percent": round(movement, 5),

        "live_btc_price": current_price,

        "live_vs_last_close_percent": (

            round(live_difference, 5)

            if live_difference is not None else None

        )

    }

    if (

        ema9 > ema21

        and latest_close > ema9

        and movement >= MIN_MOMENTUM_PERCENT

    ):

        return "UP", "Strong UP candle momentum confirmed", diagnostics

    if (

        ema9 < ema21

        and latest_close < ema9

        and movement <= -MIN_MOMENTUM_PERCENT

    ):

        return "DOWN", "Strong DOWN candle momentum confirmed", diagnostics

    if ema9 > ema21 and latest_close > ema9:

        return None, "UP candle momentum is too weak", diagnostics

    if ema9 < ema21 and latest_close < ema9:

        return None, "DOWN candle momentum is too weak", diagnostics

    return None, "No clear directional candle momentum", diagnostics


# ==========================================
# MARKET EVALUATION
# ==========================================

def evaluate_market(
    market,
    raw_market,
    candles,
    current_price,
    live_momentum
):

    now = datetime.now(timezone.utc)

    start = datetime.fromisoformat(

        market["starts_at"].replace("Z", "+00:00")

    )

    end = datetime.fromisoformat(

        market["ends_at"].replace("Z", "+00:00")

    )

    elapsed = (now - start).total_seconds()

    if not (start <= now < end):

        return None, "Market is not active", {}

    if elapsed < MIN_ELAPSED_SECONDS:

        return None, "Waiting for market activation", {}

    if elapsed >= MAX_ELAPSED_SECONDS:

        return None, "Market is too close to settlement", {}

    market_start_price, price_source = find_market_start_price(

        market,

        raw_market

    )

    if market_start_price is None:

        return None, (

            f"Market starting BTC price unavailable: {price_source}"

        ), {

            "price_source": price_source

        }

    if current_price is None:

        return None, "Current BTC price unavailable", {}

    current_price = float(current_price)

    if current_price > market_start_price:

        price_direction = "UP"

    elif current_price < market_start_price:

        price_direction = "DOWN"

    else:

        return None, "BTC is exactly at market starting price", {}

    # First evaluate completed candle momentum.
    direction, momentum_reason, diagnostics = analyse_momentum(

        candles,

        current_price

    )

    diagnostics["market_start_price"] = market_start_price

    diagnostics["current_btc_price"] = current_price

    diagnostics["direction_vs_start_price"] = price_direction

    diagnostics["start_price_source"] = price_source

    if direction is None:

        return None, momentum_reason, diagnostics

    # Validate the separate 30-second live momentum measurement.
    live_valid, live_reason, live_diagnostics = validate_live_momentum(
        live_momentum
    )

    diagnostics.update(live_diagnostics)

    if not live_valid:

        return None, live_reason, diagnostics

    # Candle direction and live direction must agree.
    live_direction = live_momentum["direction"]

    if direction != live_direction:

        return None, (
            "Live 30-second momentum conflicts with candle momentum"
        ), diagnostics

    # Both momentum measurements must agree with market direction.
    if direction != price_direction:

        return None, (
            "Momentum conflicts with market starting-price direction"
        ), diagnostics

    # Select the actual outcome buying price.
    if direction == "UP":

        entry_price = market.get("up_ask")

        available_size = market.get("up_ask_size")

    else:

        entry_price = market.get("down_ask")

        available_size = market.get("down_ask_size")

    if entry_price is None:

        return None, "Actual outcome buying price unavailable", diagnostics

    entry_price = float(entry_price)

    if not 0 < entry_price < 1:

        return None, "Invalid outcome buying price", diagnostics

    if entry_price < MIN_ENTRY_PRICE:

        return None, (

            f"{direction} price is {entry_price:.2f}; "

            "waiting for at least 0.70"

        ), diagnostics

    if available_size is None or float(available_size) <= 0:

        return None, "Insufficient visible liquidity", diagnostics

    required_shares = PAPER_TRADE_AMOUNT / entry_price

    if float(available_size) < required_shares:

        return None, (

            "Visible order-book size is insufficient "

            "for the simulated trade"

        ), diagnostics

    decision = {

        "market_id": market["market_id"],

        "market_title": market["title"],

        "direction": direction,

        "entry_price": entry_price,

        "available_size": float(available_size),

        "required_shares": round(required_shares, 8),

        "market_start_price": market_start_price,

        "start_price_source": price_source,

        "current_btc_price": current_price,

        "price_direction": price_direction,

        "elapsed_seconds": round(elapsed, 2),

        "remaining_seconds": round(

            (end - now).total_seconds(), 2

        ),

        "momentum_reason": momentum_reason,

        "live_momentum": live_diagnostics,

        "fee_rate_bps": market.get("fee_rate_bps"),

        "decision": "PAPER_TRADE_CANDIDATE"

    }

    return decision, "All entry conditions passed", diagnostics


# ==========================================
# FEE ESTIMATION
# ==========================================

def estimate_fee(market, stake):

    fee_rate_bps = market.get("fee_rate_bps")

    if fee_rate_bps is None:

        return None

    try:

        fee_rate_bps = float(fee_rate_bps)

        if fee_rate_bps < 0:
            return None

        return round(

            stake * fee_rate_bps / 10000,

            4

        )

    except (ValueError, TypeError):

        return None


# ==========================================
# PAPER TRADE EXECUTION
# ==========================================

def execute_paper_trade(decision, market, paper_trader):

    print("\nPAPER TRADE EXECUTION")

    print("-" * 45)

    stake = PAPER_TRADE_AMOUNT

    fee = estimate_fee(market, stake)

    if fee is None:

        return {

            "status": "REJECTED",

            "reason": "Market fee information unavailable"

        }

    slippage = 0.00

    print("Market:", decision["market_title"])

    print("Direction:", decision["direction"])

    print("Entry price:", decision["entry_price"])

    print("Stake:", stake)

    print("Estimated fee:", fee)

    print("Estimated slippage:", slippage)

    print("Live momentum:", decision["live_momentum"])

    print("Mode: PAPER")

    result = paper_trader.open_trade(

        market_id=decision["market_id"],

        title=decision["market_title"],

        side=decision["direction"],

        price=decision["entry_price"],

        stake=stake,

        estimated_fee=fee,

        estimated_slippage=slippage

    )

    if isinstance(result, dict) and result.get("error"):

        print("PAPER TRADE REJECTED:", result["error"])

        return {

            "status": "REJECTED",

            "reason": result["error"]

        }

    print("PAPER TRADE OPENED")

    print("Trade ID:", result["trade_id"])

    print("Shares:", result["shares"])

    return {

        "status": "OPEN",

        "trade_id": result["trade_id"],

        "side": result["side"],

        "entry_price": result["entry_price"],

        "stake": result["stake"],

        "shares": result["shares"],

        "estimated_fee": result["estimated_fee"],

        "reserved_total": result["reserved_total"]

    }


# ==========================================
# MAIN ENGINE
# ==========================================

def main():

    print("=" * 50)

    print("BTC 5-MINUTE STRATEGY ENGINE")

    print("=" * 50)

    orderbook_data = load_json("orderbooks.json")

    price_data = load_json("btc_price_data.json")

    raw_market_data = load_json("market_data.json")

    markets = orderbook_data.get("orderbooks", [])

    candles = price_data.get("candles", [])

    current_price = price_data.get("current_price")

    live_momentum = price_data.get("live_momentum", {})

    raw_markets = raw_market_data.get("markets", [])

    raw_market_lookup = {

        str(market.get("id", market.get("market_id"))): market

        for market in raw_markets

    }

    paper_trader = PaperTrader()

    results = []

    candidates = []

    opened_trades = []

    for market in markets:

        market_id = str(market.get("market_id"))

        raw_market = raw_market_lookup.get(market_id, {})

        decision, reason, diagnostics = evaluate_market(

            market,

            raw_market,

            candles,

            current_price,

            live_momentum

        )

        result = {

            "market_id": market_id,

            "title": market.get("title"),

            "decision": "NO TRADE",

            "reason": reason,

            "momentum_diagnostics": diagnostics

        }

        if decision:

            candidates.append(decision)

            result.update(decision)

            result["decision"] = "PAPER_TRADE_CANDIDATE"

            trade_result = execute_paper_trade(

                decision,

                market,

                paper_trader

            )

            result["paper_trade"] = trade_result

            if trade_result["status"] == "OPEN":

                result["decision"] = "PAPER_TRADE_OPEN"

                opened_trades.append(trade_result)

        results.append(result)

        print("\nMarket:", market.get("title"))

        print("Decision:", result["decision"])

        print("Reason:", reason)

        if diagnostics:

            print(

                "Market starting BTC price:",

                diagnostics.get("market_start_price")

            )

            print(

                "Current BTC price:",

                diagnostics.get("current_btc_price")

            )

            print(

                "Direction relative to starting price:",

                diagnostics.get("direction_vs_start_price")

            )

            print(

                "Starting price source:",

                diagnostics.get("start_price_source")

            )

            print(

                "30-second momentum direction:",

                diagnostics.get("live_momentum_direction")

            )

            print(

                "30-second momentum movement:",

                diagnostics.get("live_momentum_percent")

            )

    output = {

        "updated_at": datetime.now(timezone.utc).isoformat(),

        "mode": "PAPER",

        "real_trading_enabled": False,

        "markets_checked": len(markets),

        "candidates_found": len(candidates),

        "paper_trades_opened": len(opened_trades),

        "results": results

    }

    with open("strategy_decisions.json", "w") as file:

        json.dump(output, file, indent=2)

    print("\n" + "=" * 50)

    print("MARKETS CHECKED:", len(markets))

    print("PAPER CANDIDATES:", len(candidates))

    print("PAPER TRADES OPENED:", len(opened_trades))

    print("REAL TRADING: DISABLED")

    print("Results saved to strategy_decisions.json")

    print("=" * 50)

    print("\nPAPER ACCOUNT STATUS")

    for key, value in paper_trader.get_status().items():

        print(f"{key}: {value}")


if __name__ == "__main__":

    main()
