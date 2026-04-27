# System Requirements

## Deployment Profiles

| Profile | Purpose | GPU | CPU | RAM | Disk |
| --- | --- | --- | --- | --- | --- |
| API + proxy only | Contract-safe gateway with external model provider | Optional | 8 vCPU | 16 GB | 50 GB |
| Local vLLM serving | Self-hosted 7B model inference | 1x H100 80GB (or equivalent) | 16 vCPU | 64 GB | 250 GB |
| Training + serving | QLoRA fine-tuning and online evaluation | 4-8x H100 80GB | 64 vCPU | 256 GB | 1 TB |

## Software Baseline

- Ubuntu 22.04+ for Linux servers (macOS supported for development only)
- Python 3.11+
- Docker Engine 24+
- Docker Compose v2+
- NVIDIA Driver 535+ and NVIDIA Container Toolkit for GPU containers

## Network and Credentials

- Hugging Face access for model and dataset pull
- Optional external OpenAI-compatible provider key for hosted-inference mode
- Restricted network ingress to API and proxy ports
