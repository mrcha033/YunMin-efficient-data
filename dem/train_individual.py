"""LoRA fine-tuning utilities using HuggingFace Transformers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import logging
import yaml
import pandas as pd
import json
import torch
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load YAML configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def train_individual_domain(
    data_path: str,
    domain: str,
    config_path: str = "configs/dem_config.yaml",
    output_dir: Optional[str] = None,
    log_dir: str = "logs",
    summary_dir: str = "summary",
) -> str:
    """Fine-tune the base model for ``domain`` using LoRA."""

    cfg = load_config(config_path)
    base_name = cfg["base_model"].get("name") or cfg["base_model"].get("path")
    training_cfg = cfg.get("training", {})
    lora_cfg = cfg.get("lora", {})

    output_dir = output_dir or f"models/lora_{domain}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    Path(summary_dir).mkdir(parents=True, exist_ok=True)

    log_file = Path(log_dir) / f"train_{domain}.log"
    logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(log_file), logging.StreamHandler()])

    tokenizer = AutoTokenizer.from_pretrained(base_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(base_name)

    lora_config = LoraConfig(
        r=lora_cfg.get("r", 8),
        lora_alpha=lora_cfg.get("alpha", 32),
        lora_dropout=lora_cfg.get("dropout", 0.1),
        target_modules=lora_cfg.get("target_modules", []),
    )
    model = get_peft_model(model, lora_config)

    texts = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                texts.append(json.loads(line)["text"])
            except Exception:
                continue

    enc = tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=min(32, tokenizer.model_max_length),
        return_tensors="pt",
    )
    dataset = TensorDataset(enc.input_ids, enc.attention_mask, enc.input_ids.clone())
    dataloader = DataLoader(dataset, batch_size=training_cfg.get("batch_size", 1))
    optimizer = torch.optim.AdamW(model.parameters(), lr=training_cfg.get("learning_rate", 5e-5))
    losses = []

    model.train()
    for epoch in range(training_cfg.get("max_epochs", 1)):
        for batch in dataloader:
            optimizer.zero_grad()
            outputs = model(input_ids=batch[0], attention_mask=batch[1], labels=batch[2])
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
            logger.info("loss=%f", loss.item())

    model.save_pretrained(output_dir)
    adapter_bin = Path(output_dir) / "adapter_model.bin"

    pd.DataFrame({"loss": losses}).to_csv(Path(summary_dir) / f"train_{domain}.csv", index=False)

    logger.info("Training finished")
    return str(adapter_bin)


if __name__ == "__main__":  # pragma: no cover - manual usage
    import argparse

    parser = argparse.ArgumentParser(description="Train LoRA adapter for a domain")
    parser.add_argument("--config", default="configs/dem_config.yaml")
    parser.add_argument("--data", required=True, help="Path to JSONL dataset")
    parser.add_argument("--domain", required=True, help="Domain name")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    train_individual_domain(args.data, args.domain, args.config, args.output_dir)

