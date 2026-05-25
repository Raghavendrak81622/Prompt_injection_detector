"""
Learner
-------
Persists detection results and user feedback.
When enough confirmed injections accumulate, it extracts recurring
phrases and adds them as new custom patterns — making the detector
progressively smarter without manual effort.
"""

import json
import os
import re
import hashlib
from datetime import datetime
from collections import Counter
from typing import Optional


class Learner:
    """
    Manages a local JSON log of detections + feedback, and periodically
    extracts new patterns from confirmed-injection examples.
    """

    # How many confirmed injections must share a phrase before it becomes a pattern
    PATTERN_MIN_FREQUENCY = 3

    # Minimum phrase token length to consider as a candidate pattern
    MIN_NGRAM = 3
    MAX_NGRAM = 7

    def __init__(self, log_path: str = "detections.json"):
        self.log_path = log_path
        self._log: list[dict] = []
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def record(
        self,
        text: str,
        rule_score: float,
        verdict: str,
        categories: list,
        autosave: bool = True,
    ) -> str:
        """
        Store a detection result.  Returns a unique ID for later feedback.
        """
        entry_id = hashlib.md5(
            (text + datetime.utcnow().isoformat()).encode()
        ).hexdigest()[:12]

        entry = {
            "id": entry_id,
            "timestamp": datetime.utcnow().isoformat(),
            "text_preview": text[:120],
            "rule_score": rule_score,
            "verdict": verdict,
            "categories": categories,
            "feedback": None,   # "tp" | "fp" | "fn"
        }
        self._log.append(entry)
        if autosave:
            self._save()
        return entry_id

    def record_batch(self, entries: list[dict]):
        """Store multiple results and save once."""
        for entry in entries:
            eid = hashlib.md5(
                (entry["text"] + datetime.utcnow().isoformat()).encode()
            ).hexdigest()[:12]
            
            log_entry = {
                "id": eid,
                "timestamp": datetime.utcnow().isoformat(),
                "text_preview": entry["text"][:120],
                "rule_score": entry["rule_score"],
                "verdict": entry["verdict"],
                "categories": entry["categories"],
                "feedback": None,
            }
            self._log.append(log_entry)
        self._save()

    def submit_feedback(self, entry_id: str, feedback: str) -> bool:
        """
        feedback: "tp" (true positive), "fp" (false positive), "fn" (false negative)
        Returns True if the entry was found and updated.
        """
        feedback = feedback.lower().strip()
        if feedback not in ("tp", "fp", "fn"):
            return False

        for entry in self._log:
            if entry["id"] == entry_id:
                entry["feedback"] = feedback
                self._save()
                return True
        return False

    def get_custom_patterns(self) -> dict:
        """
        Analyse confirmed true-positive examples and extract recurring
        n-grams as new regex patterns.

        Returns a dict in the same shape as PATTERNS so RuleEngine
        can merge it directly.
        """
        confirmed = [
            e for e in self._log
            if e.get("feedback") in ("tp", "fn")
        ]
        if len(confirmed) < self.PATTERN_MIN_FREQUENCY:
            return {}

        phrase_counter: Counter = Counter()
        for entry in confirmed:
            text = entry["text_preview"].lower()
            tokens = re.findall(r'\b\w+\b', text)
            for n in range(self.MIN_NGRAM, self.MAX_NGRAM + 1):
                for i in range(len(tokens) - n + 1):
                    phrase = " ".join(tokens[i:i + n])
                    phrase_counter[phrase] += 1

        # Keep only phrases that appear in at least PATTERN_MIN_FREQUENCY examples
        hot_phrases = [
            phrase for phrase, count in phrase_counter.items()
            if count >= self.PATTERN_MIN_FREQUENCY
        ]

        if not hot_phrases:
            return {}

        # Convert phrases to simple regex patterns
        new_patterns = []
        for phrase in hot_phrases:
            # Escape and allow flexible whitespace between tokens
            tokens = phrase.split()
            pattern = r'\s+'.join(re.escape(t) for t in tokens)
            new_patterns.append(pattern)

        return {
            "learned_patterns": {
                "severity": "HIGH",
                "weight": 7,
                "patterns": new_patterns,
            }
        }

    def stats(self) -> dict:
        """Return a summary of the detection log."""
        total = len(self._log)
        by_verdict = Counter(e["verdict"] for e in self._log)
        feedback_counts = Counter(
            e["feedback"] for e in self._log if e["feedback"]
        )
        return {
            "total_analyzed": total,
            "by_verdict": dict(by_verdict),
            "feedback": dict(feedback_counts),
            "false_positive_rate": round(
                feedback_counts.get("fp", 0) / max(total, 1), 3
            ),
        }

    def recent(self, n: int = 10) -> list:
        """Return the n most recent log entries."""
        return self._log[-n:]

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    self._log = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._log = []
        else:
            self._log = []

    def _save(self):
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(self._log, f, indent=2, ensure_ascii=False)
        except IOError:
            pass   # non-fatal: just skip saving if the FS is read-only
