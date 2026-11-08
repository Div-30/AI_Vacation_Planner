import asyncio
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(root_dir)

from deepeval import evaluate
from deepeval.test_case import LLMTestCase

from app import models
from app.agent.graph import init_itinerary_graph
from app.services import llm_service
from app.evaluation.dataset import dataset
from app.evaluation.metrics import relevance_metric, completeness_metric, task_metric

async def run_evaluation():
    print("Initializing Agent Graph...")
    await init_itinerary_graph()
    test_cases = []
    sample_trips = [
        models.Trip(id=1, destination="Kyoto", days=3, budget=800, trip_style="cultural"),
        models.Trip(id=2, destination="Banff", days=2, budget=2000, trip_style="adventure"),
        models.Trip(id=3, destination="Paris", days=1, budget=300, trip_style="food tour"),
    ]

    for golden, trip in zip(dataset.goldens, sample_trips):
        print(f"Generating itinerary for {trip.destination} ({trip.days} days)...")
        result = await llm_service.generate_itinerary_json(trip)
        actual_output_str = str(result)
        test_case = LLMTestCase(
            input=golden.input,
            actual_output=actual_output_str,
            expected_output=golden.expected_output,
        )
        test_cases.append(test_case)
    print("Running DeepEval metrics...")
    evaluate(test_cases, [relevance_metric, completeness_metric, task_metric])
if __name__ == "__main__":
    asyncio.run(run_evaluation())
