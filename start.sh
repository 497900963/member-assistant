#!/bin/bash
# Start the member-assistant server detached.
# Env: MEMBER_ASSISTANT_LLM_API_KEY must be set for real LLM answers.
export PATH="/data/home/.local/bin:$PATH"
export PIP_BREAK_SYSTEM_PACKAGES=1
cd /data/home/ai-project/member-assistant
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 \
  > /data/home/ai-project/member-assistant/server.log 2>&1 &
echo "server pid $!"
