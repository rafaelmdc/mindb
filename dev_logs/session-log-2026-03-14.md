# Session Log

**Date:** 2026-03-14

## Objective
- Bootstrap the Django project.
- Implement the first-pass schema from `docs/schema.md`.
- Create migrations and register the core models in Django admin.
- Move the project to a Docker-based Django + PostgreSQL local setup.

## What happened
- Read `README.md`, `docs/schema.md`, `docs/roadmap.md`, `docs/graph.md`, and `AGENTS.md` before making architectural decisions.
- Created a minimal Django project structure with `config`, `core`, and `database`.
- Implemented first-pass models for `Study`, `Sample`, `Organism`, `RelativeAssociation`, `CoreMetadata`, `MetadataVariable`, `MetadataValue`, and `ImportBatch`.
- Added documented integrity rules, including conditional DOI uniqueness, `(study, label)` uniqueness, canonical organism pair ordering, self-pair prevention, and one typed metadata value per row.
- Registered all core models in Django admin with search, filters, list displays, and a `CoreMetadata` inline on `Sample`.
- Added a minimal `.env` loader in Django settings and created `.env` with Django and PostgreSQL variables.
- Confirmed the manual `.env` approach works, while noting it is valid but less standard than `django-environ` or `python-decouple`.
- Added container-first local infrastructure with a `Dockerfile`, `docker-compose.yml`, `.dockerignore`, and Python dependencies.
- Switched container database connectivity to the Docker `db` service and started the stack with Docker Compose.

## Files touched
- `README.md`
- `AGENTS.md`
- `docs/schema.md`
- `docs/roadmap.md`
- `docs/graph.md`
- `manage.py`
- `config/settings.py`
- `config/urls.py`
- `database/models.py`
- `database/admin.py`
- `database/migrations/0001_initial.py`
- `.env`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

## Validation
- Ran `python3 manage.py makemigrations`
- Ran `python3 manage.py migrate`
- Ran `python3 manage.py check`
- Ran `python3 manage.py makemigrations --check --dry-run`
- Ran `docker compose config`
- Ran `docker compose up -d --build`
- Ran `docker compose ps`
- Ran `docker compose logs web --tail=200`
- Result: Django migrations applied successfully inside the Docker web container against PostgreSQL database `innov_health`.

## Current status
- done

## Open issues
- The app container still uses Django `runserver`; this is fine for local development but not the production shape for Kubernetes.
- `.env` contains placeholder secrets and local development credentials.
- No browser views, home page, CSV import workflow, or graph feature have been built yet.

## Next step
- Replace `runserver` with `gunicorn` and add a production-appropriate web container entrypoint so the Docker setup aligns better with the eventual Kubernetes deployment path.
