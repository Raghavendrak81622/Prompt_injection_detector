"""
Rule Engine
-----------
Runs the regex pattern library against the input, applies weighting,
normalises text (unicode, leet-speak, spacing tricks) and checks
malicious n-gram sequences.
"""

import re
import unicodedata
from collections import defaultdict
from typing import NamedTuple

from .patterns import PATTERNS, MALICIOUS_NGRAMS, SAFE_CONTEXT_CLUES


# ─── Result type ──────────────────────────────────────────────────────────────

class RuleResult(NamedTuple):
    score: float                     # 0.0 – 10.0
    triggered_categories: list       # list of category names hit
    matched_patterns: list           # list of (category, pattern_str) tuples
    ngram_hits: list                 # list of triggered n-gram tuples
    safe_context: bool               # True if safe-context clues found
    normalized_text: str             # text after normalization


# ─── Normalisation helpers ────────────────────────────────────────────────────

_LEET = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a',
    '5': 's', '6': 'g', '7': 't', '8': 'b', '@': 'a',
    '$': 's', '!': 'i', '+': 't',
})

_UNICODE_HOMOGLYPHS = {
    '\u0456': 'i', '\u04CF': 'i', '\u1EC9': 'i', '\u0131': 'i',  # i-likes
    '\u0430': 'a', '\u03B1': 'a',                                   # a-likes
    '\u0435': 'e', '\u03B5': 'e',                                   # e-likes
    '\u03BF': 'o', '\u0D20': 'o',                                   # o-likes
    '\u0441': 'c',                                                   # c-likes
    '\u0440': 'r',                                                   # r-likes
    '\u0455': 's',                                                   # s-likes
    '\u0442': 't',                                                   # t-likes
}


def normalize_text(text: str) -> str:
    """Return a normalised copy useful for pattern matching."""
    # 1. Unicode normalisation
    text = unicodedata.normalize('NFKC', text)

    # 2. Homoglyph replacement
    for char, replacement in _UNICODE_HOMOGLYPHS.items():
        text = text.replace(char, replacement)

    # 3. Lowercase
    text = text.lower()

    # 4. Remove excess whitespace between characters (spaced-out evasion)
    #    e.g. "i g n o r e" → "ignore"
    text = re.sub(r'(?<=\w)\s(?=\w)', '', text)

    # 5. Leet-speak translation
    text = text.translate(_LEET)

    # 6. Remove zero-width / invisible characters
    text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', text)

    # 7. Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text).strip()

    return text


# ─── Engine ───────────────────────────────────────────────────────────────────

class RuleEngine:
    """
    Scores a text string by running all categories of regex patterns
    and checking for known malicious n-gram sequences.
    """

    def __init__(self, custom_patterns: dict = None):
        """
        custom_patterns: same shape as PATTERNS — merged at runtime
        so learned patterns are included automatically.
        """
        self._patterns = dict(PATTERNS)
        if custom_patterns:
            for cat, data in custom_patterns.items():
                if cat in self._patterns:
                    self._patterns[cat]['patterns'].extend(data.get('patterns', []))
                else:
                    self._patterns[cat] = data

        # Pre-compile all regexes for speed
        self._compiled: dict[str, list[re.Pattern]] = {}
        for category, data in self._patterns.items():
            compiled = []
            for pat in data['patterns']:
                try:
                    compiled.append(re.compile(pat, re.IGNORECASE | re.DOTALL))
                except re.error:
                    pass  # skip malformed patterns
            self._compiled[category] = compiled

        # Pre-compile safe-context patterns
        self._safe_patterns = [
            re.compile(p, re.IGNORECASE) for p in SAFE_CONTEXT_CLUES
        ]

    # ── public API ────────────────────────────────────────────────────────────

    def analyze(self, text: str) -> RuleResult:
        original = text
        normalized = normalize_text(text)

        triggered_categories = []
        matched_patterns = []
        category_scores: dict[str, float] = defaultdict(float)

        # Run patterns against BOTH original and normalized text
        for category, patterns in self._compiled.items():
            weight = self._patterns[category].get('weight', 5)
            for pat in patterns:
                for candidate in (original, normalized):
                    if pat.search(candidate):
                        if category not in triggered_categories:
                            triggered_categories.append(category)
                        matched_patterns.append((category, pat.pattern))
                        category_scores[category] += weight
                        break   # one hit per pattern per category is enough

        # N-gram analysis on normalised tokens
        ngram_hits = self._check_ngrams(normalized)

        # Safe-context detection
        safe_context = any(p.search(original) for p in self._safe_patterns)

        # ── Score calculation ──────────────────────────────────────────────
        raw_score = self._calculate_score(category_scores, ngram_hits, safe_context)

        return RuleResult(
            score=raw_score,
            triggered_categories=triggered_categories,
            matched_patterns=matched_patterns,
            ngram_hits=ngram_hits,
            safe_context=safe_context,
            normalized_text=normalized,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _check_ngrams(self, text: str) -> list:
        """Look for malicious n-gram sequences in the token stream."""
        tokens = re.findall(r'\b\w+\b', text.lower())
        hits = []
        for ngram in MALICIOUS_NGRAMS:
            n = len(ngram)
            for i in range(len(tokens) - n + 1):
                if tuple(tokens[i:i + n]) == ngram:
                    hits.append(ngram)
                    break   # only count each n-gram once
        return hits

    def _calculate_score(
        self,
        category_scores: dict,
        ngram_hits: list,
        safe_context: bool,
    ) -> float:
        """
        Produce a score in [0, 10].

        Rules:
        - Each category contributes up to its weight once (capped).
        - Multiple categories compound: each additional one adds 50 % of
          its marginal contribution.
        - Each unique n-gram hit adds 0.5.
        - CRITICAL-severity hit always floors the score at 7.
        - Safe-context clue reduces score by 30 % (floor 0).
        """
        if not category_scores and not ngram_hits:
            return 0.0

        # Sort by contribution descending
        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

        score = 0.0
        for idx, (cat, raw) in enumerate(sorted_cats):
            weight = self._patterns[cat].get('weight', 5)
            # Cap per-category contribution, diminish with rank
            contribution = min(raw, weight * 2) * (0.5 ** idx)
            score += contribution

        # N-gram bonus
        score += len(ngram_hits) * 0.5

        # CRITICAL floor
        critical_cats = [
            c for c in category_scores
            if self._patterns[c].get('severity') == 'CRITICAL'
        ]
        if critical_cats:
            score = max(score, 7.0)

        # Safe-context discount
        if safe_context:
            score *= 0.7

        return round(min(score, 10.0), 2)
