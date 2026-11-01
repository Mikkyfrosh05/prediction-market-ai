import json
from config import CONFIG
from probability_engine import ProbabilityEngine


class OpportunityDetector:

    def __init__(self):
        self.engine = ProbabilityEngine(
            minimum_edge=CONFIG["MINIMUM_EDGE"]
        )

    def detect(self, market, estimated_yes_probability):

        yes_ask = market.get("yes_ask")
        no_ask = market.get("no_ask")

        if yes_ask is None or no_ask is None:
            return []

        if not 0 < yes_ask < 1:
            return []

        if not 0 < no_ask < 1:
            return []

        if not self.engine.validate_probability(
            estimated_yes_probability
        ):
            return []

        results = []

        # Analyse YES
        yes_result = self.engine.analyse(
            estimated_yes_probability,
            yes_ask
        )

        if yes_result["edge"] >= self.engine.minimum_edge:
            results.append({
                "market_id": market["market_id"],
                "market_title": market["question"],
                "side": "YES",
                "entry_price": yes_ask,
                "estimated_edge": yes_result["edge"]
            })

        # Analyse NO
        no_probability = 1 - estimated_yes_probability

        no_result = self.engine.analyse(
            no_probability,
            no_ask
        )

        if no_result["edge"] >= self.engine.minimum_edge:
            results.append({
                "market_id": market["market_id"],
                "market_title": market["question"],
                "side": "NO",
                "entry_price": no_ask,
                "estimated_edge": no_result["edge"]
            })

        return results

    def scan(self, estimated_probabilities):

        with open("orderbooks.json") as file:
            data = json.load(file)

        opportunities = []

        for market in data.get("orderbooks", []):

            market_id = str(market["market_id"])

            probability = estimated_probabilities.get(
                market_id
            )

            if probability is None:
                continue

            opportunities.extend(
                self.detect(market, probability)
            )

        opportunities.sort(
            key=lambda x: x["estimated_edge"],
            reverse=True
        )

        output = {
            "markets_analysed": len(data["orderbooks"]),
            "opportunities_found": len(opportunities),
            "opportunities": opportunities
        }

        with open("opportunities.json", "w") as file:
            json.dump(output, file, indent=2)

        print("Markets analysed:", output["markets_analysed"])
        print("Opportunities found:", output["opportunities_found"])

        return output


if __name__ == "__main__":

    detector = OpportunityDetector()

    test_probabilities = {
        "52261": 0.65,
        "190414": 0.60
    }

    detector.scan(test_probabilities)
