#!/usr/bin/env sh
set -eu

cd /app
mkdir -p runtime

if [ ! -f config.yaml ]; then
  cp config.docker.example.yaml config.yaml
fi

exec uv run rsi-bot web --config config.yaml
