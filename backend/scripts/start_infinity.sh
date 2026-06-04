#!/bin/bash
infinity_emb v2 \
  --model-id BAAI/bge-m3 \
  --model-id BAAI/bge-reranker-v2-m3 \
  --port 7997 \
  --no-bettertransformer \
  --batch-size 32 \
  --device cuda
