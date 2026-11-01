import json
from config import CONFIG


class OpportunityDetector:

    def __init__(self):
        self.minimum_edge = CONFIG["MINIMUM_EDGE"]

    def detect(self, market, estimated_yes_probability):

        yes_ask = market.get("yes_ask")
        no_ask = market.get("no_ask")

        if yes_ask is None or no_ask is None:
            return None

        if not 0 < yes_ask < 1:
            return None

        if not 0 < no_ask < 1:
            return None

        if not 0 <= estimated_yes_probability <= 1:
            return None

        yes_edge = estimated_yes_probability - yes_ask

        no_edge = (
            (1 - estimated_yes_probability) - no_ask
        )

        opportunities = []

        if yes_edge >= self.minimum_edge:
            opportunities.append({
                "market_id": market.get("market_id"),
                "market_title": market.get("question"),
                "side": "YES",
                "entry_price": yes_ask,
                "estimated_edge": round(yes_edge, 4),
                "available_quantity": market.get(
                    "yes_ask_liquidity", 0
                )
            })

        if no_edge >= self.minimum_edge:
            opportunities.append({
                "market_id": market.get("market_id"),
                "market_title": market.get("question"),
                "side": "NO",
                "entry_price": no_ask,
                "estimated_edge": round(no_edge, 4),
                "available_quantity": market.get(
                    "yes_bid_liquidity", 0
                )
            })

        return opportunities if opportunities else None

    def scan(self, estimated_probabilities):

        with open("orderbooks.json", "r") as file:
            data = json.load(file)

        opportunities = []

        for market in data.get("orderbooks", []):

            market_id = str(market.get("market_id"))

            probability = estimated_probabilities.get(
                market_id
            )

            if probability is None:
                continue

            result = self.detect(market, probability)

            if result:
                opportunities.extend(result)

        opportunities.sort(
            key=lambda x: x["estimated_edge"],
            reverse=True
        )

        output = {
            "markets_analysed": len(data.get("orderbooks", [])),
            "opportunities_found": len(opportunities),
            "opportunities": opportunities
        }

        with open("opportunities.json", "w") as file:
            json.dump(output, file, indent=2)

        print("OPPORTUNITY ANALYSIS")
        print("--------------------")
        print("Markets analysed:", output["markets_analysed"])
        print("Opportunities found:", output["opportunities_found"])

        return output


if __name__ == "__main__":

    detector = OpportunityDetector()

    # Temporary test probabilities.
    # These are illustrative, NOT actual AI predictions.
    test_probabilities = {
        "52261": 0.65,
        "190414": 0.60
    }

    detector.scan(test_probabilities)
