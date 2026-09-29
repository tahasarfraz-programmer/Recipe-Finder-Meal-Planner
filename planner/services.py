"""Rule-based meal plan generation (no external APIs)."""
import datetime
import random

from django.db.models import F

from recipes.models import Recipe

from .models import MealPlan

MEALS_BY_COUNT = {
    1: ["dinner"],
    2: ["lunch", "dinner"],
    3: ["breakfast", "lunch", "dinner"],
    4: ["breakfast", "lunch", "dinner", "snack"],
}
CATEGORY_HINTS = {
    "breakfast": {"breakfast"},
    "lunch": {"lunch", "salad", "soup"},
    "dinner": {"dinner"},
    "snack": {"snack", "appetizer"},
}


def candidate_recipes(prefs):
    qs = Recipe.objects.select_related("category").annotate(_minutes=F("prep_time") + F("cook_time"))
    if prefs.get("diet"):
        qs = qs.filter(diets__slug=prefs["diet"])
    if prefs.get("cuisine"):
        qs = qs.filter(cuisine__slug=prefs["cuisine"])
    if prefs.get("max_time"):
        qs = qs.filter(_minutes__lte=prefs["max_time"])
    if prefs.get("difficulty"):
        qs = qs.filter(difficulty=prefs["difficulty"])
    return list(qs.distinct())


def per_meal_calories(prefs):
    if prefs.get("calories") and prefs.get("meals_per_day"):
        return prefs["calories"] / prefs["meals_per_day"]
    return None


def pick_recipe(candidates, meal_type, used_ids=(), per_meal=None, exclude_id=None):
    pool = [r for r in candidates if r.category.slug in CATEGORY_HINTS[meal_type] and r.pk != exclude_id]
    if not pool:  # fall back to anything matching the other preferences
        pool = [r for r in candidates if r.pk != exclude_id]
    pool = [r for r in pool if r.pk not in used_ids] or pool
    if not pool:
        return None
    if per_meal:
        pool = sorted(pool, key=lambda r: abs((r.calories if r.calories is not None else 10**6) - per_meal))[:5]
    return random.choice(pool)


def generate_plan(user, prefs, start_date, days, replace_existing=False):
    """Fill the planner. Returns (created_count, skipped_count)."""
    candidates = candidate_recipes(prefs)
    if not candidates:
        return 0, 0
    meal_types = MEALS_BY_COUNT[prefs.get("meals_per_day", 3)]
    per_meal = per_meal_calories(prefs)
    existing = {(p.date, p.meal_type) for p in MealPlan.objects.filter(
        user=user, date__range=(start_date, start_date + datetime.timedelta(days=days - 1)))}
    used, created, skipped = set(), 0, 0
    for offset in range(days):
        day = start_date + datetime.timedelta(days=offset)
        for meal_type in meal_types:
            if (day, meal_type) in existing and not replace_existing:
                skipped += 1
                continue
            recipe = pick_recipe(candidates, meal_type, used, per_meal)
            used.add(recipe.pk)
            MealPlan.objects.update_or_create(
                user=user, date=day, meal_type=meal_type, defaults={"recipe": recipe, "is_cooked": False})
            created += 1
    return created, skipped
