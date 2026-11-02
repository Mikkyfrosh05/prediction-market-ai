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


def read_level(level):

    if not isinstance(level, (list, tuple)):
        return None, None

    if len(level) < 2:
        return None, None

    try:

        price = float(level[0])
        size = float(level[1])

        return price, size

    except (ValueError, TypeError):

        return None, None


def get_best_level(levels):

    if not levels:
        return None, None

    return read_level(levels[0])


def calculate_complement(price, precision):

    if price is None:
        return None

    return round(
        1.0 - price,
        precision
    )


def map_orderbook_to_outcomes(market, book):

    outcomes = market.get("outcomes", [])

    if len(outcomes) < 2:
        raise ValueError(
            "Market does not contain two outcomes"
        )

    first_outcome = (
        outcomes[0].get("name", "").strip().upper()
    )

    second_outcome = (
        outcomes[1].get("name", "").strip().upper()
    )

    if {first_outcome, second_outcome} != {"UP", "DOWN"}:

        raise ValueError(
            f"Unexpected outcomes: {first_outcome}, {second_outcome}"
        )

    precision = int(
        market.get("decimalPrecision", 2)
    )

    asks = book.get("asks", [])
    bids = book.get("bids", [])

    base_ask, base_ask_size = get_best_level(asks)

    base_bid, base_bid_size = get_best_level(bids)

    # First outcome uses the actual orderbook.

    base = {

        "bid": base_bid,

        "ask": base_ask,

        "bid_size": base_bid_size or 0,

        "ask_size": base_ask_size or 0

    }

    # Second outcome is the complementary outcome.
    # Its bid comes from 1 - first outcome ask.
    # Its ask comes from 1 - first outcome bid.

    complementary = {

        "bid": calculate_complement(
            base_ask,
            precision
        ),

        "ask": calculate_complement(
            base_bid,
            precision
        ),

        "bid_size": base_ask_size or 0,

        "ask_size": base_bid_size or 0

    }

    if first_outcome == "UP":

        up = base
        down = complementary

    else:

        down = base
        up = complementary

    return up, down


def scan_markets():

    markets = get_markets()

    scanned = []

    print("\nBTC OUTCOME ORDERBOOK SCANNER")
    print("--------------------------------")

    for market in markets:

        market_id = market.get("id")

        if market_id is None:
            continue

        try:

            # Fetch a fresh orderbook snapshot.

            book = get_orderbook(market_id)

            # Confirm the returned book belongs
            # to the requested market.

            book_market_id = book.get("marketId")

            if (
                book_market_id is not None
                and str(book_market_id) != str(market_id)
            ):

                raise ValueError(
                    "Orderbook market ID mismatch"
                )

            # Derive actual UP and DOWN prices
            # from the fresh orderbook.

            up, down = map_orderbook_to_outcomes(
                market,
                book
            )

            now = datetime.now(timezone.utc)

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

            update_timestamp = book.get(
                "updateTimestampMs"
            )

            if update_timestamp is not None:

                orderbook_age = round(
                    (
                        now.timestamp() * 1000
                        - float(update_timestamp)
                    ) / 1000,
                    2
                )

            else:

                orderbook_age = None

            item = {

                "market_id": market_id,

                "title": market.get("title"),

                "asset": "BTC",

                "timeframe": "5 minutes",

                "starts_at": market.get("startsAt"),

                "ends_at": market.get("endsAt"),

                "active": active,

                "elapsed_seconds": round(
                    elapsed_seconds,
                    2
                ),

                "remaining_seconds": round(
                    remaining_seconds,
                    2
                ),

                "up_bid": up["bid"],

                "up_ask": up["ask"],

                "down_bid": down["bid"],

                "down_ask": down["ask"],

                "up_bid_size": up["bid_size"],

                "up_ask_size": up["ask_size"],

                "down_bid_size": down["bid_size"],

                "down_ask_size": down["ask_size"],

                "fee_rate_bps": market.get(
                    "feeRateBps"
                ),

                "maker_fee_bps": market.get(
                    "makerFeeBps"
                ),

                "decimal_precision": market.get(
                    "decimalPrecision"
                ),

                "orderbook_updated": update_timestamp,

                "orderbook_age_seconds": orderbook_age,

                "base_outcome": market["outcomes"][0]["name"],

                "actual_outcome_prices_available": (

                    up["ask"] is not None

                    and down["ask"] is not None

                )

            }

            scanned.append(item)

            print("\nMarket:", item["title"])

            print("Market ID:", market_id)

            print("Active:", active)

            print(
                "Elapsed:",
                item["elapsed_seconds"]
            )

            print("Base outcome:", item["base_outcome"])

            print("UP best bid:", item["up_bid"])

            print("UP best ask:", item["up_ask"])

            print("DOWN best bid:", item["down_bid"])

            print("DOWN best ask:", item["down_ask"])

            print("UP ask size:", item["up_ask_size"])

            print("DOWN ask size:", item["down_ask_size"])

            print(
                "Orderbook age:",
                item["orderbook_age_seconds"]
            )

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
