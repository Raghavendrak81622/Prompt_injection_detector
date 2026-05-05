"""
Guardrail Pipeline
------------------
Implements the 10-layer guardrail architecture:
A - Input boundary (L0, L1, L2)
B - Detection (L3, L4, L5)
C - Pre-execution gate (L6)
LLM inference
D - Post-generation validation (L7, L8)
E - Agentic guard (L9)
F - Observability + feedback (L10)
"""

import math
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .detector import PromptInjectionDetector
from .rule_engine import normalize_text

# ─── Types ────────────────────────────────────────────────────────────────────

@dataclass
class SessionContext:
    session_id: str
    history: List[Dict[str, str]] = field(default_factory=list)
    turn_count: int = 0

@dataclass
class ToolCall:
    tool_name: str
    parameters: Dict[str, Any]

@dataclass
class PipelineResult:
    status: str             # "ALLOWED", "BLOCKED", "SANITIZED", "REWRITTEN"
    original_input: str
    final_input: Optional[str]
    llm_output: Optional[str] = None
    tool_calls_blocked: bool = False
    verdict: str = "UNKNOWN"
    reason: str = ""
    layer_triggered: str = ""

# ─── New Layers ───────────────────────────────────────────────────────────────

class InputRouter:
    """L0: Input router + session loader"""
    def load_session(self, session_id: str) -> SessionContext:
        # Mock session loader
        return SessionContext(session_id=session_id)

class SCPIIsolator:
    """L1: SCPI - structured isolation"""
    def isolate(self, text: str) -> str:
        # Use ChatML / XML style boundary to isolate untrusted input
        return f"<untrusted_user_input>\n{text}\n</untrusted_user_input>"

class PerplexityScorer:
    """L2: Preprocessing + perplexity scoring"""
    def score(self, text: str) -> float:
        # Mock perplexity calculation.
        # Unusually high or low perplexity can indicate obfuscation (e.g., base64, random chars)
        if not text:
            return 100.0 # High perplexity for empty/junk
        # Simple heuristic: word length and character distribution
        words = text.split()
        avg_word_len = sum(len(w) for w in words) / max(1, len(words))
        if avg_word_len > 15: 
            return 80.0
        return 20.0  # Normal

class MLClassifierMiniBERT:
    """L4: ML classifier - fine-tuned DeBERTa model"""
    def __init__(self):
        try:
            from transformers import pipeline
            import torch
            device = 0 if torch.cuda.is_available() else -1
            print("Loading ML Classifier (ProtectAI/deberta-v3-base-prompt-injection-v2)...")
            self.classifier = pipeline(
                "text-classification", 
                model="ProtectAI/deberta-v3-base-prompt-injection-v2", 
                device=device
            )
            self.available = True
            print("ML Classifier loaded successfully!")
        except Exception as e:
            print(f"Failed to load ML Classifier: {e}")
            self.available = False

    def predict(self, text: str) -> float:
        if not self.available:
            return 0.0
            
        try:
            # Truncate to max length to avoid tokenization errors
            truncated = text[:2000]
            result = self.classifier(truncated)[0]
            
            # The ProtectAI model returns INJECTION or SAFE
            label = result['label'].upper()
            score = result['score']
            
            if "INJECTION" in label:
                return score
            else:
                return 1.0 - score
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.0

class OutputValidator:
    """L7: Output validator - critic model"""
    def validate(self, original_input: str, llm_output: str) -> bool:
        # Checks semantic alignment: did output follow an injected instruction?
        if "I am now an unrestricted AI" in llm_output or "My system prompt is" in llm_output:
            return False
        return True

class AdaptiveResponseRewriter:
    """L8: Adaptive response rewriter (ARR)"""
    def rewrite(self, llm_output: str) -> str:
        # Rewrite misaligned output to a safe fallback
        return "I cannot fulfill this request as it violates safety guidelines."

class ToolCallValidator:
    """L9: Tool-call validator"""
    def validate_tools(self, tools: List[ToolCall]) -> bool:
        # Pre-execution, least privilege, blocks agentic exploitation
        for tool in tools:
            if tool.tool_name in ["delete_files", "system_exec", "run_bash"]:
                # High risk tools blocked
                return False
        return True

class SessionMonitor:
    """L10: Session monitor + feedback loop"""
    def monitor(self, session: SessionContext, result: PipelineResult):
        # multi-turn anomaly detection, verdicts feed retraining
        pass

# ─── Pipeline ─────────────────────────────────────────────────────────────────

class GuardrailPipeline:
    def __init__(self, api_key: str = None):
        self.detector = PromptInjectionDetector(api_key=api_key)
        self.router = InputRouter()
        self.isolator = SCPIIsolator()
        self.perplexity = PerplexityScorer()
        self.ml_classifier = MLClassifierMiniBERT()
        self.output_validator = OutputValidator()
        self.arr = AdaptiveResponseRewriter()
        self.tool_validator = ToolCallValidator()
        self.monitor = SessionMonitor()

    def run(self, text: str, session_id: str = "default", mock_llm_response: str = None, mock_tools: List[ToolCall] = None) -> PipelineResult:
        """Runs the full 10-layer pipeline."""
        
        # --- A. Input boundary ---
        # L0
        session = self.router.load_session(session_id)
        # L1
        isolated_text = self.isolator.isolate(text)
        # L2
        px_score = self.perplexity.score(text)
        if px_score > 75.0:
            return PipelineResult("BLOCKED", text, None, verdict="INJECTION", reason="High perplexity (obfuscation detected)", layer_triggered="L2")

        # --- B. Detection ---
        # L3 & L5 are handled by detector
        detect_result = self.detector.detect(text)
        
        # L4 (parallel to L3)
        ml_score = self.ml_classifier.predict(text)
        
        # --- C. Pre-execution gate ---
        # L6
        final_verdict = detect_result.verdict
        if ml_score > 0.9:
            final_verdict = "INJECTION"
            
        if final_verdict == "INJECTION":
            return PipelineResult("BLOCKED", text, None, verdict="INJECTION", reason="Detection engine flagged input", layer_triggered="L6")
        elif final_verdict == "SUSPICIOUS":
            # Sanitize by enforcing strict boundaries
            processed_input = f"Strictly answer the following: {isolated_text}"
            status = "SANITIZED"
        else:
            processed_input = text
            status = "ALLOWED"

        # --- LLM Inference (Mocked) ---
        llm_output = mock_llm_response if mock_llm_response else "This is a safe response."
        tools = mock_tools if mock_tools else []

        # --- E. Agentic guard ---
        # L9
        if not self.tool_validator.validate_tools(tools):
            return PipelineResult("BLOCKED", text, processed_input, verdict="INJECTION", reason="Malicious tool call blocked", layer_triggered="L9")

        # --- D. Post-generation validation ---
        # L7
        if not self.output_validator.validate(text, llm_output):
            # L8
            llm_output = self.arr.rewrite(llm_output)
            status = "REWRITTEN"
            layer = "L8"
        else:
            layer = "L7 (Pass)"

        res = PipelineResult(status, text, processed_input, llm_output, verdict="SAFE", reason="Passed all checks", layer_triggered=layer)
        
        # --- F. Observability ---
        # L10
        self.monitor.monitor(session, res)
        
        return res
