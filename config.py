import os

CONFIG = {
    # Trading mode
    "MODE": "PAPER",

    # Starting virtual balance
    "STARTING_BALANCE": 100.0,

    # Risk management
    "MAX_TRADE": 2.0,
    "MAX_DAILY_LOSS": 5.0,

    # Market scanning
    "MARKET_LIMIT": 50,
    "MINIMUM_EDGE": 0.05,

    # API configuration
    "PREDICT_API_KEY": os.getenv("PREDICT_API_KEY"),

    "API_URL": "https://api.predict.fun"
}
