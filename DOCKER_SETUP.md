# DOCKER_SETUP.md

## Run the app with Docker (no source build required)

### Prerequisites
1. Install **Docker Desktop** (https://www.docker.com/products/docker-desktop/).
2. Make sure Docker Desktop is running.

### Setup steps
1. Get the two files you need — **`docker-compose.prod.yml`** and **`.env`** — from the project owner.
2. Place both files in the same folder.
3. Open a terminal in that folder and run:
   ```bash
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up
   ```
4. Open your browser at **http://localhost:3000**

### Notes
- All friends connect to the same shared cloud database.
- Ports: 3000 (app), 8000 (API).
