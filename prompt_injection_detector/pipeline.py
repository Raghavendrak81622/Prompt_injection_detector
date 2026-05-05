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

    def predict_batch(self, texts: List[str]) -> List[float]:
        if not self.available:
            return [0.0] * len(texts)
            
        try:
            # Truncate all texts
            truncated = [t[:2000] for t in texts]
            results = self.classifier(truncated, batch_size=8)
            
            scores = []
            for result in results:
                label = result['label'].upper()
                score = result['score']
                if "INJECTION" in label:
                    scores.append(score)
                else:
                    scores.append(1.0 - score)
            return scores
        except Exception as e:
            print(f"Batch prediction error: {e}")
            return [0.0] * len(texts)

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
        """Runs the full 10-layer pipeline for a single input."""
        return self.run_batch([text], session_id, [mock_llm_response] if mock_llm_response else None, [mock_tools] if mock_tools else None)[0]

    def run_batch(self, texts: List[str], session_id: str = "default", mock_llm_responses: List[str] = None, mock_tools_list: List[List[ToolCall]] = None) -> List[PipelineResult]:
        """Runs the full 10-layer pipeline in optimized batches."""
        
        # --- A. Input boundary ---
        # L0 (mock session for all)
        session = self.router.load_session(session_id)
        
        # L1 & L2 (preprocess each)
        preprocessed_data = []
        for text in texts:
            preprocessed_data.append({
                "text": text,
                "isolated": self.isolator.isolate(text),
                "px": self.perplexity.score(text)
            })

        # --- B. Detection (Batched) ---
        # L3 & L5 (Rule Engine & LLM)
        detect_results = self.detector.detect_batch(texts)
        
        # L4 (ML Classifier Batched)
        ml_scores = self.ml_classifier.predict_batch(texts)
        
        # --- C. Pre-execution & Beyond ---
        pipeline_results = []
        for i, text in enumerate(texts):
            p_data = preprocessed_data[i]
            d_res = detect_results[i]
            ml_score = ml_scores[i]

            if p_data["px"] > 75.0:
                res = PipelineResult("BLOCKED", text, None, verdict="INJECTION", reason="High perplexity (obfuscation detected)", layer_triggered="L2")
                pipeline_results.append(res)
                continue

            final_verdict = d_res.verdict
            if ml_score > 0.9:
                final_verdict = "INJECTION"
            elif ml_score > 0.5 and final_verdict == "SAFE":
                final_verdict = "SUSPICIOUS"

            if final_verdict == "INJECTION":
                res = PipelineResult("BLOCKED", text, None, verdict="INJECTION", reason="Detection engine flagged input", layer_triggered="L6")
            elif final_verdict == "SUSPICIOUS":
                res = PipelineResult("SANITIZED", text, f"Strictly answer: {p_data['isolated']}", verdict="SUSPICIOUS", reason="Suspicious signals detected", layer_triggered="L6")
            else:
                res = PipelineResult("ALLOWED", text, text, verdict="SAFE", reason="Passed all checks", layer_triggered="L7 (Pass)")

            # Mock LLM inference and Post-generation
            if res.status != "BLOCKED":
                llm_output = mock_llm_responses[i] if mock_llm_responses and i < len(mock_llm_responses) else "Safe response."
                tools = mock_tools_list[i] if mock_tools_list and i < len(mock_tools_list) else []
                
                # L9 Agentic Guard
                if not self.tool_validator.validate_tools(tools):
                    res = PipelineResult("BLOCKED", text, res.final_input, verdict="INJECTION", reason="Malicious tool call blocked", layer_triggered="L9")
                else:
                    # L7 Output Validator
                    if not self.output_validator.validate(text, llm_output):
                        llm_output = self.arr.rewrite(llm_output)
                        res.status = "REWRITTEN"
                        res.layer_triggered = "L8"
                    res.llm_output = llm_output

            pipeline_results.append(res)
            self.monitor.monitor(session, res)

        return pipeline_results
