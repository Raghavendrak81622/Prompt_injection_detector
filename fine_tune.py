#!/usr/bin/env python3
"""
Fine-tuning script for DeBERTa-v3 using the Hugging Face Trainer API.
Optimized for an RTX 4050 (6GB VRAM).
"""

import json
import torch
import os
import sys

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer
)

def main():
    print("=" * 60)
    print("🧠 ML Model Fine-Tuning Sequence")
    print("=" * 60)

    model_name = "ProtectAI/deberta-v3-base-prompt-injection-v2"
    
    print(f"Loading base model ({model_name})...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # Load the model and its pre-existing classification head
    model = AutoModelForSequenceClassification.from_pretrained(model_name)

    # Use absolute paths based on the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mistakes_path = os.path.join(script_dir, "mistakes.json")
    output_dir = os.path.join(script_dir, "fine_tuned_deberta")

    print("Loading mistakes dataset...")
    try:
        with open(mistakes_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: mistakes.json not found!")
        sys.exit(1)

    # The ProtectAI model expects label 0 for SAFE and label 1 for INJECTION
    # We map our dataset to these labels
    dataset = Dataset.from_list(data)

    print("Tokenizing data...")
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # ─── GPU Optimization for RTX 4050 6GB ───
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,              # Number of passes over the dataset
        per_device_train_batch_size=2,   # Very small batch size to fit in 6GB VRAM
        gradient_accumulation_steps=4,   # Accumulate gradients to simulate a batch size of 8
        fp16=True,                       # Use mixed precision (crucial for RTX GPUs, cuts memory in half!)
        learning_rate=2e-5,              # Small learning rate to tweak (not destroy) existing knowledge
        logging_steps=1,
        save_strategy="no",              # Don't save intermediate checkpoints for this quick run
        report_to="none"                 # Disable wandb/tensorboard logging
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    print("\n🚀 Starting Fine-Tuning on GPU...")
    trainer.train()

    print(f"\n💾 Saving fine-tuned model to '{output_dir}'...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print("=" * 60)
    print("✅ Training Complete!")
    print(f"To use the new model, update 'pipeline.py' to point to '{output_dir}'.")

if __name__ == "__main__":
    main()
