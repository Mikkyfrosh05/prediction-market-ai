import json
from datetime import datetime, timezone

from config import CONFIG
from orderbook_scanner import scan_markets


def display_status():

    print("=" * 45)
    print("PREDICTION MARKET AI")
    print("=" * 45)

    print("Mode:", CONFIG["MODE"])
    print("Starting balance:", CONFIG["STARTING_BALANCE"])
    print("Maximum trade:", CONFIG["MAX_TRADE"])
    print("Maximum daily loss:", CONFIG["MAX_DAILY_LOSS"])
    print("Time:", datetime.now(timezone.utc).isoformat())

    print("=" * 45)


def analyse_orderbooks():

    try:
        with open("orderbooks.json", "r") as file:
            data = json.load(file)

    except FileNotFoundError:
        print("Orderbook data not found.")
        return

    markets = data.get("orderbooks", [])

    print("\nORDER BOOK ANALYSIS")
    print("-" * 45)

    print("Markets analysed:", len(markets))

    for market in markets:

        yes_bid = market.get("yes_bid")
        yes_ask = market.get("yes_ask")

        if yes_bid is None or yes_ask is None:
            continue

        spread = yes_ask - yes_bid

        print("\nMarket:", market.get("question"))
        print("YES bid:", yes_bid)
        print("YES ask:", yes_ask)
        print("YES spread:", round(spread, 4))

        if spread >= 0.20:
            print("Warning: Very wide spread")

        elif spread <= 0.05:
            print("Spread: Relatively narrow")

        else:
            print("Spread: Moderate")


def main():

    display_status()

    print("\nStarting market analysis...")

    try:
        scan_markets()

        analyse_orderbooks()

        print("\nAnalysis completed successfully.")

    except Exception as error:
        print("\nAnalysis failed:", error)
        raise

    print("\nTrading mode:", CONFIG["MODE"])
    print("No real trades have been executed.")


if __name__ == "__main__":
    main()
