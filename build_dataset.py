#!/usr/bin/env python3
"""
build_dataset.py
Downloads and combines massive datasets from Hugging Face.
- Safe Prompts: tatsu-lab/alpaca
- Injections: imoxto/prompt_injection_cleaned_dataset
Saves them locally as a Hugging Face dataset.
"""

import os
import json
import random
from datasets import load_dataset, Dataset, DatasetDict

def main():
    print("="*60)
    print("🚀 MASSIVE DATASET BUILDER (100k+ Rows)")
    print("="*60)

    # 1. Load Safe Prompts
    print("\n[1/3] Downloading Safe Prompts (tatsu-lab/alpaca)...")
    try:
        alpaca_ds = load_dataset('tatsu-lab/alpaca', split='train')
        safe_prompts = []
        # Alpaca has ~52k instructions. We'll take up to 50k
        for row in alpaca_ds:
            text = row['instruction']
            if row.get('input'):
                text += "\n" + row['input']
            safe_prompts.append({'text': text, 'label': 0})
        
        # Shuffle and sample 50k
        random.seed(42)
        random.shuffle(safe_prompts)
        safe_prompts = safe_prompts[:50000]
        print(f"✅ Loaded {len(safe_prompts)} Safe Prompts.")
    except Exception as e:
        print(f"❌ Error loading safe prompts: {e}")
        return

    # 2. Load Injections
    print("\n[2/3] Downloading Injection Prompts (imoxto/prompt_injection_cleaned_dataset)...")
    try:
        injection_ds = load_dataset('imoxto/prompt_injection_cleaned_dataset', split='train')
        injection_prompts = []
        for row in injection_ds:
            text = row.get('user_input')
            if text and isinstance(text, str) and len(text.strip()) > 5:
                injection_prompts.append({'text': text.strip(), 'label': 1})
        
        # Ensure uniqueness
        unique_injections = {p['text']: p for p in injection_prompts}.values()
        injection_prompts = list(unique_injections)
        
        # Shuffle and sample 50k
        random.seed(42)
        random.shuffle(injection_prompts)
        injection_prompts = injection_prompts[:50000]
        print(f"✅ Loaded {len(injection_prompts)} Injection Prompts.")
    except Exception as e:
        print(f"❌ Error loading injection prompts: {e}")
        return

    # 3. Combine and Save
    print("\n[3/3] Combining, Shuffling, and Saving to Disk...")
    combined = safe_prompts + injection_prompts
    random.shuffle(combined)
    
    # Split into 90% train, 10% test
    split_idx = int(len(combined) * 0.9)
    train_data = combined[:split_idx]
    test_data = combined[split_idx:]
    
    # Convert to Hugging Face Dataset format
    train_dataset = Dataset.from_list(train_data)
    test_dataset = Dataset.from_list(test_data)
    
    dataset_dict = DatasetDict({
        'train': train_dataset,
        'test': test_dataset
    })
    
    output_dir = os.path.join(os.path.dirname(__file__), "massive_dataset")
    dataset_dict.save_to_disk(output_dir)
    print(f"✅ Dataset successfully saved to '{output_dir}'")
    print(f"   Train size: {len(train_dataset)}")
    print(f"   Test size:  {len(test_dataset)}")
    print("="*60)

if __name__ == "__main__":
    main()
