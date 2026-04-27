PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python)

.PHONY: install run test compile quality train score all

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

quality:
	$(PYTHON) evaluation/run_quality_suite.py \
		--base-url http://127.0.0.1:8080 \
		--prompts-file evaluation/prompts/sample_prompts.jsonl \
		--output-json evaluation/results/quality_suite_report.json

train:
	$(PYTHON) training/scripts/build_dataset.py \
		--input-csv training/data/sample_outcomes.csv \
		--output-jsonl training/outputs/sft_bootstrap.jsonl \
		--report-json training/outputs/sft_build_report.json
	$(PYTHON) training/scripts/train_structured_model.py \
		--input-csv training/data/sample_outcomes.csv \
		--output-model training/outputs/structured_model.joblib \
		--output-scored-csv training/outputs/structured_holdout_scored.csv \
		--output-report training/outputs/structured_training_report.json

score:
	$(PYTHON) training/scripts/score_outcomes.py \
		--input-csv training/outputs/structured_holdout_scored.csv \
		--score-col ModelScore \
		--output-json training/outputs/outcome_metrics.json

all: compile test
