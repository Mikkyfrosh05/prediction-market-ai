import json
from datetime import datetime, timezone

MIN_ELAPSED_SECONDS = 150
MIN_ENTRY_PRICE = 0.70
MAX_ELAPSED_SECONDS = 300
MIN_MOMENTUM_PERCENT = 0.05


def load_json(filename):
    with open(filename, "r") as file:
        return json.load(file)


def calculate_ema(prices, period):
    multiplier = 2 / (period + 1)
    ema = prices[0]

    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return ema


def find_market_start_price(market, raw_market):
    """
    Finds the BTC starting price from the Predict.fun market data.
    """

    candidates = [
        market.get("crypto_start_price"),
        market.get("start_price"),
        market.get("startPrice"),
        raw_market.get("crypto_start_price"),
        raw_market.get("start_price"),
        raw_market.get("startPrice")
    ]

    for source in [market, raw_market]:
        for key in ["variantData", "variantDetails", "variant_data"]:
            variant = source.get(key)

            if isinstance(variant, dict):
                candidates.extend([
                    variant.get("startPrice"),
                    variant.get("start_price")
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


def analyse_momentum(candles, current_price=None):

    if len(candles) < 30:
        return None, "Not enough completed BTC candles", {}

    closes = [float(candle["close"]) for candle in candles]

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
        return "UP", "Strong UP momentum confirmed", diagnostics

    if (
        ema9 < ema21
        and latest_close < ema9
        and movement <= -MIN_MOMENTUM_PERCENT
    ):
        return "DOWN", "Strong DOWN momentum confirmed", diagnostics

    if ema9 > ema21 and latest_close > ema9:
        return None, "UP momentum is too weak", diagnostics

    if ema9 < ema21 and latest_close < ema9:
        return None, "DOWN momentum is too weak", diagnostics

    return None, "No clear directional momentum", diagnostics


def evaluate_market(market, raw_market, candles, current_price):

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
        return None, "Waiting for at least 2 minutes 30 seconds", {}

    if elapsed >= MAX_ELAPSED_SECONDS:
        return None, "Market is too close to settlement", {}

    # Get the actual market starting price.
    market_start_price = find_market_start_price(
        market,
        raw_market
    )

    if market_start_price is None:
        return None, "Market starting BTC price unavailable", {}

    # Compare current BTC price with market starting price.
    if current_price is None:
        return None, "Current BTC price unavailable", {}

    current_price = float(current_price)

    if current_price > market_start_price:
        price_direction = "UP"

    elif current_price < market_start_price:
        price_direction = "DOWN"

    else:
        return None, "BTC is exactly at market starting price", {}

    direction, momentum_reason, diagnostics = analyse_momentum(
        candles,
        current_price
    )

    diagnostics["market_start_price"] = market_start_price
    diagnostics["current_btc_price"] = current_price
    diagnostics["direction_vs_start_price"] = price_direction

    if direction is None:
        return None, momentum_reason, diagnostics

    # Require momentum and starting-price direction to agree.
    if direction != price_direction:
        return None, (
            "Momentum conflicts with market starting-price direction"
        ), diagnostics

    # Get the actual Predict.fun buying price.
    if direction == "UP":
        entry_price = market.get("up_ask")
        available_size = market.get("up_ask_size")

    else:
        entry_price = market.get("down_ask")
        available_size = market.get("down_ask_size")

    if entry_price is None:
        return None, "Actual outcome buying price unavailable", diagnostics

    entry_price = float(entry_price)

    if entry_price < MIN_ENTRY_PRICE:
        return None, (
            f"{direction} price is {entry_price:.2f}; "
            "waiting for at least 0.70"
        ), diagnostics

    if available_size is None or float(available_size) <= 0:
        return None, "Insufficient visible liquidity", diagnostics

    decision = {
        "market_id": market["market_id"],
        "market_title": market["title"],
        "direction": direction,
        "entry_price": entry_price,
        "available_size": float(available_size),
        "market_start_price": market_start_price,
        "current_btc_price": current_price,
        "price_direction": price_direction,
        "elapsed_seconds": round(elapsed, 2),
        "remaining_seconds": round((end - now).total_seconds(), 2),
        "momentum_reason": momentum_reason,
        "fee_rate_bps": market.get("fee_rate_bps"),
        "decision": "PAPER_TRADE_CANDIDATE"
    }

    return decision, "All entry conditions passed", diagnostics


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

    raw_markets = raw_market_data.get("markets", [])

    raw_market_lookup = {
        str(market.get("id", market.get("market_id"))): market
        for market in raw_markets
    }

    results = []
    candidates = []

    for market in markets:

        market_id = str(market.get("market_id"))

        raw_market = raw_market_lookup.get(market_id, {})

        decision, reason, diagnostics = evaluate_market(
            market,
            raw_market,
            candles,
            current_price
        )

        result = {
            "market_id": market_id,
            "title": market.get("title"),
            "decision": "NO TRADE",
            "reason": reason,
            "momentum_diagnostics": diagnostics
        }

        if decision:

            result.update(decision)
            result["decision"] = "PAPER_TRADE_CANDIDATE"

            candidates.append(decision)

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

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "PAPER",
        "real_trading_enabled": False,
        "markets_checked": len(markets),
        "candidates_found": len(candidates),
        "results": results
    }

    with open("strategy_decisions.json", "w") as file:
        json.dump(output, file, indent=2)

    print("\n" + "=" * 50)
    print("MARKETS CHECKED:", len(markets))
    print("PAPER CANDIDATES:", len(candidates))
    print("REAL TRADING: DISABLED")
    print("Results saved to strategy_decisions.json")
    print("=" * 50)


if __name__ == "__main__":
    main()
