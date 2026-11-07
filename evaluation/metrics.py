import os
from dotenv import load_dotenv

load_dotenv()
os.environ["USE_ANTHROPIC_MODEL"] = "YES"

from deepeval.models import AnthropicModel
from deepeval.metrics import GEval, TaskCompletionMetric

judge_model = AnthropicModel(model="claude-haiku-4-5")

relevance_metric = GEval(
    name="Itinerary Relevance",
    evaluation_steps=["Check if the itinerary destination matches the user's requested destination.", 
                      "Check if the activities reflect the user's travel style (e.g. cultural, adventure, food).", 
                      "Verify that estimated costs realistically match the user's budget."],
    evaluation_params=["input", "actual_output"],
    threshold=0.8,
    model=judge_model,
    )
completeness_metric = GEval(
    name="Itinerary Completeness",
    evaluation_steps=[
        "Check if the total number of days generated matches the requested duration.",
        "Ensure each day contains structured morning, afternoon, or evening activities.",
        "Verify that each activity specifies a location and realistic time/duration."
    ],
    evaluation_params=["input", "actual_output"],
    threshold=0.8,
    model=judge_model,
)
task_metric = TaskCompletionMetric(
    threshold=0.8,
    task="Generate a realistic, geographically valid, and budget-aligned vacation itinerary.",
    model=judge_model,
)