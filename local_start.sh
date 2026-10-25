#!/bin/bash

echo "Iniciando backend..."

cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACK_PID=$!
cd ..

echo "Iniciando frontend..."

cd frontend
npm install
npm run dev &
FRONT_PID=$!

wait $BACK_PID $FRONT_PID