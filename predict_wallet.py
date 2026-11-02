import os
import requests
import sys

API_BASE = "https://api.predict.fun"

API_KEY = os.getenv("PREDICT_API_KEY")
ACCOUNT_ADDRESS = os.getenv("PREDICT_ACCOUNT_ADDRESS")


def check_configuration():
    if not API_KEY:
        print("ERROR: PREDICT_API_KEY is missing.")
        sys.exit(1)

    if not ACCOUNT_ADDRESS:
        print("ERROR: PREDICT_ACCOUNT_ADDRESS is missing.")
        sys.exit(1)

    print("Wallet configuration found.")
    print(f"Predict Account: {ACCOUNT_ADDRESS}")


def get_auth_message():
    print("\nRequesting authentication message...")

    headers = {
        "x-api-key": API_KEY
    }

    try:
        response = requests.get(
            f"{API_BASE}/v1/auth/message",
            headers=headers,
            timeout=15
        )

        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            print("Authentication message request failed.")
            return

        message = result.get("data", {}).get("message")

        if not message:
            print("No authentication message returned.")
            return

        print("\nAuthentication message received.")
        print("Message:")
        print(message)

        print("\nWallet API connection: SUCCESS")
        print("No signature generated.")
        print("No orders submitted.")
        print("No funds moved.")

    except requests.RequestException as error:
        print(f"API connection failed: {error}")


if __name__ == "__main__":
    check_configuration()
    get_auth_message()
