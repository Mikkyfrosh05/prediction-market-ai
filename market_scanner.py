import json

from datetime import datetime, timezone


def parse_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def get_markets():

    try:
        with open("market_data.json", "r") as file:
            data = json.load(file)

        markets = data.get("markets", [])

        now = datetime.now(timezone.utc)

        active_markets = []
        upcoming_markets = []
        recent_markets = []

        for market in markets:

            # BTC 5-minute validation
            if market.get("crypto_variant") != "CRYPTO_UP_DOWN":
                continue

            if not market.get("price_feed_symbol", "").upper().startswith("BTC"):
                continue

            if market.get("duration_seconds") != 300:
                continue

            if market.get("tradingStatus") != "OPEN":
                continue

            start = parse_time(market.get("startsAt"))
            end = parse_time(market.get("endsAt"))

            if not start or not end:
                continue

            if start <= now < end:
                active_markets.append(market)

            elif start > now:
                upcoming_markets.append(market)

            elif end <= now:
                recent_markets.append(market)

        # Sort markets by their starting time
        upcoming_markets.sort(
            key=lambda market: market["startsAt"]
        )

        recent_markets.sort(
            key=lambda market: market["endsAt"],
            reverse=True
        )

        # Keep current round, next two rounds and two recent rounds
        selected_markets = (
            active_markets[:1]
            + upcoming_markets[:2]
            + recent_markets[:2]
        )

        print("\nBTC 5-MINUTE MARKET SCANNER")
        print("----------------------------")
        print("Active markets:", len(active_markets))
        print("Upcoming markets:", len(upcoming_markets))
        print("Recent markets:", len(recent_markets))
        print("Selected markets:", len(selected_markets))

        for market in selected_markets:

            print("\n----------------------------")
            print("Title:", market.get("title"))
            print("Market ID:", market.get("id"))
            print("Start:", market.get("startsAt"))
            print("End:", market.get("endsAt"))

        return selected_markets

    except FileNotFoundError:
        print("market_data.json not found.")
        return []

    except (ValueError, TypeError) as error:
        print("Market scanner error:", error)
        return []


if __name__ == "__main__":

    markets = get_markets()

    print("\nMarkets selected:", len(markets))
