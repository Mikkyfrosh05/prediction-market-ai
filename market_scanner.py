import requests
from config import CONFIG


def get_markets():

    url = f"{CONFIG['API_URL']}/v1/markets"

    headers = {}

    api_key = CONFIG.get("PREDICT_API_KEY")

    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "first": CONFIG["MARKET_LIMIT"]
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("success"):
            print("API did not return successful data.")
            return []

        markets = result.get("data", [])

        if isinstance(markets, dict):
            markets = markets.get("markets", [])

        return [
            market for market in markets
            if market.get("tradingStatus") == "OPEN"
        ]

    except requests.RequestException as error:
        print(f"Market scanner error: {error}")
        return []

    except (ValueError, TypeError) as error:
        print(f"Invalid market response: {error}")
        return []


if __name__ == "__main__":

    markets = get_markets()

    print(f"\nMarkets found: {len(markets)}")

    for market in markets:

        print("\n-------------------------")
        print("Title:", market.get("title"))
        print("Market ID:", market.get("id"))
        print("Status:", market.get("tradingStatus"))
