from deepeval.dataset import EvaluationDataset, Golden

dataset = EvaluationDataset()

goldens = [
    Golden(
        input="Plan a 3-day cultural trip to Kyoto with a moderate budget of $800.",
        expected_output="A 3-day itinerary covering historic shrines, local culinary experiences, and temples within an $800 budget."
    ),
    Golden(
        input="Plan a 2-day outdoor adventure trip to Banff with a high budget of $2000.",
        expected_output="Plan a 2-day itinerary featuring national park trails, scenic lakes, and guided excursions within a 2000 budget."
    ),
    Golden(
        input="Plan a 1-day food tour trip to Paris with a budget of $300.",
        expected_output="A 1-day culinary itinerary with bakeries, bistros, and market visits adhering to $300."
    )
]

for g in goldens:
    dataset.add_golden(g)