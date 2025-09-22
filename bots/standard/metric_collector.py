from pipecat.metrics.metrics import (
    LLMUsageMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
    LLMTokenUsage,
    ProcessingMetricsData,
)
from pipecat.frames.frames import MetricsFrame
from pipecat.frames.frames import TranscriptionFrame, TTSAudioRawFrame, LLMTextFrame
from pipecat.metrics import metrics
from pipecat.observers.base_observer import BaseObserver, FramePushed
from loguru import logger


class MetricsCollector(BaseObserver):
    """Enhanced metrics collector following RTVI pattern for structured metrics handling."""

    def __init__(self):
        super().__init__()
        # Initialize structured metrics storage following RTVI pattern
        self.metrics_data = {
            "ttfb": [],
            "processing": [],
            "tokens": [],
            "characters": [],
        }

        # Legacy counters for backward compatibility
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tts_characters = 0
        self.llm_ttfb = 0.0
        self.tts_ttfb = 0.0
        self.stt_ttfb = 0.0

        # Add STT duration tracking
        self.total_stt_duration = 0.0

    async def on_push_frame(self, data: FramePushed):
        """Handle frames and process metrics following RTVI pattern."""
        frame = data.frame

        if isinstance(frame, MetricsFrame):
            await self._handle_metrics(frame)

    async def _handle_metrics(self, frame: MetricsFrame):
        """Handle metrics frames and convert to structured metrics following RTVI pattern."""
        metrics = {}

        # Process frame data - handle both single items and lists
        data_list = frame.data if isinstance(frame.data, list) else [frame.data]

        for d in data_list:

            if isinstance(d, TTFBMetricsData):
                # logger.info(f"🔍 Processing TTFB for processor: {d.processor}, value: {d.value}")
                # print(f"🔍 Processing TTFB for processor 🚀🚀🚀: {d}")

                # Convert TTFB from seconds to milliseconds
                ttfb_ms = d.value * 1000 if d.value is not None else 0.0

                if "ttsservice" in d.processor.lower():
                    self.tts_ttfb = ttfb_ms

                elif "sttservice" in d.processor.lower():
                    self.stt_ttfb = ttfb_ms

                elif "llmservice" in d.processor.lower():
                    self.llm_ttfb = ttfb_ms

            elif isinstance(d, LLMUsageMetricsData):

                # Store in structured data
                if "tokens" not in metrics:
                    metrics["tokens"] = []

                token_entry = d.value.model_dump(exclude_none=True)
                metrics["tokens"].append(token_entry)
                self.metrics_data["tokens"].append(token_entry)

                # Update token counters
                usage: LLMTokenUsage = d.value
                self.total_prompt_tokens += usage.prompt_tokens
                self.total_completion_tokens += usage.completion_tokens

            elif isinstance(d, TTSUsageMetricsData):

                # Store in structured data
                if "characters" not in metrics:
                    metrics["characters"] = []

                char_entry = d.model_dump(exclude_none=True)
                metrics["characters"].append(char_entry)
                self.metrics_data["characters"].append(char_entry)

                # Update character counter
                self.total_tts_characters += d.value

            elif isinstance(d, ProcessingMetricsData):

                # Store in structured data
                if "processing" not in metrics:
                    metrics["processing"] = []

                processing_entry = d.model_dump(exclude_none=True)
                metrics["processing"].append(processing_entry)
                self.metrics_data["processing"].append(processing_entry)

                # Track STT duration specifically
                if hasattr(d, "processor") and "sttservice" in d.processor.lower():
                    if hasattr(d, "value") and isinstance(d.value, (int, float)):
                        self.total_stt_duration += d.value

    def get_latency(self):
        """Get average latency metrics."""
        latencies = {
            "llm_ttfb": self.llm_ttfb,
            "tts_ttfb": self.tts_ttfb,
            "stt_ttfb": self.stt_ttfb,
            "total_stt_duration": self.total_stt_duration,
            "total_latency": self.llm_ttfb + self.tts_ttfb + self.stt_ttfb,
        }

        return latencies

    def get_token_usage(self):
        """Get detailed token usage metrics."""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "tts_characters": self.total_tts_characters,
        }

    def get_metric_summary(self):
        """Enhanced summary with structured data."""
        # Get structured metrics
        logger.info("📊 Generating structured metrics summary")
        logger.info(f"📊 Current structured metrics data TTS TTFB: {self.tts_ttfb:.2f}ms")
        logger.info(f"📊 Current structured metrics data LLM TTFB: {self.llm_ttfb:.2f}ms")
        logger.info(f"📊 Current structured metrics data STT TTFB: {self.stt_ttfb:.2f}ms")
        logger.info(f"📊 STT Total Duration: {self.total_stt_duration:.2f}ms")
        logger.info(
            f"📊 Current structured metrics data Total Latency: {self.get_latency()['total_latency']:.2f}ms"
        )

        # Log token usage
        logger.info(f"💰 Token Usage Summary:")
        logger.info(f"  📝 Total Prompt Tokens: {self.total_prompt_tokens}")
        logger.info(f"  🤖 Total Completion Tokens: {self.total_completion_tokens}")
        logger.info(
            f"  📊 Total Tokens: {self.total_prompt_tokens + self.total_completion_tokens}"
        )
        logger.info(f"  🔊 Total TTS Characters: {self.total_tts_characters}")

        # Return structured metrics for potential external use
        return {
            "tts_ttfb": self.tts_ttfb,
            "llm_ttfb": self.llm_ttfb,
            "stt_ttfb": self.stt_ttfb,
            "stt_total_duration": self.total_stt_duration,
            "total_latency": self.get_latency()["total_latency"],
            "tokens": {
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            },
            "tts_characters": self.total_tts_characters,
        }


class CostCollector:
    """Cost collector to handle cost tracking."""

    def __init__(self):
        self.llm_cost = 0.0
        self.tts_cost = 0.0
        self.stt_cost = 0.0
        self.total_cost = 0.0

    def calculate_llm_cost(self, input_tokens: int, output_tokens: int,model: str):
        """Calculate LLM cost."""
        if model in llm_prices:
            input_cost = (input_tokens / 1_000_000) * llm_prices[model]["input_cost"]
            output_cost = (output_tokens / 1_000_000) * llm_prices[model]["output_cost"]
            self.llm_cost = input_cost + output_cost
        

    
    def get_cost(self):
        """Get cost metrics."""
        return {
            "llm_cost": self.llm_cost,
            "tts_cost": self.tts_cost,
            "stt_cost": self.stt_cost,
            "total_cost": self.total_cost,
        }


# LLM prices 1M tokens
llm_prices = {
    "openai/gpt-4o-mini-2024-07-18": {"input_cost": 0.15, "output_cost": 0.60},
    "gemini/gemini-2.5-pro": {"input_cost": 1.25, "output_cost": 10.00},
    "gemini/gemini-2.5-flash": {"input_cost": 0.30, "output_cost": 2.50},
    "gemini/gemini-2.5-flash-lite": {"input_cost": 0.10, "output_cost": 0.40},
    "gemini/gemini-2.0-flash": {"input_cost": 0.10, "output_cost": 0.40},
    "gemini/gemini-2.0-flash-lite": {"input_cost": 0.075, "output_cost": 0.30},
    "openai/gpt-5-2025-08-07": {"input_cost": 1.25, "output_cost": 10.00},
    "openai/gpt-5-mini-2025-08-07": {"input_cost": 0.25, "output_cost": 2.00},
    "openai/gpt-5-nano-2025-08-07": {"input_cost": 0.05, "output_cost": 0.40},
    "openai/gpt-4.1-2025-04-14": {"input_cost": 3.00, "output_cost": 12.00},
    "openai/gpt-4.1-nano-2025-04-14": {"input_cost": 0.20, "output_cost": 0.80},
    "openai/o4-mini-2025-04-16": {"input_cost": 4.00, "output_cost": 16.00},
    "openai/gpt-4.1-mini-2025-04-14": {"input_cost": 0.80, "output_cost": 3.20},
}
