import os
import sys
import requests

from predict_sdk import OrderBuilder, ChainId, OrderBuilderOptions

API_BASE = "https://api.predict.fun"

API_KEY = os.getenv("PREDICT_API_KEY")
ACCOUNT = os.getenv("PREDICT_ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVY_WALLET_PRIVATE_KEY")


def main():
    if not all([API_KEY, ACCOUNT, PRIVATE_KEY]):
        print("Missing required environment configuration.")
        sys.exit(1)

    print("Initialising Predict Smart Wallet...")

    builder = OrderBuilder.make(
        ChainId.BNB_MAINNET,
        PRIVATE_KEY,
        OrderBuilderOptions(predict_account=ACCOUNT)
    )

    headers = {
        "x-api-key": API_KEY
    }

    print("Requesting authentication message...")

    response = requests.get(
        f"{API_BASE}/v1/auth/message",
        headers=headers,
        timeout=20
    )
    response.raise_for_status()

    message = response.json()["data"]["message"]

    print("Signing authentication message...")

    signature = builder.sign_predict_account_message(message)

    print("Requesting JWT authentication...")

    response = requests.post(
        f"{API_BASE}/v1/auth",
        headers={
            **headers,
            "Content-Type": "application/json"
        },
        json={
            "signer": ACCOUNT,
            "signature": signature,
            "message": message
        },
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    token = result.get("data", {}).get("token")

    if not result.get("success") or not token:
        print("Authentication was not confirmed.")
        sys.exit(1)

    print("PREDICT SMART WALLET AUTHENTICATION: SUCCESS")
    print("JWT received. Token hidden.")
    print("No orders submitted.")
    print("No approvals performed.")
    print("No funds moved.")


if __name__ == "__main__":
    main()
