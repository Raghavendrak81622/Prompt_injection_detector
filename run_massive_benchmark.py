import os
import sys
import time
from datasets import load_dataset

sys.path.insert(0, os.getcwd())
from prompt_injection_detector.pipeline import GuardrailPipeline

def run_benchmark():
    print("="*70)
    print("  MASSIVE BENCHMARK EVALUATION")
    print("="*70)

    print("Loading deepset/prompt-injections test dataset...")
    # This dataset has clear 0 (safe) and 1 (injection) labels
    # We will use the test split to ensure it's unseen data
    dataset = load_dataset("deepset/prompt-injections", split="train")
    
    # Get available counts
    safe_data = dataset.filter(lambda x: x['label'] == 0).shuffle(seed=42)
    inj_data = dataset.filter(lambda x: x['label'] == 1).shuffle(seed=42)
    
    # Take a representative sample (up to 250 of each)
    safe_limit = min(250, len(safe_data))
    inj_limit = min(250, len(inj_data))
    
    safe_data = safe_data.select(range(safe_limit))
    inj_data = inj_data.select(range(inj_limit))
    
    prompts_to_run = []
    expected_labels = []
    
    for row in safe_data:
        prompts_to_run.append(row['text'])
        expected_labels.append("SAFE")
        
    for row in inj_data:
        prompts_to_run.append(row['text'])
        expected_labels.append("INJECTION")

    print(f"Loaded {len(prompts_to_run)} prompts (250 SAFE, 250 INJECTION).")

    print("Initializing Massive ML Pipeline...")
    pipeline = GuardrailPipeline()
    
    print(f"Running batch inference on {len(prompts_to_run)} prompts...")
    start_time = time.time()
    results = pipeline.run_batch(prompts_to_run)
    total_time = time.time() - start_time
    
    # Calculate metrics
    tp = 0 # True Positive: Correctly blocked injection
    tn = 0 # True Negative: Correctly allowed safe
    fp = 0 # False Positive: Blocked safe prompt
    fn = 0 # False Negative: Allowed injection
    
    for i, res in enumerate(results):
        actual = res.verdict
        expected = expected_labels[i]
        
        is_flagged = actual in ["INJECTION", "SUSPICIOUS"]
        is_malicious = expected == "INJECTION"
        
        if is_malicious and is_flagged:
            tp += 1
        elif not is_malicious and not is_flagged:
            tn += 1
        elif not is_malicious and is_flagged:
            fp += 1
        elif is_malicious and not is_flagged:
            fn += 1
            
    total_tests = tp + tn + fp + fn
    accuracy = (tp + tn) / total_tests if total_tests else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0
    fpr = fp / (fp + tn) if (fp + tn) else 0
    asr = fn / (tp + fn) if (tp + fn) else 0 # Attack Success Rate
    
    print("\n" + "="*70)
    print("  FINAL BENCHMARK METRICS (deepset/prompt-injections)")
    print("="*70)
    print(f"Total Prompts Evaluated : {total_tests}")
    print(f"True Positives (Caught) : {tp}")
    print(f"True Negatives (Safe)   : {tn}")
    print(f"False Positives (Alarm) : {fp}  (Safe prompts blocked)")
    print(f"False Negatives (Missed): {fn}  (Injections that bypassed)")
    print("-" * 50)
    print(f"Accuracy               : {accuracy*100:.2f}%")
    print(f"Precision              : {precision*100:.2f}%")
    print(f"Recall (Security Rate) : {recall*100:.2f}%")
    print(f"F1 Score               : {f1*100:.2f}%")
    print(f"False Positive Rate    : {fpr*100:.2f}% (UX Friction)")
    print(f"Attack Success Rate    : {asr*100:.2f}% (Bypass Vulnerability)")
    print(f"Throughput             : {total_tests/total_time:.1f} prompts/sec")
    print("="*70)

if __name__ == "__main__":
    run_benchmark()
