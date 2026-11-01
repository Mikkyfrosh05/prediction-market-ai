import os
import json
import requests
from datetime import datetime, timezone

API_URL = "https://api.predict.fun/v1/markets"
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
        raise Exception("Orderbook API request failed")

    return result["data"]


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

            yes_bid = float(bids[0][0]) if bids else None
            yes_ask = float(asks[0][0]) if asks else None

            no_bid = 1 - yes_ask if yes_ask is not None else None
            no_ask = 1 - yes_bid if yes_bid is not None else None

            item = {
                "market_id": market_id,
                "question": market.get("title"),
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,
                "no_bid": no_bid,
                "no_ask": no_ask,
                "yes_bid_liquidity": float(bids[0][1]) if bids else 0,
                "yes_ask_liquidity": float(asks[0][1]) if asks else 0,
                "orderbook_updated": book.get("updateTimestampMs")
            }

            scanned.append(item)

            print(f"Market {market_id}: YES bid={yes_bid}, YES ask={yes_ask}")

        except Exception as error:
            print(f"Market {market_id} failed: {error}")

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": len(scanned),
        "orderbooks": scanned
    }

    with open("orderbooks.json", "w") as file:
        json.dump(output, file, indent=2)

    print("Orderbook scanning completed!")
    print("Markets successfully scanned:", len(scanned))


if __name__ == "__main__":
    scan_markets()
