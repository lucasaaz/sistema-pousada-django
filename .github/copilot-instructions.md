# Copilot Instructions for AI Agents

## Project Overview
- This is a Django-based hotel/pousada management system. Main app: `gestao`. Core files: `gestao/models.py`, `gestao/views.py`, `gestao/forms.py`, `gestao/admin.py`.
- Data is stored in a MySQL database (local dev uses XAMPP, see README for setup). Default DB config is in `pousada_project/settings.py` under `DATABASES`.
- Static assets: `static/` (css, img, js). Templates: `templates/` (base, dashboard, gestao subfolder for client forms/lists).

## Key Workflows
- **Setup**: Create/activate a Python virtualenv, install dependencies from `requirements.txt`.
- **DB Migration**: Run `python manage.py migrate` to sync models to DB.
- **Admin User**: Create with `python manage.py createsuperuser`.
- **Run Server**: `python manage.py runserver` (default: http://127.0.0.1:8000).
- **Admin Panel**: http://127.0.0.1:8000/admin (for initial data entry).

## Patterns & Conventions
- **App Structure**: All business logic is in the `gestao` app. Models, forms, views, and admin customizations are separated by file.
- **Templates**: Use Django template inheritance (`base.html`). App-specific templates are in `templates/gestao/`.
- **Static Files**: Reference via `{% static %}` in templates. Organize by type (css, img, js).
- **Migrations**: All schema changes go through Django migrations (`gestao/migrations/`).
- **Forms**: Use Django forms in `gestao/forms.py` for validation/UI.
- **Admin**: Register/manage models in `gestao/admin.py`.

## Integration Points
- **Database**: MySQL (local: XAMPP, prod: update `settings.py` for remote DB).
- **External Libraries**: See `requirements.txt` (must include `Django`, `mysqlclient`).
- **Deployment**: For production, set `DEBUG = False` and configure `ALLOWED_HOSTS` in `settings.py`. Use Gunicorn/uWSGI + Nginx/Apache for serving.

## Examples
- To add a new model: edit `gestao/models.py`, run `python manage.py makemigrations` and `python manage.py migrate`.
- To add a new view/template: update `gestao/views.py`, create template in `templates/gestao/`, add URL in `gestao/urls.py`.
- To customize admin: edit `gestao/admin.py`.

## References
- Main project config: `pousada_project/settings.py`
- App logic: `gestao/`
- Templates: `templates/`
- Static files: `static/`
- Migrations: `gestao/migrations/`

---
If any workflow, convention, or integration is unclear, ask the user for clarification or examples from their usage.
