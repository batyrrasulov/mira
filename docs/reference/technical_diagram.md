# Technical Diagram

```mermaid
flowchart LR
    A[Hugging Face Model Hub\nOpen Source Base Model] --> B[scripts/pull_hf_model.py\nModel Snapshot]
    D[Hugging Face Dataset\nMath/Instruction Data] --> E[training/scripts/prepare_hf_dataset.py]
    E --> F[training/scripts/train_lora_adapter.py\nQLoRA on H100 Cluster]
    B --> F
    F --> G[training/scripts/merge_lora_adapter.py\nMerged Weights]
    G --> H[models/merged/*]

    H --> I[vLLM Main Server\nPort 8000]
    I --> J[llm_canary_proxy.py\nPort 8003]
    J --> K[Mira API\nOpenAI-compatible\nPort 8080]
    K --> L[LMS / Client Applications]

    M[evaluation/run_adapter_gate.py] --> J
    M --> N[Promotion Decision]
    N --> O[scripts/rollout_canary.sh]
    N --> P[scripts/rollback_canary.sh]
```

## Notes

- vLLM is the model execution plane.
- The canary proxy controls base-versus-adapter routing percentages.
- Mira API enforces schema and guardrails while preserving OpenAI endpoint compatibility.
- Promotion gate scores quality and latency before rollout.
