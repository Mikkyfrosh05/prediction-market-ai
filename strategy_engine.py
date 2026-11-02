import json
from datetime import datetime, timezone


MIN_ELAPSED_SECONDS = 150
MIN_ENTRY_PRICE = 0.70
MAX_ELAPSED_SECONDS = 300

def load_json(filename):
    with open(filename, "r") as file:
        return json.load(file)


def calculate_ema(prices, period):
    multiplier = 2 / (period + 1)
    ema = prices[0]

    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return ema


def analyse_momentum(candles):
    if len(candles) < 30:
        return None, "Not enough completed BTC candles"

    closes = [float(candle["close"]) for candle in candles]

    ema9 = calculate_ema(closes[-30:], 9)
    ema21 = calculate_ema(closes[-30:], 21)

    latest_close = closes[-1]
    previous_close = closes[-4]

    momentum = ((latest_close - previous_close) / previous_close) * 100

    if ema9 > ema21 and latest_close > ema9 and momentum > 0:
        return "UP", "EMA and short-term momentum confirm UP"

    if ema9 < ema21 and latest_close < ema9 and momentum < 0:
        return "DOWN", "EMA and short-term momentum confirm DOWN"

    return None, "No clear directional momentum"


def evaluate_market(market, candles):
    now = datetime.now(timezone.utc)

    start = datetime.fromisoformat(
        market["starts_at"].replace("Z", "+00:00")
    )

    end = datetime.fromisoformat(
        market["ends_at"].replace("Z", "+00:00")
    )

    elapsed = (now - start).total_seconds()

    if not (start <= now < end):
        return None, "Market is not active"

    if elapsed < MIN_ELAPSED_SECONDS:
        return None, "Waiting for at least 2 minutes 30 seconds"

    if elapsed >= MAX_ELAPSED_SECONDS:
        return None, "Market is too close to settlement"

    direction, momentum_reason = analyse_momentum(candles)

    if direction is None:
        return None, momentum_reason

    if direction == "UP":
        entry_price = market.get("up_ask")
        available_size = market.get("up_ask_size")
    else:
        entry_price = market.get("down_ask")
        available_size = market.get("down_ask_size")

    if entry_price is None:
        return None, "Actual outcome buying price unavailable"

    entry_price = float(entry_price)

    if entry_price < MIN_ENTRY_PRICE:
        return None, (
            f"{direction} price is {entry_price:.2f}; "
            "waiting for at least 0.70"
        )

    if available_size is None or float(available_size) <= 0:
        return None, "Insufficient visible liquidity"

    decision = {
        "market_id": market["market_id"],
        "market_title": market["title"],
        "direction": direction,
        "entry_price": entry_price,
        "available_size": float(available_size),
        "elapsed_seconds": round(elapsed, 2),
        "remaining_seconds": round(
            (end - now).total_seconds(), 2
        ),
        "momentum_reason": momentum_reason,
        "fee_rate_bps": market.get("fee_rate_bps"),
        "decision": "PAPER_TRADE_CANDIDATE"
    }

    return decision, "All initial entry conditions passed"


def main():
    print("=" * 50)
    print("BTC 5-MINUTE STRATEGY ENGINE")
    print("=" * 50)

    orderbook_data = load_json("orderbooks.json")
    price_data = load_json("btc_price_data.json")

    markets = orderbook_data.get("orderbooks", [])
    candles = price_data.get("candles", [])

    results = []
    candidates = []

    for market in markets:
        decision, reason = evaluate_market(market, candles)

        result = {
            "market_id": market.get("market_id"),
            "title": market.get("title"),
            "decision": "NO TRADE",
            "reason": reason
        }

        if decision:
            result.update(decision)
            result["decision"] = "PAPER_TRADE_CANDIDATE"
            candidates.append(decision)

        results.append(result)

        print("\nMarket:", market.get("title"))
        print("Decision:", result["decision"])
        print("Reason:", reason)

        if decision:
            print("Direction:", decision["direction"])
            print("Entry price:", decision["entry_price"])

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
