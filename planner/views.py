import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from recipes.models import Recipe

from . import services
from .forms import GenerateMealPlanForm, MealPlanForm
from .models import MealPlan


def monday_of(day):
    return day - datetime.timedelta(days=day.weekday())


def week_url(day):
    return f"{reverse('planner:week')}?week={monday_of(day).isoformat()}"


def _parse_date(value, default):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


@login_required
def week_view(request):
    today = datetime.date.today()
    start = monday_of(_parse_date(request.GET.get("week"), today))
    days = [start + datetime.timedelta(days=i) for i in range(7)]
    plans = MealPlan.objects.filter(user=request.user, date__range=(days[0], days[-1])).select_related("recipe", "recipe__category")
    by_slot = {(p.date, p.meal_type): p for p in plans}

    rows = [
        {"meal_type": value, "label": label, "cells": [{"date": d, "plan": by_slot.get((d, value))} for d in days]}
        for value, label in MealPlan.MealType.choices
    ]
    agenda = [
        {
            "date": d,
            "is_today": d == today,
            "slots": [{"meal_type": v, "label": l, "plan": by_slot.get((d, v))} for v, l in MealPlan.MealType.choices],
        }
        for d in days
    ]
    return render(request, "planner/week.html", {
        "days": days, "rows": rows, "agenda": agenda, "today": today,
        "week_start": days[0], "week_end": days[-1],
        "prev_week": (start - datetime.timedelta(days=7)).isoformat(),
        "next_week": (start + datetime.timedelta(days=7)).isoformat(),
        "this_week": monday_of(today).isoformat(),
        "planned_count": len(by_slot),
    })


@login_required
def add_meal(request):
    """Add a recipe to a slot; adding to an occupied slot replaces the meal."""
    initial = {"date": _parse_date(request.GET.get("date"), datetime.date.today()), "meal_type": request.GET.get("meal_type", "dinner")}
    if request.GET.get("recipe"):
        recipe = Recipe.objects.filter(slug=request.GET["recipe"]).first()
        if recipe:
            initial["recipe"] = recipe.pk
    form = MealPlanForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        _, created = MealPlan.objects.update_or_create(
            user=request.user, date=data["date"], meal_type=data["meal_type"],
            defaults={"recipe": data["recipe"], "is_cooked": False},
        )
        messages.success(request, "Meal added to your planner." if created else "Planned meal replaced.")
        return redirect(week_url(data["date"]))
    existing = None
    if request.method == "GET":
        existing = MealPlan.objects.filter(
            user=request.user, date=initial["date"], meal_type=initial["meal_type"]).select_related("recipe").first()
    return render(request, "planner/add_meal.html", {"form": form, "existing": existing})


@login_required
@require_POST
def remove_meal(request, pk):
    plan = get_object_or_404(MealPlan, pk=pk, user=request.user)
    plan.delete()
    messages.info(request, "Meal removed from your planner.")
    return redirect(week_url(plan.date))


@login_required
@require_POST
def toggle_cooked(request, pk):
    plan = get_object_or_404(MealPlan, pk=pk, user=request.user)
    plan.is_cooked = not plan.is_cooked
    plan.save(update_fields=["is_cooked"])
    messages.success(request, "Marked as cooked." if plan.is_cooked else "Marked as not cooked.")
    return redirect(week_url(plan.date))


@login_required
def generate(request):
    form = GenerateMealPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        prefs = {
            "diet": data["dietary_preference"].slug if data["dietary_preference"] else None,
            "cuisine": data["cuisine"].slug if data["cuisine"] else None,
            "max_time": data["max_cooking_time"],
            "difficulty": data["difficulty"] or None,
            "calories": data["calories_target"],
            "meals_per_day": data["meals_per_day"],
        }
        created, skipped = services.generate_plan(
            request.user, prefs, data["start_date"], data["days"], data["replace_existing"])
        if not created and not skipped:
            messages.error(request, "No recipes match those preferences. Try relaxing a filter.")
        else:
            request.session["planner_prefs"] = prefs
            msg = f"Generated {created} meal{'s' if created != 1 else ''}."
            if skipped:
                msg += f" {skipped} occupied slot{'s were' if skipped != 1 else ' was'} kept."
            messages.success(request, msg)
            return redirect(week_url(data["start_date"]))
    return render(request, "planner/generate.html", {"form": form})


@login_required
@require_POST
def regenerate_meal(request, pk):
    plan = get_object_or_404(MealPlan.objects.select_related("recipe"), pk=pk, user=request.user)
    prefs = request.session.get("planner_prefs", {})
    candidates = services.candidate_recipes(prefs)
    new = services.pick_recipe(
        candidates, plan.meal_type, per_meal=services.per_meal_calories(prefs), exclude_id=plan.recipe_id)
    if new is None:
        messages.info(request, "No other recipe matches your preferences for this slot.")
    else:
        plan.recipe, plan.is_cooked = new, False
        plan.save(update_fields=["recipe", "is_cooked"])
        messages.success(request, f"Swapped in {new.title}.")
    return redirect(week_url(plan.date))
