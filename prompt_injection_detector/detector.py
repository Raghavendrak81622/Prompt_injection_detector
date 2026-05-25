"""
Detector
--------
Easy-to-use interface for the RuleEngine.
"""

from dataclasses import dataclass, field
from typing import Optional

from .rule_engine import RuleEngine, RuleResult
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
            "entry_id": self.entry_id,
        }


# ─── Detector ─────────────────────────────────────────────────────────────────

class PromptInjectionDetector:
    """
    Main class.  Instantiate once, call detect() for each prompt.

    Parameters
    ----------
    log_path : str
        Where to persist the detection log (JSON).
    auto_inject_threshold : float
        Rule score above which INJECTION is returned.
    """

    def __init__(
        self,
        log_path: str = "detections.json",
        auto_inject_threshold: float = 5.0,
    ):
        self._learner = Learner(log_path=log_path)
        self._rule_engine = RuleEngine(
            custom_patterns=self._learner.get_custom_patterns()
        )
        self.auto_inject_threshold = auto_inject_threshold

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> DetectionResult:
        """Analyse a single text and return a DetectionResult."""

        # ── Layer 1: Rule engine ───────────────────────────────────────────
        rule: RuleResult = self._rule_engine.analyze(text)

        # ── Layer 3: Final verdict ─────────────────────────────────────────
        verdict, confidence = self._decide(rule)

        # ── Log & return ──────────────────────────────────────────────────
        entry_id = self._learner.record(
            text=text,
            rule_score=rule.score,
            verdict=verdict,
            categories=rule.triggered_categories,
        )

        return DetectionResult(
            verdict=verdict,
            confidence=confidence,
            rule_score=rule.score,
            triggered_categories=rule.triggered_categories,
            matched_patterns=rule.matched_patterns,
            ngram_hits=rule.ngram_hits,
            safe_context=rule.safe_context,
            entry_id=entry_id,
        )

    def detect_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Analyse a list of prompts efficiently."""
        results = []
        log_entries = []
        
        for text in texts:
            # Analyze
            rule = self._rule_engine.analyze(text)
            verdict, confidence = self._decide(rule)
            
            # Prepare result object
            res = DetectionResult(
                verdict=verdict,
                confidence=confidence,
                rule_score=rule.score,
                triggered_categories=rule.triggered_categories,
                matched_patterns=rule.matched_patterns,
                ngram_hits=rule.ngram_hits,
                safe_context=rule.safe_context,
                entry_id=None, # Will be set after batch record
            )
            results.append(res)
            
            # Prepare for batch log
            log_entries.append({
                "text": text,
                "rule_score": rule.score,
                "verdict": verdict,
                "categories": rule.triggered_categories,
            })
            
        # Save all logs in one go
        self._learner.record_batch(log_entries)
        return results

    def feedback(self, entry_id: str, is_correct: bool) -> bool:
        """
        Provide feedback on a detection.
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
    ) -> tuple[str, float]:
        """
        Return (verdict, confidence).
        """
        score = rule.score

        if score >= self.auto_inject_threshold:
            return "INJECTION", min(0.95, 0.7 + score / 100)
            
        if score == 0:
            return "SAFE", 0.95

        if score >= 2.5:
            return "SUSPICIOUS", self._score_to_confidence(score)

        return "SAFE", 0.8

    @staticmethod
    def _score_to_confidence(score: float) -> float:
        """Map a rule score in [0, 10] to a confidence in [0, 1]."""
        return round(min(1.0, score / 10.0 * 0.9 + 0.1), 3)

