from config import CONFIG


class OpportunityDetector:

    def __init__(self):
        self.minimum_edge = CONFIG["MINIMUM_EDGE"]

    def detect(self, market, estimated_yes_probability):

        yes_price = market.get("yes_price")

        if yes_price is None:
            return None

        if not 0 < yes_price < 1:
            return None

        if not 0 <= estimated_yes_probability <= 1:
            return None

        no_price = 1 - yes_price

        yes_edge = estimated_yes_probability - yes_price

        no_edge = (
            (1 - estimated_yes_probability) - no_price
        )

        if yes_edge >= self.minimum_edge:
            side = "YES"
            edge = yes_edge

        elif no_edge >= self.minimum_edge:
            side = "NO"
            edge = no_edge

        else:
            return None

        return {
            "market_id": market.get("id"),
            "market_title": market.get("title"),
            "side": side,
            "market_price": (
                yes_price if side == "YES" else no_price
            ),
            "estimated_edge": round(edge, 4),
            "signal": "POTENTIAL_OPPORTUNITY"
        }


if __name__ == "__main__":

    detector = OpportunityDetector()

    example_market = {
        "id": 101,
        "title": "Will Bitcoin exceed $100,000?",
        "yes_price": 0.40
    }

    result = detector.detect(
        example_market,
        estimated_yes_probability=0.65
    )

    print("OPPORTUNITY ANALYSIS")
    print("--------------------")
    print(result)
