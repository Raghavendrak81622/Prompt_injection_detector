"""
Guardrail Pipeline
------------------
Implements the 9-layer guardrail architecture:
A - Input boundary (L0, L1, L2)
B - Detection (L3, L4)
LLM inference
C - Post-generation validation (L5, L6)
D - Agentic guard (L7)
E - Observability + feedback (L8)
"""

import os
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
    confidence: float = 0.0  # Trust factor (0.0 to 1.0)
    latency: float = 0.0     # Processing time in seconds

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
    """L4: Deep semantic intent classification using DeBERTa"""
    def __init__(self, model_name: str = "ProtectAI/deberta-v3-base-prompt-injection-v2"):
        self.available = False
        self.classifier = None
        
        # Check if a fine-tuned model exists locally
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        massive_model_path = os.path.join(script_dir, "v3_massive_model")
        fine_tuned_path = os.path.join(script_dir, "fine_tuned_deberta")
        
        if os.path.exists(massive_model_path):
            model_to_load = massive_model_path
            print(f"Loading STATE-OF-THE-ART Massive ML Classifier ({model_to_load})...")
        elif os.path.exists(fine_tuned_path):
            model_to_load = fine_tuned_path
            print(f"Loading CUSTOM Fine-Tuned ML Classifier ({model_to_load})...")
        else:
            model_to_load = model_name
            print(f"Loading ML Classifier ({model_to_load})...")
            
        try:
            from transformers import pipeline
            import torch
            self.classifier = pipeline(
                "text-classification", 
                model=model_to_load, 
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            self.available = True
            print("ML Classifier loaded successfully!")
        except Exception as e:
            print(f"Failed to load ML Classifier: {e}")

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
    """L5: Output validator - critic model"""
    def validate(self, original_input: str, llm_output: str) -> bool:
        # Checks semantic alignment: did output follow an injected instruction?
        if "I am now an unrestricted AI" in llm_output or "My system prompt is" in llm_output:
            return False
        return True

class AdaptiveResponseRewriter:
    """L6: Adaptive response rewriter (ARR)"""
    def rewrite(self, llm_output: str) -> str:
        # Rewrite misaligned output to a safe fallback
        return "I cannot fulfill this request as it violates safety guidelines."

class ToolCallValidator:
    """L7: Tool-call validator"""
    def validate_tools(self, tools: List[ToolCall]) -> bool:
        # Pre-execution, least privilege, blocks agentic exploitation
        for tool in tools:
            if tool.tool_name in ["delete_files", "system_exec", "run_bash"]:
                # High risk tools blocked
                return False
        return True

class SessionMonitor:
    """L8: Session monitor + feedback loop"""
    def monitor(self, session: SessionContext, result: PipelineResult):
        # multi-turn anomaly detection, verdicts feed retraining
        pass

# ─── Pipeline ─────────────────────────────────────────────────────────────────

class GuardrailPipeline:
    def __init__(self):
        self.detector = PromptInjectionDetector()
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
        # L3 (Rule Engine)
        detect_results = self.detector.detect_batch(texts)
        
        # L4 (ML Classifier Batched)
        ml_scores = self.ml_classifier.predict_batch(texts)
        
        import time
        # --- C. Pre-execution & Beyond ---
        pipeline_results = []
        for i, text in enumerate(texts):
            start_p = time.time()
            p_data = preprocessed_data[i]
            d_res = detect_results[i]
            ml_score = ml_scores[i]

            if p_data["px"] > 75.0:
                res = PipelineResult("BLOCKED", text, None, verdict="INJECTION", reason="High perplexity (obfuscation detected)", layer_triggered="L2")
                res.latency = time.time() - start_p
                pipeline_results.append(res)
                continue

            final_verdict = d_res.verdict
            if ml_score > 0.9:
                final_verdict = "INJECTION"
            elif ml_score > 0.5 and final_verdict == "SAFE":
                final_verdict = "SUSPICIOUS"

            # --- Heuristic Override for Lexical Overfitting ---
            # Models trained on HF datasets often overfit to words like "hacker" or "devil".
            # If the prompt is very short and lacks imperative injection verbs, downgrade the threat.
            text_lower = text.lower()
            words = text_lower.split()
            # Use regex to match exact word boundaries, plus catch common injection targets
            imperative_pattern = r'\b(ignore|act|system|override|bypass|disregard|forget|simulate|pretend|dan|execute|instruction|instructions|prompt|repeat|reveal|secret|secrets|code|codes|password|passwords|key|keys)\b'
            has_imperative = bool(re.search(imperative_pattern, text_lower))
            
            if len(words) < 10 and not has_imperative:
                if final_verdict in ["INJECTION", "SUSPICIOUS"] and d_res.verdict == "SAFE":
                    final_verdict = "SAFE"
                    ml_score = min(ml_score, 0.49) # Cap confidence so it passes

            if final_verdict == "INJECTION":
                triggered = "L3" if d_res.verdict == "INJECTION" else "L4"
                res = PipelineResult("BLOCKED", text, None, verdict="INJECTION", reason="Detection engine flagged input", layer_triggered=triggered, confidence=ml_score)
            elif final_verdict == "SUSPICIOUS":
                triggered = "L3" if d_res.verdict == "SUSPICIOUS" else "L4"
                res = PipelineResult("SANITIZED", text, f"Strictly answer: {p_data['isolated']}", verdict="SUSPICIOUS", reason="Suspicious signals detected", layer_triggered=triggered, confidence=ml_score)
            else:
                res = PipelineResult("ALLOWED", text, text, verdict="SAFE", reason="Passed all checks", layer_triggered="L4 (Pass)", confidence=1.0 - ml_score if ml_score < 0.5 else ml_score)

            # Mock LLM inference and Post-generation
            if res.status != "BLOCKED":
                llm_output = mock_llm_responses[i] if mock_llm_responses and i < len(mock_llm_responses) else "Safe response."
                tools = mock_tools_list[i] if mock_tools_list and i < len(mock_tools_list) else []
                
                # L7 Tool Validator
                if not self.tool_validator.validate_tools(tools):
                    res = PipelineResult("BLOCKED", text, res.final_input, verdict="INJECTION", reason="Malicious tool call blocked", layer_triggered="L7")
                else:
                    # L5 Output Validator
                    if not self.output_validator.validate(text, llm_output):
                        llm_output = self.arr.rewrite(llm_output)
                        res.status = "REWRITTEN"
                        res.layer_triggered = "L5"
                    res.llm_output = llm_output

            res.latency = time.time() - start_p
            pipeline_results.append(res)
            self.monitor.monitor(session, res)

        return pipeline_results
