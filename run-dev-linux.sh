#!/usr/bin/env bash

# --- Start backend ---
cd backend

# activate venv
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# run backend
uvicorn api:app --reload &
BACK_PID=$!

# --- Start frontend ---
cd ../frontend

# run Vite dev server
npm run dev

# when frontend exits, stop backend
kill $BACK_PID 2>/dev/null || true
