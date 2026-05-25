#!/usr/bin/env python3
"""
Benchmark script for the 9-layer Guardrail Pipeline.
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
    print("\n" + "=" * 70)
    print("  [BENCHMARK] Guardrail Pipeline")
    print("=" * 70)
    
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
    # --- Run Batch Processing ---
    print(f"\nRunning {len(dataset)} tests in batch mode...")
    print("-" * 70)
    print(f"{'STATUS':<10} | {'VERDICT':<10} | {'LATENCY':<8} | {'PROMPT'}")
    print("-" * 70)

    prompts_to_run = [d[0] for d in dataset]
    start_batch = time.time()
    results = pipeline.run_batch(prompts_to_run)
    batch_latency = (time.time() - start_batch) * 1000
    
    for i, (text, expected_malicious, category) in enumerate(dataset):
        result = results[i]
        
        # In our pipeline, BLOCKED or SANITIZED means it caught something
        actual_malicious = (result.status in ["BLOCKED", "SANITIZED", "REWRITTEN"])
        
        if actual_malicious and expected_malicious:
            stats["tp"] += 1
            icon = "[OK]"
        elif not actual_malicious and not expected_malicious:
            stats["tn"] += 1
            icon = "[OK]"
        elif actual_malicious and not expected_malicious:
            stats["fp"] += 1
            icon = "[FP]"
        else:
            stats["fn"] += 1
            icon = "[FN]"

        print(f"{icon:<10} | {result.verdict:<10} | {'batch':>8} | {text[:45]}...")

    # --- Calculate Metrics ---
    total = len(dataset)
    accuracy = (stats["tp"] + stats["tn"]) / total
    precision = stats["tp"] / (stats["tp"] + stats["fp"]) if (stats["tp"] + stats["fp"]) > 0 else 0
    recall = stats["tp"] / (stats["tp"] + stats["fn"]) if (stats["tp"] + stats["fn"]) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    fpr = stats["fp"] / (stats["fp"] + stats["tn"]) if (stats["fp"] + stats["tn"]) > 0 else 0
    fnr = stats["fn"] / (stats["fn"] + stats["tp"]) if (stats["fn"] + stats["tp"]) > 0 else 0
    asr = fnr  # Attack Success Rate (successful bypasses)
    utility_accuracy = stats["tn"] / (stats["tn"] + stats["fp"]) if (stats["tn"] + stats["fp"]) > 0 else 0
    
    # Latency and Confidence stats
    latencies = [r.latency * 1000 for r in results if r.latency] # Convert to ms
    # If latencies is empty (pipeline didn't provide individual latencies), use batch avg
    if not latencies:
        avg_lat = batch_latency / total
        latencies = [avg_lat] * total
    
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.5)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    confidences = [r.confidence for r in results]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    
    # Category-wise stats
    cat_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    for i, (text, expected_malicious, category) in enumerate(dataset):
        result = results[i]
        actual_malicious = (result.status in ["BLOCKED", "SANITIZED", "REWRITTEN"])
        cat_stats[category]["total"] += 1
        if actual_malicious == expected_malicious:
            cat_stats[category]["correct"] += 1

    print("\n" + "=" * 70)
    print("  ENHANCED PERFORMANCE METRICS")
    print("=" * 70)
    
    print(f"  [ CORE CLASSIFICATION ]")
    print(f"  Overall Accuracy:  {accuracy:>7.2%}")
    print(f"  Precision:         {precision:>7.2%}")
    print(f"  Recall (Security): {recall:>7.2%}")
    print(f"  F1-Score:          {f1:>7.2%}")
    print(f"  Utility Accuracy:  {utility_accuracy:>7.2%} (True Neg Rate)")
    
    print(f"\n  [ SECURITY GATE METRICS ]")
    print(f"  FPR (False Pos):   {fpr:>7.2%} (UX Friction)")
    print(f"  FNR (False Neg):   {fnr:>7.2%} (Security Leak)")
    print(f"  ASR (Attack Suc):  {asr:>7.2%} (Bypass Rate)")
    print(f"  Total Missed:      {stats['fn']:>7}")
    print(f"  Total False Alarms:{stats['fp']:>7}")
    
    print(f"\n  [ CATEGORICAL PERFORMANCE ]")
    for cat, data in cat_stats.items():
        cat_acc = data["correct"] / data["total"]
        print(f"  {cat:<18}: {cat_acc:>7.2%} ({data['correct']}/{data['total']})")
    
    print(f"\n  [ LATENCY & THROUGHPUT ]")
    print(f"  p50 (Median):      {p50:>7.1f} ms")
    print(f"  p95 (Tail):        {p95:>7.1f} ms")
    print(f"  p99 (Worst Case):  {p99:>7.1f} ms")
    print(f"  Avg Latency:       {batch_latency/total:>7.1f} ms")
    print(f"  Throughput:        {1000 / (batch_latency/total):>7.1f} prompts/sec")
    
    print(f"\n  [ CONFIDENCE ANALYSIS ]")
    print(f"  Avg Confidence:    {avg_conf:>7.2%}")
    print("-" * 70)
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
