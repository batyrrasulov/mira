PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python)

.PHONY: install run test compile quality train-structured score-structured pull-model prepare-data train-lora merge-lora adapter-gate pipeline start-stack stop-stack rollout rollback train score all

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run:
	bash scripts/run_local_api.sh

test:
	pytest -q

compile:
	$(PYTHON) -m py_compile src/mira/*.py
	$(PYTHON) -m py_compile training/scripts/*.py
	$(PYTHON) -m py_compile evaluation/*.py
	$(PYTHON) -m py_compile scripts/*.py

quality:
	$(PYTHON) evaluation/run_quality_suite.py \
		--base-url http://127.0.0.1:8080 \
		--prompts-file evaluation/prompts/sample_prompts.jsonl \
		--output-json evaluation/results/quality_suite_report.json

train-structured:
	$(PYTHON) training/scripts/build_dataset.py \
		--input-csv training/data/sample_outcomes.csv \
		--output-jsonl training/outputs/sft_bootstrap.jsonl \
		--report-json training/outputs/sft_build_report.json
	$(PYTHON) training/scripts/train_structured_model.py \
		--input-csv training/data/sample_outcomes.csv \
		--output-model training/outputs/structured_model.joblib \
		--output-scored-csv training/outputs/structured_holdout_scored.csv \
		--output-report training/outputs/structured_training_report.json

score-structured:
	$(PYTHON) training/scripts/score_outcomes.py \
		--input-csv training/outputs/structured_holdout_scored.csv \
		--score-col ModelScore \
		--output-json training/outputs/outcome_metrics.json

train: train-structured

score: score-structured

pull-model:
	$(PYTHON) scripts/pull_hf_model.py \
		--repo-id Qwen/Qwen2.5-7B-Instruct \
		--local-dir models/base/qwen2.5-7b-instruct

prepare-data:
	$(PYTHON) training/scripts/prepare_hf_dataset.py \
		--dataset-id TIGER-Lab/MathInstruct \
		--split train \
		--max-samples 20000 \
		--train-output training/data/edu_train.jsonl \
		--eval-output training/data/edu_eval.jsonl

train-lora:
	$(PYTHON) training/scripts/train_lora_adapter.py \
		--config-yaml training/configs/qlora_h100.yaml

merge-lora:
	$(PYTHON) training/scripts/merge_lora_adapter.py \
		--base-model-id Qwen/Qwen2.5-7B-Instruct \
		--adapter-path training/outputs/qwen25_edu_qlora_adapter \
		--output-dir models/merged/qwen25_edu_merged

adapter-gate:
	$(PYTHON) evaluation/run_adapter_gate.py \
		--base-url http://127.0.0.1:8003 \
		--base-model qwen2.5-7b-instruct \
		--canary-model qwen2.5-7b-instruct-edu-lora \
		--prompts-file evaluation/prompts/sample_prompts.jsonl \
		--output-json evaluation/results/adapter_gate_report.json

pipeline:
	bash training/scripts/run_full_pipeline.sh

start-stack:
	bash scripts/start_backend_stack.sh

stop-stack:
	bash scripts/stop_backend_stack.sh

rollout:
	bash scripts/rollout_canary.sh --percent 25

rollback:
	bash scripts/rollback_canary.sh

all: compile test
