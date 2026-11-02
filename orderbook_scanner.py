import json
import os
import requests
import traceback

from datetime import datetime, timezone

from config import CONFIG
from market_scanner import get_markets


API_URL = f"{CONFIG['API_URL']}/v1/markets"

API_KEY = os.environ.get("PREDICT_API_KEY")

if not API_KEY:
    raise ValueError("PREDICT_API_KEY is missing!")

HEADERS = {
    "x-api-key": API_KEY
}


def get_orderbook(market_id):

    url = f"{API_URL}/{market_id}/orderbook"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise Exception("Orderbook request failed")

    return result["data"]


def get_outcome_price(outcomes, outcome_name):

    for outcome in outcomes:

        name = outcome.get("name", "").strip().upper()

        if name != outcome_name.upper():
            continue

        best_bid = outcome.get("bestBid") or {}
        best_ask = outcome.get("bestAsk") or {}

        return {

            "bid": float(best_bid["price"])
            if best_bid.get("price") is not None
            else None,

            "ask": float(best_ask["price"])
            if best_ask.get("price") is not None
            else None,

            "bid_size": float(best_bid.get("size", 0)),

            "ask_size": float(best_ask.get("size", 0))

        }

    return {
        "bid": None,
        "ask": None,
        "bid_size": 0,
        "ask_size": 0
    }


def scan_markets():

    markets = get_markets()

    now = datetime.now(timezone.utc)

    scanned = []

    print("\nBTC OUTCOME ORDERBOOK SCANNER")
    print("----------------------------")

    for market in markets:

        market_id = market.get("id")

        if market_id is None:
            continue

        try:

            # Read actual UP and DOWN outcome prices
            outcomes = market.get("outcomes", [])

            up = get_outcome_price(
                outcomes,
                "UP"
            )

            down = get_outcome_price(
                outcomes,
                "DOWN"
            )

            # Fetch orderbook for additional market information
            book = get_orderbook(market_id)

            start = datetime.fromisoformat(
                market["startsAt"].replace("Z", "+00:00")
            )

            end = datetime.fromisoformat(
                market["endsAt"].replace("Z", "+00:00")
            )

            elapsed_seconds = (
                now - start
            ).total_seconds()

            remaining_seconds = (
                end - now
            ).total_seconds()

            active = start <= now < end

            item = {

                "market_id": market_id,

                "title": market.get("title"),

                "asset": "BTC",

                "timeframe": "5 minutes",

                "starts_at": market.get("startsAt"),

                "ends_at": market.get("endsAt"),

                "active": active,

                "elapsed_seconds": round(elapsed_seconds, 2),

                "remaining_seconds": round(
                    remaining_seconds, 2
                ),

                "up_bid": up["bid"],

                "up_ask": up["ask"],

                "down_bid": down["bid"],

                "down_ask": down["ask"],

                "up_bid_size": up["bid_size"],

                "up_ask_size": up["ask_size"],

                "down_bid_size": down["bid_size"],

                "down_ask_size": down["ask_size"],

                "fee_rate_bps": market.get("feeRateBps"),

                "maker_fee_bps": market.get("makerFeeBps"),

                "orderbook_updated": book.get(
                    "updateTimestampMs"
                ),

                "actual_outcome_prices_available": (
                    up["ask"] is not None
                    and down["ask"] is not None
                )

            }

            scanned.append(item)

            print("\nMarket:", item["title"])

            print("Active:", active)

            print("Elapsed:", item["elapsed_seconds"])

            print("UP best ask:", item["up_ask"])

            print("DOWN best ask:", item["down_ask"])

        except Exception as error:

            print(
                f"\nMarket {market_id} failed: {error}"
            )

            traceback.print_exc()

    output = {

        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "asset": "BTC",

        "timeframe": "5 minutes",

        "markets_scanned": len(scanned),

        "orderbooks": scanned

    }

    with open("orderbooks.json", "w") as file:

        json.dump(
            output,
            file,
            indent=2
        )

    print("\nSCANNING COMPLETED")

    print("Markets scanned:", len(scanned))


if __name__ == "__main__":

    scan_markets()
