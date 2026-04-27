#!/usr/bin/env python3
"""Train a LoRA/QLoRA adapter for Mira educational prompts."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from datasets import Dataset, load_dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoRA/QLoRA adapter")
    parser.add_argument("--config-yaml", default="training/configs/qlora_h100.yaml")
    return parser.parse_args()


def load_config(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    if not isinstance(cfg, dict):
        raise SystemExit(f"Invalid config file: {path}")
    return cfg


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def render_messages(tokenizer: AutoTokenizer, messages: list[dict[str, Any]]) -> str:
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)

    segments: list[str] = []
    for item in messages:
        role = str(item.get("role", "user")).strip().lower()
        content = str(item.get("content", "")).strip()
        if content:
            segments.append(f"{role}: {content}")
    return "\n".join(segments)


def to_text_dataset(raw_ds: Dataset, tokenizer: AutoTokenizer) -> Dataset:
    def _map_row(row: dict[str, Any]) -> dict[str, Any]:
        messages = row.get("messages")
        if not isinstance(messages, list):
            return {"text": ""}
        text = render_messages(tokenizer, messages)
        return {"text": text}

    text_ds = raw_ds.map(_map_row, remove_columns=raw_ds.column_names)
    text_ds = text_ds.filter(lambda row: bool(row.get("text")))
    return text_ds


def tokenize_dataset(text_ds: Dataset, tokenizer: AutoTokenizer, max_seq_length: int) -> Dataset:
    def _tokenize(batch: dict[str, list[str]]) -> dict[str, Any]:
        tokens = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_seq_length,
            padding="max_length",
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    return text_ds.map(_tokenize, batched=True, remove_columns=["text"])


def load_dtype(name: str) -> torch.dtype:
    norm = name.strip().lower()
    mapping = {
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
        "float16": torch.float16,
        "fp16": torch.float16,
        "float32": torch.float32,
        "fp32": torch.float32,
    }
    if norm not in mapping:
        raise SystemExit(f"Unsupported dtype: {name}")
    return mapping[norm]


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config_yaml)

    model_cfg = cfg["model"]
    data_cfg = cfg["data"]
    trainer_cfg = cfg["trainer"]
    lora_cfg = cfg["lora"]
    quant_cfg = cfg["quantization"]

    set_seed(int(trainer_cfg.get("seed", 42)))

    base_model_id = str(model_cfg["base_model_id"])
    tokenizer_id = str(model_cfg.get("tokenizer_id", base_model_id))
    trust_remote_code = bool(model_cfg.get("trust_remote_code", False))

    quant_dtype = load_dtype(str(quant_cfg.get("bnb_4bit_compute_dtype", "bfloat16")))
    bnb_config = None
    if bool(quant_cfg.get("load_in_4bit", True)):
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=str(quant_cfg.get("bnb_4bit_quant_type", "nf4")),
            bnb_4bit_compute_dtype=quant_dtype,
            bnb_4bit_use_double_quant=bool(quant_cfg.get("bnb_4bit_use_double_quant", True)),
        )

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id, trust_remote_code=trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        trust_remote_code=trust_remote_code,
        torch_dtype=torch.bfloat16,
        quantization_config=bnb_config,
        device_map="auto",
    )

    if bnb_config is not None:
        model = prepare_model_for_kbit_training(model)

    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(lora_cfg.get("r", 64)),
        lora_alpha=int(lora_cfg.get("alpha", 128)),
        lora_dropout=float(lora_cfg.get("dropout", 0.05)),
        bias=str(lora_cfg.get("bias", "none")),
        target_modules=list(lora_cfg.get("target_modules", [])),
    )
    model = get_peft_model(model, lora)

    train_file = str(data_cfg["train_file"])
    eval_file = str(data_cfg["eval_file"])

    raw_train = load_dataset("json", data_files=train_file, split="train")
    raw_eval = load_dataset("json", data_files=eval_file, split="train")

    text_train = to_text_dataset(raw_train, tokenizer)
    text_eval = to_text_dataset(raw_eval, tokenizer)

    max_seq_length = int(trainer_cfg.get("max_seq_length", 4096))
    train_ds = tokenize_dataset(text_train, tokenizer, max_seq_length)
    eval_ds = tokenize_dataset(text_eval, tokenizer, max_seq_length)

    output_dir = str(trainer_cfg["output_dir"])
    report_file = str(trainer_cfg.get("report_file", Path(output_dir) / "training_report.json"))

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=float(trainer_cfg.get("epochs", 2)),
        learning_rate=float(trainer_cfg.get("learning_rate", 1.2e-4)),
        weight_decay=float(trainer_cfg.get("weight_decay", 0.01)),
        warmup_ratio=float(trainer_cfg.get("warmup_ratio", 0.03)),
        lr_scheduler_type=str(trainer_cfg.get("lr_scheduler_type", "cosine")),
        per_device_train_batch_size=int(trainer_cfg.get("per_device_train_batch_size", 2)),
        per_device_eval_batch_size=int(trainer_cfg.get("per_device_eval_batch_size", 2)),
        gradient_accumulation_steps=int(trainer_cfg.get("gradient_accumulation_steps", 16)),
        gradient_checkpointing=bool(trainer_cfg.get("gradient_checkpointing", True)),
        max_grad_norm=float(trainer_cfg.get("max_grad_norm", 0.3)),
        bf16=bool(trainer_cfg.get("bf16", True)),
        logging_steps=int(trainer_cfg.get("logging_steps", 10)),
        save_steps=int(trainer_cfg.get("save_steps", 100)),
        eval_steps=int(trainer_cfg.get("eval_steps", 100)),
        evaluation_strategy="steps",
        save_strategy="steps",
        report_to=[],
        remove_unused_columns=False,
    )

    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        tokenizer=tokenizer,
    )

    train_result = trainer.train()
    eval_result = trainer.evaluate()

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    metrics = {
        "train_metrics": {k: float(v) for k, v in train_result.metrics.items() if isinstance(v, (int, float))},
        "eval_metrics": {k: float(v) for k, v in eval_result.items() if isinstance(v, (int, float))},
        "base_model_id": base_model_id,
        "train_rows": len(train_ds),
        "eval_rows": len(eval_ds),
        "output_dir": output_dir,
    }

    report_path = Path(report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
