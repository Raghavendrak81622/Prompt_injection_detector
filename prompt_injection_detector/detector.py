"""
Detector
--------
Combines RuleEngine + LLMClassifier into a single easy-to-use interface.

Decision logic:
  Rule score ≥ 7            → immediately INJECTION (skip LLM to save cost)
  Rule score 3–6.99         → call LLM to arbitrate
  Rule score < 3            → SAFE (LLM called only in strict mode)
  LLM says INJECTION        → final verdict INJECTION
  LLM says SUSPICIOUS       → final verdict SUSPICIOUS
  LLM says SAFE             → final verdict SAFE (overrides rule score < 5)
"""

from dataclasses import dataclass, field
from typing import Optional

from .rule_engine import RuleEngine, RuleResult
from .llm_classifier import LLMClassifier, LLMResult
from .learner import Learner


# ─── Result ───────────────────────────────────────────────────────────────────

@dataclass
class DetectionResult:
    verdict: str                        # "SAFE" | "SUSPICIOUS" | "INJECTION"
    confidence: float                   # 0.0 – 1.0
    rule_score: float                   # raw score from RuleEngine (0–10)
    triggered_categories: list          # pattern categories that fired
    matched_patterns: list              # individual patterns that matched
    ngram_hits: list                    # n-gram sequences that matched
    safe_context: bool                  # safe-context clue found
    llm_verdict: Optional[str]          # LLM verdict (or None if not called)
    llm_reasoning: Optional[str]        # LLM explanation
    llm_injection_type: Optional[str]   # LLM-identified injection type
    entry_id: Optional[str]             # ID for submitting feedback later
    summary: str = field(init=False)    # human-readable one-liner

    def __post_init__(self):
        icon = {"SAFE": "✅", "SUSPICIOUS": "⚠️", "INJECTION": "🚨"}.get(
            self.verdict, "❓"
        )
        self.summary = (
            f"{icon} {self.verdict}  |  rule={self.rule_score:.1f}/10  "
            f"|  confidence={self.confidence:.0%}"
        )
        if self.triggered_categories:
            self.summary += f"  |  categories: {', '.join(self.triggered_categories)}"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "rule_score": self.rule_score,
            "triggered_categories": self.triggered_categories,
            "matched_patterns_count": len(self.matched_patterns),
            "ngram_hits": self.ngram_hits,
            "safe_context": self.safe_context,
            "llm_verdict": self.llm_verdict,
            "llm_reasoning": self.llm_reasoning,
            "llm_injection_type": self.llm_injection_type,
            "entry_id": self.entry_id,
        }


# ─── Detector ─────────────────────────────────────────────────────────────────

class PromptInjectionDetector:
    """
    Main class.  Instantiate once, call detect() for each prompt.

    Parameters
    ----------
    api_key : str, optional
        Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
    log_path : str
        Where to persist the detection log (JSON).
    strict : bool
        If True, call the LLM even for low rule-engine scores.
    llm_threshold : float
        Rule score above which the LLM is consulted (default 2.5).
    auto_inject_threshold : float
        Rule score above which INJECTION is returned without the LLM (default 7).
    """

    def __init__(
        self,
        api_key: str = None,
        log_path: str = "detections.json",
        strict: bool = False,
        llm_threshold: float = 2.5,
        auto_inject_threshold: float = 7.0,
    ):
        self._learner = Learner(log_path=log_path)
        self._rule_engine = RuleEngine(
            custom_patterns=self._learner.get_custom_patterns()
        )
        self._llm = LLMClassifier(api_key=api_key)
        self.strict = strict
        self.llm_threshold = llm_threshold
        self.auto_inject_threshold = auto_inject_threshold

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> DetectionResult:
        """Analyse a single text and return a DetectionResult."""

        # ── Layer 1: Rule engine ───────────────────────────────────────────
        rule: RuleResult = self._rule_engine.analyze(text)

        # ── Layer 2: LLM (conditional) ────────────────────────────────────
        llm_result: Optional[LLMResult] = None
        call_llm = (
            self._llm.available and (
                rule.score >= self.llm_threshold or self.strict
            )
            and rule.score < self.auto_inject_threshold   # no need if already obvious
        )

        if call_llm:
            llm_result = self._llm.classify(text)

        # ── Layer 3: Final verdict ─────────────────────────────────────────
        verdict, confidence = self._decide(rule, llm_result)

        # ── Log & return ──────────────────────────────────────────────────
        entry_id = self._learner.record(
            text=text,
            rule_score=rule.score,
            verdict=verdict,
            categories=rule.triggered_categories,
            llm_verdict=llm_result.verdict if llm_result else None,
        )

        return DetectionResult(
            verdict=verdict,
            confidence=confidence,
            rule_score=rule.score,
            triggered_categories=rule.triggered_categories,
            matched_patterns=rule.matched_patterns,
            ngram_hits=rule.ngram_hits,
            safe_context=rule.safe_context,
            llm_verdict=llm_result.verdict if llm_result else None,
            llm_reasoning=llm_result.reasoning if llm_result else None,
            llm_injection_type=llm_result.injection_type if llm_result else None,
            entry_id=entry_id,
        )

    def detect_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Analyse a list of prompts. Returns results in the same order."""
        return [self.detect(t) for t in texts]

    def feedback(self, entry_id: str, is_correct: bool) -> bool:
        """
        Provide feedback on a detection.
        is_correct=True  → true positive (injection was real)
        is_correct=False → false positive (was actually safe)
        Returns True if the entry was found.
        """
        label = "tp" if is_correct else "fp"
        updated = self._learner.submit_feedback(entry_id, label)
        if updated:
            # Refresh learned patterns in the rule engine
            self._rule_engine = RuleEngine(
                custom_patterns=self._learner.get_custom_patterns()
            )
        return updated

    def stats(self) -> dict:
        return self._learner.stats()

    def recent_detections(self, n: int = 10) -> list:
        return self._learner.recent(n)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _decide(
        self,
        rule: RuleResult,
        llm: Optional[LLMResult],
    ) -> tuple[str, float]:
        """
        Return (verdict, confidence).

        Fusion logic:
        - Rule score ≥ auto_inject_threshold → INJECTION, high confidence
        - Both agree → amplify confidence
        - Only rule fires → use rule score to set verdict
        - LLM says SAFE but rule fired moderately → SUSPICIOUS
        - LLM drives when rule score is low and strict mode is on
        """
        score = rule.score

        # ── Fast path: extremely obvious injection ─────────────────────────
        if score >= self.auto_inject_threshold:
            return "INJECTION", min(0.95, 0.7 + score / 100)

        # ── No signals at all ─────────────────────────────────────────────
        if score == 0 and llm is None:
            return "SAFE", 0.95

        if score == 0 and llm is not None:
            if llm.verdict == "INJECTION":
                return "INJECTION", llm.confidence
            if llm.verdict == "SUSPICIOUS":
                return "SUSPICIOUS", llm.confidence
            return "SAFE", max(0.85, llm.confidence)

        # ── Rule fired, LLM not called ────────────────────────────────────
        if llm is None:
            if score >= 5:
                return "INJECTION", self._score_to_confidence(score)
            if score >= 2.5:
                return "SUSPICIOUS", self._score_to_confidence(score)
            return "SAFE", 0.8

        # ── Both rule and LLM have opinions ───────────────────────────────
        llm_v = llm.verdict

        if llm_v == "INJECTION":
            # LLM says injection — believe it, boost with rule score
            conf = min(0.97, llm.confidence + score * 0.02)
            return "INJECTION", conf

        if llm_v == "SUSPICIOUS":
            if score >= 5:
                return "INJECTION", self._score_to_confidence(score) * 0.9
            return "SUSPICIOUS", max(llm.confidence, self._score_to_confidence(score))

        if llm_v == "SAFE":
            if score >= 6:
                # Rule is very confident — override LLM's safe verdict
                return "SUSPICIOUS", 0.65
            # LLM says safe and rule score is moderate — trust LLM
            if rule.safe_context:
                return "SAFE", 0.85
            return "SAFE", 0.75

        # Unknown LLM verdict fallback
        return ("INJECTION" if score >= 5 else "SUSPICIOUS"), self._score_to_confidence(score)

    @staticmethod
    def _score_to_confidence(score: float) -> float:
        """Map a rule score in [0, 10] to a confidence in [0, 1]."""
        return round(min(1.0, score / 10.0 * 0.9 + 0.1), 3)
