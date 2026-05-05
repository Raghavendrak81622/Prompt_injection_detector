#!/usr/bin/env python3
"""
Benchmark script for the 10-layer Guardrail Pipeline.
Calculates Accuracy, Precision, Recall, and Latency.
"""

import sys
import os
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

from prompt_injection_detector import GuardrailPipeline
from test_prompts import SAFE_PROMPTS, SUSPICIOUS_PROMPTS, INJECTION_PROMPTS

def main():
    print("\n" + "═" * 70)
    print("  🛡️  Guardrail Pipeline Benchmark")
    print("═" * 70)
    
    print("Initializing Pipeline (loading ML models to GPU)...")
    start_init = time.time()
    pipeline = GuardrailPipeline()
    print(f"Initialization took {time.time() - start_init:.2f}s")
    
    # Combined dataset: (text, is_injection_or_suspicious)
    dataset = []
    for p in SAFE_PROMPTS:
        dataset.append((p, False, "SAFE"))
    for p in SUSPICIOUS_PROMPTS:
        dataset.append((p, True, "SUSPICIOUS"))
    for p in INJECTION_PROMPTS:
        dataset.append((p, True, "INJECTION"))

    stats = {
        "tp": 0,  # True Positives (Caught injection)
        "tn": 0,  # True Negatives (Allowed safe)
        "fp": 0,  # False Positives (Blocked safe)
        "fn": 0,  # False Negatives (Missed injection)
    }
    
    latencies = []
    
    print(f"\nRunning {len(dataset)} tests...")
    print("-" * 70)
    print(f"{'STATUS':<10} | {'VERDICT':<10} | {'LATENCY':<8} | {'PROMPT'}")
    print("-" * 70)

    for text, expected_malicious, category in dataset:
        start_req = time.time()
        result = pipeline.run(text)
        latency = time.time() - start_req
        latencies.append(latency)
        
        # In our pipeline, BLOCKED or SANITIZED means it caught something
        actual_malicious = (result.status in ["BLOCKED", "SANITIZED", "REWRITTEN"])
        
        if actual_malicious and expected_malicious:
            stats["tp"] += 1
            icon = "✅"
        elif not actual_malicious and not expected_malicious:
            stats["tn"] += 1
            icon = "✅"
        elif actual_malicious and not expected_malicious:
            stats["fp"] += 1
            icon = "❌ FP"
        else:
            stats["fn"] += 1
            icon = "❌ FN"

        print(f"{icon:<10} | {result.verdict:<10} | {latency*1000:>6.1f}ms | {text[:45]}...")

    # --- Calculate Metrics ---
    total = len(dataset)
    accuracy = (stats["tp"] + stats["tn"]) / total
    precision = stats["tp"] / (stats["tp"] + stats["fp"]) if (stats["tp"] + stats["fp"]) > 0 else 0
    recall = stats["tp"] / (stats["tp"] + stats["fn"]) if (stats["tp"] + stats["fn"]) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    avg_latency = sum(latencies) / total * 1000

    print("\n" + "═" * 70)
    print("  📊 PERFORMANCE METRICS")
    print("═" * 70)
    print(f"  Overall Accuracy:  {accuracy:>7.2%}")
    print(f"  Precision:         {precision:>7.2%} (How many blocks were correct)")
    print(f"  Recall:            {recall:>7.2%} (How many injections were caught)")
    print(f"  F1-Score:          {f1:>7.2%}")
    print("-" * 70)
    print(f"  Avg Latency:       {avg_latency:>7.1f}ms")
    print(f"  Max Latency:       {max(latencies)*1000:>7.1f}ms")
    print(f"  Total TP/TN:       {stats['tp']}/{stats['tn']}")
    print(f"  Total FP/FN:       {stats['fp']}/{stats['fn']}")
    print("═" * 70 + "\n")

if __name__ == "__main__":
    main()
