from pipecat.frames.frames import Frame, MetricsFrame
from pipecat.metrics.metrics import LLMUsageMetricsData
from pipecat.processors.frame_processor import FrameProcessor

# Cost Tracker class to handle calculations
class CostTracker:
    def __init__(self):
        self.total_cost = 0.0
        self.sessions = []
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Gemini 2.0 Flash Live pricing per 1M tokens
        input_cost = (input_tokens / 1_000_000) * 2.10  # Audio input
        output_cost = (output_tokens / 1_000_000) * 8.50  # Audio output
        return input_cost + output_cost
    
    def log_usage(self, input_tokens: int, output_tokens: int):
        cost = self.calculate_cost(input_tokens, output_tokens)
        self.total_cost += cost
        
        session_data = {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': cost
        }
        self.sessions.append(session_data)
        
        return cost
    
    def get_final_summary(self):
        """Get final cost summary for the call."""
        total_input_tokens = sum(session['input_tokens'] for session in self.sessions)
        total_output_tokens = sum(session['output_tokens'] for session in self.sessions)
        
        return {
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'total_cost': self.total_cost,
            'total_sessions': len(self.sessions)
        }

# Simple function to process metrics frames without StartFrame issues
def process_metrics_frame(frame: Frame, cost_tracker: CostTracker):
    """Process a metrics frame to extract LLM usage data and update cost tracking."""
    if isinstance(frame, MetricsFrame):
        for data in frame.data:
            if isinstance(data, LLMUsageMetricsData):
                usage = data.value
                cost_tracker.log_usage(
                    usage.prompt_tokens,
                    usage.completion_tokens
                )

# Simple processor that bypasses StartFrame requirements
class SimpleCostMonitor:
    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
    
    async def process_frame(self, frame: Frame, direction):
        print(f"🔍 SimpleCostMonitor processing: {type(frame).__name__}")
        process_metrics_frame(frame, self.cost_tracker)
        return frame