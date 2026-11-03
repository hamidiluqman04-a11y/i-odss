# I-ODSS production image: builds the React app, then runs Django (which serves
# both the website and /api). Used by Render (render.yaml) and works on any Docker host.

# ── Stage 1: build the React frontend ─────────────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Collect the Django admin's CSS/JS. Settings need these variables to load;
# throwaway values are fine because collectstatic never touches the database.
RUN DJANGO_SECRET_KEY=build-only DB_NAME=x DB_USER=x DB_PASSWORD=x \
    python manage.py collectstatic --noinput

# Run as a normal user, not root.
RUN useradd --create-home iodss && chown -R iodss /app
USER iodss

# On every start: update the database tables, (re)create the demo account if
# DEMO_USER_* are set, then serve with gunicorn on the port the host gives us.
CMD ["sh", "-c", "python manage.py migrate --noinput && (python manage.py create_demo_user || echo 'Demo account skipped: DEMO_USER_EMAIL / DEMO_USER_PASSWORD not set.') && exec gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 120 --access-logfile -"]
