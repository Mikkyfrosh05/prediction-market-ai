class ProbabilityEngine:

    def __init__(self, minimum_edge=0.05):
        self.minimum_edge = minimum_edge

    def validate_probability(self, probability):

        if not isinstance(probability, (int, float)):
            return False

        return 0 <= probability <= 1

    def calculate_edge(self, estimated_probability, market_price):

        if not self.validate_probability(estimated_probability):
            raise ValueError("Invalid estimated probability")

        if not self.validate_probability(market_price):
            raise ValueError("Invalid market price")

        return estimated_probability - market_price

    def analyse(self, estimated_probability, market_price):

        edge = self.calculate_edge(
            estimated_probability,
            market_price
        )

        if edge >= self.minimum_edge:
            signal = "POTENTIAL_YES_OPPORTUNITY"

        elif edge <= -self.minimum_edge:
            signal = "POTENTIAL_NO_OPPORTUNITY"

        else:
            signal = "NO_CLEAR_OPPORTUNITY"

        return {
            "estimated_probability": estimated_probability,
            "market_probability": market_price,
            "edge": round(edge, 4),
            "signal": signal
        }


if __name__ == "__main__":

    engine = ProbabilityEngine(minimum_edge=0.05)

    result = engine.analyse(
        estimated_probability=0.65,
        market_price=0.40
    )

    print("PROBABILITY ANALYSIS")
    print("--------------------")

    for key, value in result.items():
        print(f"{key}: {value}")
