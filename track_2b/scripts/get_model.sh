#!/bin/sh
# Download the Apertus v1.5 8B text-only GGUF once (build time). Nothing is downloaded at runtime.
set -e
mkdir -p models
F=models/apertus-v1.5-8b-text-q4_k_m.gguf
[ -f "$F" ] || curl -L -o "$F" https://huggingface.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF/resolve/main/apertus-v1.5-8b-text-q4_k_m.gguf
