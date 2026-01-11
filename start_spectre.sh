#!/bin/bash

# Spectre Launch Script
# Starts Backend (Uvicorn) and Gateway (Nginx)

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_PORT=8000
GATEWAY_PORT=8090

echo "🚀 Starting Spectre Platform..."

# 1. Start Backend
echo "Starting Backend on port $BACKEND_PORT..."
source "$ROOT_DIR/.venv/bin/activate"
uvicorn backend.api.main:app --port $BACKEND_PORT &
BACKEND_PID=$!
echo "Backend running (PID: $BACKEND_PID)"

# 2. Start Nginx
# Note: We use -g 'daemon off;' to keep it in foreground if we want, 
# but here we'll let it daemonize or just use the config.
# Ideally we run nginx as root, but for this dev setup we run as user on port 8080
if command -v nginx &> /dev/null; then
    echo "Starting Nginx Gateway on port $GATEWAY_PORT..."
    # Config path must be absolute or relative to pwd. We use absolute in the file but let's be safe
    # We create a temporary config with the correct root path interpolated if needed, 
    # but I hardcoded it for now.
    
    # Check if nginx can run effectively without sudo on 8080
    nginx -c "$ROOT_DIR/nginx/spectre.conf" -p "$ROOT_DIR/nginx/" &
    NGINX_PID=$!
    echo "Gateway running..."
else
    echo "❌ Nginx not found! Dashboard available at backend only."
fi

echo "✅ Spectre is LIVE at http://localhost:$GATEWAY_PORT"
echo "   Backend API at http://localhost:$BACKEND_PORT"

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
wait
