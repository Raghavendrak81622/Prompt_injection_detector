#!/usr/bin/env python3
"""
train_massive.py
Highly optimized fine-tuning script for training a DeBERTa model 
on 100,000 examples using an RTX 4050 6GB VRAM constraint.
"""

import os
import torch
import numpy as np
from datasets import load_from_disk
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    preds = np.argmax(predictions, axis=1)
    
    accuracy = (preds == labels).mean()
    
    tp = ((preds == 1) & (labels == 1)).sum()
    tn = ((preds == 0) & (labels == 0)).sum()
    fp = ((preds == 1) & (labels == 0)).sum()
    fn = ((preds == 0) & (labels == 1)).sum()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def main():
    print("="*60)
    print("🧠 MASSIVE TRAINING PIPELINE")
    print("   Optimized for RTX 4050 (6GB VRAM) & i5 CPU")
    print("="*60)

    model_id = "ProtectAI/deberta-v3-base-prompt-injection-v2"
    dataset_dir = os.path.join(os.path.dirname(__file__), "massive_dataset")
    output_dir = os.path.join(os.path.dirname(__file__), "v3_massive_model")

    print(f"Loading tokenizer & model: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    # Model is initialized with 2 labels (0: Safe, 1: Injection)
    model = AutoModelForSequenceClassification.from_pretrained(model_id, num_labels=2, ignore_mismatched_sizes=True)
    
    # Gradient checkpointing saves massive VRAM by trading compute time
    model.gradient_checkpointing_enable()

    print(f"Loading dataset from: {dataset_dir}")
    dataset = load_from_disk(dataset_dir)
    print(dataset)

    def tokenize_fn(examples):
        # Truncate to 512 tokens to save memory
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=512)

    print("Tokenizing dataset...")
    # Use multiple CPU cores for tokenization
    tokenized_dataset = dataset.map(tokenize_fn, batched=True, num_proc=4, remove_columns=["text"])

    print("Setting up optimized Trainer...")
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=1,                     # 1 epoch is enough for 100k
        per_device_train_batch_size=4,          # Small physical batch size for 6GB VRAM
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=8,          # Effective batch size = 4 * 8 = 32
        learning_rate=2e-5,
        fp16=True,                              # Mixed precision halves VRAM usage!
        dataloader_num_workers=4,               # Keep GPU fed with i5 CPU threads
        dataloader_pin_memory=True,             # Faster host-to-device transfers
        eval_strategy="steps",
        eval_steps=500,                         # Eval every 500 steps
        save_strategy="steps",
        save_steps=500,
        logging_steps=50,
        optim="adamw_torch",
        report_to="none",                       # Disable wandb to keep it simple
        load_best_model_at_end=True,
        metric_for_best_model="f1"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"],
        compute_metrics=compute_metrics,
    )

    print("🚀 STARTING TRAINING LOOP...")
    trainer.train()

    print("✅ Training complete! Saving final state-of-the-art model...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"🎉 Model saved to: {output_dir}")
    print("="*60)

if __name__ == "__main__":
    main()
