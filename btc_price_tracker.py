import requests
import json
import time
import os

from datetime import datetime, timezone


API_URL = "https://data-api.binance.vision/api/v3"

# Keep the latest 10 minutes of live price samples.
HISTORY_SECONDS = 600

# Desired live momentum measurement.
MOMENTUM_WINDOW_SECONDS = 30


def get_btc_price():

    url = f"{API_URL}/ticker/bookTicker"

    params = {
        "symbol": "BTCUSDT"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    bid = float(data["bidPrice"])
    ask = float(data["askPrice"])

    midpoint = (bid + ask) / 2

    return midpoint


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

        # Ignore incomplete candles.
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


def load_previous_samples():

    if not os.path.exists("btc_price_data.json"):
        return []

    try:

        with open("btc_price_data.json", "r") as file:
            previous_data = json.load(file)

        samples = previous_data.get("price_history", [])

        if isinstance(samples, list):
            return samples

        return []

    except (json.JSONDecodeError, OSError):
        return []


def update_price_history(current_price):

    now_ms = int(time.time() * 1000)

    samples = load_previous_samples()

    # Add the latest live price.
    samples.append({

        "timestamp": now_ms,

        "time": datetime.now(
            timezone.utc
        ).isoformat(),

        "price": current_price

    })

    # Remove samples older than 10 minutes.
    cutoff_ms = now_ms - (
        HISTORY_SECONDS * 1000
    )

    samples = [

        sample for sample in samples

        if isinstance(sample, dict)

        and isinstance(sample.get("timestamp"), (int, float))

        and isinstance(sample.get("price"), (int, float))

        and sample["timestamp"] >= cutoff_ms

    ]

    return samples


def calculate_live_momentum(samples):

    if not samples:

        return {
            "available": False,
            "reason": "No price history available"
        }

    now_ms = int(time.time() * 1000)

    current_sample = samples[-1]

    current_price = float(current_sample["price"])

    target_timestamp = now_ms - (
        MOMENTUM_WINDOW_SECONDS * 1000
    )

    # Find the sample closest to 30 seconds ago,
    # preferring a sample at or before the target.
    eligible_samples = [

        sample for sample in samples

        if sample["timestamp"] <= target_timestamp

    ]

    if not eligible_samples:

        return {

            "available": False,

            "reason": "Not enough historical samples yet",

            "samples_available": len(samples),

            "required_window_seconds": MOMENTUM_WINDOW_SECONDS

        }

    reference_sample = max(
        eligible_samples,
        key=lambda sample: sample["timestamp"]
    )

    reference_price = float(reference_sample["price"])

    elapsed_seconds = (
        now_ms - reference_sample["timestamp"]
    ) / 1000

    if reference_price <= 0:

        return {
            "available": False,
            "reason": "Invalid reference price"
        }

    movement_percent = (
        (current_price - reference_price)
        / reference_price
    ) * 100

    if movement_percent > 0:

        direction = "UP"

    elif movement_percent < 0:

        direction = "DOWN"

    else:

        direction = "FLAT"

    return {

        "available": True,

        "window_seconds": round(elapsed_seconds, 2),

        "reference_price": reference_price,

        "current_price": current_price,

        "movement_percent": round(
            movement_percent,
            6
        ),

        "direction": direction,

        "reference_timestamp": reference_sample["timestamp"],

        "current_timestamp": now_ms

    }


def save_price_data():

    try:

        price = get_btc_price()

        candles = get_btc_candles()

        if len(candles) < 30:

            print("Insufficient completed candles.")

            return

        # Preserve previous live price samples.
        price_history = update_price_history(price)

        # Calculate 30-second live momentum.
        live_momentum = calculate_live_momentum(
            price_history
        )

        output = {

            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "asset": "BTC",

            "trading_pair": "BTCUSDT",

            "price_source": "BINANCE_BOOK_MID",

            "settlement_source": "CHAINLINK",

            "current_price": price,

            "current_price_timestamp": int(
                time.time() * 1000
            ),

            "live_momentum": live_momentum,

            "price_history": price_history,

            "price_history_count": len(price_history),

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

        print("Current BTC midpoint:", price)

        print("Price source: BINANCE_BOOK_MID")

        print("Settlement reference: CHAINLINK")

        print("Completed candles:", len(candles))

        print("Live price samples:", len(price_history))

        if live_momentum.get("available"):

            print("\n30-SECOND LIVE MOMENTUM")

            print(
                "Reference price:",
                live_momentum["reference_price"]
            )

            print(
                "Current price:",
                live_momentum["current_price"]
            )

            print(
                "Movement:",
                live_momentum["movement_percent"],
                "%"
            )

            print(
                "Direction:",
                live_momentum["direction"]
            )

            print(
                "Measurement window:",
                live_momentum["window_seconds"],
                "seconds"
            )

        else:

            print(
                "\n30-second momentum:",
                live_momentum.get("reason")
            )

        print("\nBTC data saved successfully!")

    except Exception as error:

        print("BTC tracker error:", error)

        raise


if __name__ == "__main__":

    save_price_data()
