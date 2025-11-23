⚙️ Requirements
Backend:

-Python 3.10+
-pip

Frontend:

-Node.js 18+
-npm or yarn

🚀 Setup — Linux (Ubuntu / Debian / Arch / Fedora)
1️⃣ Backend Setup

Open a terminal inside the backend/ folder:

cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic

Run Backend
uvicorn api:app --reload --port 8000


The backend now runs on:
http://localhost:8000

2️⃣ Frontend Setup

Open a terminal inside the frontend/ folder:

cd frontend
npm install
npm run dev


Frontend runs on:
http://localhost:5173

🚀 Setup — Windows 10 / 11
1️⃣ Backend Setup

Open PowerShell inside backend/:

cd backend
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn pydantic

Run Backend
uvicorn api:app --reload --port 8000

Backend will run on:
http://localhost:8000

2️⃣ Frontend Setup

Open PowerShell in the frontend/ folder:
cd frontend
npm install
npm run dev


Frontend runs on:
http://localhost:5173

TLDR
HOW TO RUN (LINUX)
Backend:
cd backend
venv/bin/activate
uvicorn api:app --reload --port 8000

Frontend:
cd frontend
npm run dev

HOW TO RUN (WIN)
