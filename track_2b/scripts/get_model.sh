#!/bin/sh
# Download the Apertus v1.5 8B text-only GGUF once (build time). Nothing is downloaded at runtime.
set -e
mkdir -p models
F=models/apertus-v1.5-8b-text-q4_k_m.gguf
[ -f "$F" ] || curl -L -o "$F" https://huggingface.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF/resolve/main/apertus-v1.5-8b-text-q4_k_m.gguf
echo "a037df8d87ff6caacee794ee85f55342f2152e0d359b7389033300c3bee5f299  $F" | shasum -a 256 -c -
