import os
import sys
import requests
from eth_account import Account
from predict_sdk import OrderBuilder, ChainId, OrderBuilderOptions
API_BASE = "https://api.predict.fun"
API_KEY = os.getenv("PREDICT_API_KEY")
ACCOUNT = os.getenv("PREDICT_ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVY_WALLET_PRIVATE_KEY")
def main():
    if not all([API_KEY, ACCOUNT, PRIVATE_KEY]):
        print("Missing required configuration.")
        sys.exit(1)
    try:
        signer_address = Account.from_key(PRIVATE_KEY).address
        print("Initialising Predict Smart Wallet...")
        builder = OrderBuilder.make(
            ChainId.BNB_MAINNET,
            PRIVATE_KEY,
            OrderBuilderOptions(
                predict_account=ACCOUNT
            )
        )
        print("Requesting authentication message...")
        response = requests.get(
            f"{API_BASE}/v1/auth/message",
            headers={
                "x-api-key": API_KEY
            },
            timeout=20
        )
        if not response.ok:
            print("MESSAGE HTTP STATUS:", response.status_code)
            print("MESSAGE API ERROR:", response.text[:1500])
            sys.exit(1)
        result = response.json()
        message = result.get("data", {}).get("message")
        if not message:
            raise RuntimeError("Authentication message missing.")
        print("Signing authentication message...")
        signature = builder.sign_predict_account_message(message)
        print("Requesting authentication token...")
        response = requests.post(
            f"{API_BASE}/v1/auth",
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "signer": signer_address,
                "signature": signature,
                "message": message
            },
            timeout=20
        )
        if not response.ok:
            print("AUTH HTTP STATUS:", response.status_code)
            print("AUTH API ERROR:", response.text[:1500])
            sys.exit(1)
        result = response.json()
        token = result.get("data", {}).get("token")
        if not result.get("success") or not token:
            print("AUTHENTICATION RESPONSE: Unexpected response format.")
            sys.exit(1)
        print("SMART WALLET AUTHENTICATION: SUCCESS")
        print("JWT received. Token hidden.")
        print("No orders submitted.")
        print("No approvals performed.")
        print("No funds moved.")
    except requests.RequestException as error:
        print("NETWORK ERROR:", type(error).__name__)
        sys.exit(1)
    except Exception as error:
        print("AUTHENTICATION TEST FAILED:", type(error).__name__)
        print("ERROR DETAILS:", str(error)[:1000])
        sys.exit(1)
if __name__ == "__main__":
    main()
