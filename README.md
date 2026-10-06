# MCQ Knowledge Tracing App - Phase 1

This repository contains Phase 1 of the MCQ Knowledge Tracing App. It features a FastAPI backend with PostgreSQL (Supabase) and a React frontend with Tailwind CSS.

## Getting Started

### Running Locally with Docker (Recommended)

You can run the MCQ Knowledge Tracing App with Docker (no toolchain required) or build it from source.

#### Prerequisites
[Docker Desktop](https://www.docker.com/products/docker-desktop/) must be open and running on your machine.

#### Option 1: Build the Docker Image Yourself
Build and run the full stack using Docker Compose:
```bash
docker compose up --build
```
Navigate to `http://localhost:3000` in your browser to view the frontend. The backend API is available at `http://localhost:8000`.

#### Option 2: Use the pre-built Docker Images
If you prefer to skip the build process and run without cloning the repository, you can use the pre-built images.

**1. Run the Backend API**
Since the backend requires a database, you must provide your Supabase connection string:
```bash
docker run -d -p 8000:8000 -e DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST.supabase.co:5432/postgres" -e SECRET_KEY="your_secret_key" danish1922/knowledgetrace-backend:latest
```

**2. Run the Frontend UI**
Now start the frontend:
```bash
docker run -d -p 3000:80 danish/knowledgetrace-frontend:latest
```
Just like before, navigate to `http://localhost:3000` in your browser.

---

### Running from Source

#### 1. Backend Setup

The backend uses FastAPI and SQLAlchemy with PostgreSQL (asyncpg). It handles JWT authentication, test creation, taking tests, and viewing results.

Open a terminal in the project root:

```bash
cd backend

# Activate the virtual environment (if not already activated)
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# Install dependencies if you haven't already
pip install -r requirements.txt # (or ensure asyncpg, passlib, python-jose, python-multipart are installed)

# Run the FastAPI server
uvicorn app.main:app --reload
```
The backend will run on `http://127.0.0.1:8000`. The database schemas are created automatically on startup.

### 2. Frontend Setup

The frontend uses React (Vite) and Tailwind CSS for a fast, modern UI.

Open a NEW terminal in the project root:

```bash
cd frontend

# Install dependencies if you haven't already
npm install

# Run the Vite development server
npm run dev
```
The frontend will usually run on `http://localhost:5173`. 

## How to Test

1. Open the frontend in your browser.
2. **Register a Teacher**: Click "Register here" and create an account with the role `Teacher`.
3. **Register a Student**: Create another account with the role `Student`.
4. **Login as Teacher**: Use the teacher credentials to log in.
5. **Create a Test**: On the teacher dashboard, click "Create New Test", add concepts and questions, and save.
6. **Assign (API level)**: Currently, assigning is scaffolded in the API. For Phase 1 manual testing, you can use the Swagger UI (`http://localhost:8000/docs`) to assign the test to the student by hitting `/teacher/assign-test`.
7. **Login as Student**: Log out of the teacher account and log in as the student. You will see the assigned test.
8. **Take the Test**: Click "Start Test", answer questions (which logs response times and choices).
9. **View Results**: Log back in as the Teacher and click "Results" on the test card to view the aggregate statistics.
