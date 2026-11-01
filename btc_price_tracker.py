import requests
import json

from datetime import datetime, timezone


API_URL = "https://data-api.binance.vision/api/v3"


def get_btc_price():

    url = f"{API_URL}/ticker/price"

    params = {
        "symbol": "BTCUSDT"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return {
            "symbol": data["symbol"],
            "price": float(data["price"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "BINANCE"
        }

    except requests.RequestException as error:

        print("BTC price request failed:", error)

        return None


def get_btc_candles():

    url = f"{API_URL}/klines"

    params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 15
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        candles = response.json()

        results = []

        for candle in candles:

            results.append({
                "open_time": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "close_time": candle[6]
            })

        return results

    except requests.RequestException as error:

        print("BTC candle request failed:", error)

        return None


def save_price_data():

    price = get_btc_price()

    candles = get_btc_candles()

    if price is None or candles is None:

        print("Price tracking failed.")

        return

    output = {

        "updated_at": price["timestamp"],

        "asset": "BTC",

        "trading_pair": "BTCUSDT",

        "price_source": "BINANCE",

        "settlement_source": "CHAINLINK",

        "current_price": price["price"],

        "candles": candles,

        "candle_count": len(candles)

    }

    with open("btc_price_data.json", "w") as file:

        json.dump(
            output,
            file,
            indent=2
        )

    print("\nBTC PRICE TRACKER")
    print("----------------------------")

    print("Current BTC price:", price["price"])

    print("Candles collected:", len(candles))

    print("Price source:", price["source"])

    print("\nBTC price data saved successfully!")


if __name__ == "__main__":

    save_price_data()
