#!/usr/bin/env bash

# --- Start backend ---
cd backend

# activate venv if you use one
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# run your backend (edit this line to your actual command)
# Example if you're using uvicorn:
uvicorn api:app --reload &
BACK_PID=$!

# --- Start frontend ---
cd ../frontend

# run Vite dev server
npm run dev

# when frontend exits, stop backend
kill $BACK_PID 2>/dev/null || true
