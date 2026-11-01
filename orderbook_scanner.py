import traceback
import os
import json
import requests

from decimal import Decimal
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


def get_price(levels):

    if not levels:
        return None, 0.0

    price = float(levels[0][0])
    quantity = float(levels[0][1])

    return price, quantity


def complement_price(price, precision):

    if price is None:
        return None

    result = Decimal("1") - Decimal(str(price))

    return float(round(result, precision))


def scan_markets():

    markets = get_markets()

    now = datetime.now(timezone.utc)

    # Only scan currently active and upcoming rounds.
    markets = [
        market for market in markets
        if market.get("startsAt")
        and market.get("endsAt")
        and datetime.fromisoformat(
            market["endsAt"].replace("Z", "+00:00")
        ) > now
    ]

    scanned = []

    print("\nBTC ORDERBOOK SCANNER")
    print("----------------------------")
    print("Markets to scan:", len(markets))

    for market in markets:

        market_id = market.get("id")

        if market_id is None:
            continue

        try:

            book = get_orderbook(market_id)

            if not isinstance(book, dict):
                raise ValueError("Invalid orderbook response")

            bids = book.get("bids") or []
            asks = book.get("asks") or []

            precision = market.get("decimalPrecision", 4)

            yes_bid, yes_bid_size = get_price(bids)
            yes_ask, yes_ask_size = get_price(asks)

            no_bid = complement_price(
                yes_ask,
                precision
            )

            no_ask = complement_price(
                yes_bid,
                precision
            )

            item = {

                "market_id": market_id,

                "title": market.get("title"),
                "question": market.get("question"),

                "asset": "BTC",
                "timeframe": "5 minutes",

                "starts_at": market.get("startsAt"),
                "ends_at": market.get("endsAt"),

                "yes_bid": yes_bid,
                "yes_ask": yes_ask,

                "no_bid": no_bid,
                "no_ask": no_ask,

                "yes_bid_quantity": yes_bid_size,
                "yes_ask_quantity": yes_ask_size,

                "fee_rate_bps": market.get("feeRateBps"),
                "maker_fee_bps": market.get("makerFeeBps"),

                "orderbook_updated": book.get(
                    "updateTimestampMs"
                )
            }

            scanned.append(item)

            print("\nMarket:", item["title"])
            print("ID:", market_id)
            print("UP/YES bid:", yes_bid)
            print("UP/YES ask:", yes_ask)
            print("Complementary prices:", no_bid, no_ask)

        except Exception as error:

            print(
                f"\nMarket {market_id} failed: {error}"
            )

            traceback.print_exc()

    output = {

        "updated_at": datetime.now(timezone.utc).isoformat(),

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

    print("\nORDERBOOK SCAN COMPLETED")
    print("Successfully scanned:", len(scanned))


if __name__ == "__main__":

    scan_markets()
