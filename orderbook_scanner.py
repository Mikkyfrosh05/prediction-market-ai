import os
import json
import requests

from decimal import Decimal
from datetime import datetime, timezone

from config import CONFIG


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

    with open("market_data.json", "r") as file:
        market_data = json.load(file)

    markets = market_data.get("markets", [])[:10]

    scanned = []

    print(f"Scanning {len(markets)} markets...")

    for market in markets:

        market_id = market.get("id")

        if market_id is None:
            continue

        try:

            book = get_orderbook(market_id)

            bids = book.get("bids", [])
            asks = book.get("asks", [])

            precision = market.get("decimalPrecision", 4)

            yes_bid, yes_bid_size = get_price(bids)
            yes_ask, yes_ask_size = get_price(asks)

            no_bid = complement_price(
                yes_ask, precision
            )

            no_ask = complement_price(
                yes_bid, precision
            )

            item = {

                # Market identification
                "market_id": market_id,
                "question": market.get("question"),
                "title": market.get("title"),

                # Market information
                "trading_status": market.get("tradingStatus"),
                "market_status": market.get("status"),
                "is_visible": market.get("isVisible"),
                "is_neg_risk": market.get("isNegRisk"),

                # Fees
                "fee_rate_bps": market.get("feeRateBps"),
                "maker_fee_bps": market.get("makerFeeBps"),

                # YES prices
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,

                # NO prices
                "no_bid": no_bid,
                "no_ask": no_ask,

                # Available quantities
                "yes_bid_quantity": yes_bid_size,
                "yes_ask_quantity": yes_ask_size,

                "no_bid_quantity": yes_ask_size,
                "no_ask_quantity": yes_bid_size,

                # Market statistics
                "total_liquidity_usd": (
                    market.get("stats", {}).get(
                        "totalLiquidityUsd"
                    )
                ),

                "volume_24h_usd": (
                    market.get("stats", {}).get(
                        "volume24hUsd"
                    )
                ),

                # Timestamp
                "orderbook_updated": book.get(
                    "updateTimestampMs"
                )
            }

            scanned.append(item)

            print(
                f"Market {market_id}: "
                f"{market.get('question')} | "
                f"YES bid={yes_bid} | "
                f"YES ask={yes_ask}"
            )

        except Exception as error:

            print(
                f"Market {market_id} failed: {error}"
            )

    output = {

        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "markets_scanned": len(scanned),

        "orderbooks": scanned
    }

    with open("orderbooks.json", "w") as file:

        json.dump(
            output,
            file,
            indent=2
        )

    print("\nOrderbook scanning completed!")

    print(
        "Markets successfully scanned:",
        len(scanned)
    )


if __name__ == "__main__":

    scan_markets()
