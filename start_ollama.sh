#!/bin/bash
# Start Ollama with CORS enabled for all origins
export OLLAMA_ORIGINS="*"
export OLLAMA_HOST="0.0.0.0"

# Kill existing ollama if running
pkill -f "ollama serve" 2>/dev/null

# Start ollama
/snap/bin/ollama serve
