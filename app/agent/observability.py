import logging
import time
from typing import Any, Dict, Optional
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger("agent.observability")
logger.setLevel(logging.INFO)

class AgentObservabilityCallback(BaseCallbackHandler):
    """Tracks latency, token usage, model information,
    and errors for agent runs."""
    def __init__(self):
        super().__init__()
        self.start_time: float = 0.0
        self.total_latency: float = 0.0
        self.model_name: Optional[str] = None
        self.total_tokens: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.tool_calls_count: int = 0
        self.errors: list[str] = []

    def on_chain_start(self, serialized: Optional[Dict[str, Any]], input: Dict[str, Any], **kwargs: Any) -> None:
        if self.start_time == 0.0:
            self.start_time = time.perf_counter()
    def on_llm_start(self, serialized: Optional[Dict[str, Any]], prompts: list[str], **kwargs: Any) -> None:
        if serialized and "name" in serialized:
            self.model_name = serialized["name"]
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage") or response.llm_output.get("usage_metadata")
            if token_usage: 
                self.prompt_tokens += token_usage.get("prompt_tokens", 0) or token_usage.get("input_tokens", 0)
                self.completion_tokens += token_usage.get("completion_tokens", 0) or token_usage.get("output_tokens", 0)
                self.total_tokens += token_usage.get("total_tokens", 0)
            if not self.model_name:
                self.model_name = response.llm_output.get("model_name")
    def on_tool_start(self, serialized: Optional[Dict[str, Any]], input_str: str, **kwargs: Any) -> None: 
        self.tool_calls_count += 1
    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self.errors.append(f"Tool Error: {str(error)}")
    def on_chain_end(self, output: Dict[str, Any], **kwargs: Any) -> None:
        if self.start_time > 0 and self.total_latency == 0.0:
            self.total_latency = round(time.perf_counter() - self.start_time, 3)
    def get_summary(self) -> Dict[str, Any]:
        """Returns consolidated observability metrics."""
        return {
            "model_used": self.model_name or "unknown", 
            "latency_seconds": self.total_latency,
            "prompt_tokens": self.prompt_tokens, 
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls_count": self.tool_calls_count,
            "errors": self.errors,
            "success": len(self.errors) == 0,
        }

