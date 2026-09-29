# Recipe Finder & Meal Planner

A full-stack Django web application for discovering recipes, saving favorites, planning a week of meals and turning that plan into a grouped shopping list.

## Features

- **Recipe discovery**: browse with pagination, sort by newest, rating, time, calories or name.
- **Search**: by recipe name, ingredient, cuisine, category or diet, e.g. "chicken pasta", "vegetarian dinner", "quick breakfast", "Italian recipes". Handled with Django ORM queries.
- **Filters**: category, cuisine, dietary preference, difficulty and total time. All filters combine.
- **Recipe detail**: image, times, servings scaler, ingredients, numbered steps, nutrition (with a fallback when data is missing), related recipes, SEO title/description/Open Graph tags and slug URLs like `/recipes/chicken-biryani/`.
- **Ratings & reviews**: one review per user per recipe (enforced in the database), edit or delete your own, average rating and review count.
- **Favorites**: save/remove recipes, plus a searchable, filterable *My Favorites* page.
- **Weekly meal planner**: breakfast/lunch/dinner/snack grid, week navigation, add/replace/remove meals, mark as cooked, responsive day-by-day view on mobile.
- **Generate meal plan**: rule-based (no external AI). Choose days, meals per day, diet, cuisine, max time, difficulty and daily calorie target; regenerate any single meal.
- **Shopping list**: generate from a week of planned meals (quantities merged and grouped by aisle), add custom items, edit, tick off, clear purchased, clear all, print.
- **Accounts**: register, login, logout, password reset, profile with avatar, dietary preferences, favorite cuisines and default servings.
- **Dashboard**: today's meals, quick actions and statistics cards.
- **Django admin**: full management of recipes (with ingredient and instruction inlines), categories, cuisines, diets, ingredients, reviews and more.
- **Custom 403/404/500 pages**, flash messages, accessible and responsive UI.

## Technologies

Python 3, Django 5, SQLite (PostgreSQL-ready), HTML5, CSS3, JavaScript, Bootstrap 5 and Bootstrap Icons (loaded from a CDN), Pillow.

## Installation

```bash
git clone <repository-url>
cd recipe-finder-meal-planner

python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Then:

```bash
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. `seed_data` adds 29 demo recipes, ingredients, instructions, sample nutrition and reviews. It also creates a development-only demo account (`demo` / `demo12345`) with a planned week and a few favorites; pass `--no-demo-user` to skip it, or `--reset` to wipe recipes first. The bundled nutrition values are rough sample data, not dietary advice.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key (required when `DEBUG=False`) | dev-only key |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins (production) | empty |
| `DB_ENGINE` | `sqlite` or `postgres` | `sqlite` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL settings | see `.env.example` |
| `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL` | Password-reset email | console backend |

### Switching to PostgreSQL

Install `psycopg[binary]`, set `DB_ENGINE=postgres` plus the `DB_*` variables, then run `python manage.py migrate` and `seed_data`.

## Media and static files

- Uploaded recipe images and avatars go to `media/` (`MEDIA_URL`/`MEDIA_ROOT`), served by Django only when `DEBUG=True`. Uploads are limited to JPG, PNG, WebP or GIF up to 5 MB and are verified by Pillow.
- Recipes without a photo show a generated SVG placeholder.
- Static source files live in `static/`; run `python manage.py collectstatic` to gather them into `staticfiles/` (`STATIC_ROOT`) for production, and serve `media/` and `staticfiles/` from your web server or a service such as WhiteNoise.

## Tests

```bash
python manage.py test
```

58 tests cover authentication, recipe listing/detail/search/filtering, favorites, reviews (including duplicate prevention and authorization), the meal planner and plan generator, and the shopping list.

## Project structure

```
config/     settings, root URLs, shared form helpers
recipes/    recipes, categories, cuisines, diets, ingredients, favorites, reviews, search, seed_data command
planner/    MealPlan model, weekly planner, plan generation service
shopping/   ShoppingListItem model and views
accounts/   registration, login, password reset, profile, dashboard
templates/  base layout, home, about, error pages
static/     CSS and JavaScript
```

## Security notes

CSRF protection on all forms and state-changing actions (POST only), Django's password hashing and validators, ownership checks on favorites, reviews, meal plans and shopping items, `login_required` on private pages, template auto-escaping, ORM-only database access, validated image uploads, open-redirect protection on `next`, and HTTPS/HSTS/secure-cookie settings when `DEBUG=False`.
