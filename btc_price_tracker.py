import requests
import json
import time

from datetime import datetime, timezone


API_URL = "https://data-api.binance.vision/api/v3"


def get_btc_price():

    url = f"{API_URL}/ticker/price"

    params = {
        "symbol": "BTCUSDT"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    return float(response.json()["price"])


def get_btc_candles():

    url = f"{API_URL}/klines"

    params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 100
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    raw_candles = response.json()

    now_ms = int(time.time() * 1000)

    candles = []

    for candle in raw_candles:

        close_time = candle[6]

        # Ignore candles that have not closed yet
        if close_time >= now_ms:
            continue

        candles.append({

            "open_time": candle[0],

            "open": float(candle[1]),

            "high": float(candle[2]),

            "low": float(candle[3]),

            "close": float(candle[4]),

            "volume": float(candle[5]),

            "close_time": close_time

        })

    return candles


def save_price_data():

    try:

        price = get_btc_price()

        candles = get_btc_candles()

        if len(candles) < 30:

            print("Insufficient completed candles.")

            return

        output = {

            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "asset": "BTC",

            "trading_pair": "BTCUSDT",

            "price_source": "BINANCE",

            "settlement_source": "CHAINLINK",

            "current_price": price,

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

        print("Current BTC price:", price)

        print("Completed candles:", len(candles))

        print("First candle:", candles[0]["open_time"])

        print("Latest candle:", candles[-1]["close_time"])

        print("\nBTC data saved successfully!")

    except Exception as error:

        print("BTC tracker error:", error)

        raise


if __name__ == "__main__":

    save_price_data()
