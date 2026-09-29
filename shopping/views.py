import datetime
from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from planner.models import MealPlan
from planner.views import monday_of
from recipes.models import IngredientCategory, RecipeIngredient

from .forms import ShoppingItemForm
from .models import ShoppingListItem


@login_required
def shopping_list(request):
    items = list(ShoppingListItem.objects.filter(user=request.user))
    grouped = []
    for value, label in IngredientCategory.choices:
        group = [i for i in items if i.category == value]
        if group:
            grouped.append({"label": label, "items": group})
    purchased = sum(1 for i in items if i.is_purchased)
    return render(request, "shopping/list.html", {
        "groups": grouped, "form": ShoppingItemForm(), "total": len(items), "purchased": purchased,
    })


@login_required
@require_POST
def add_item(request):
    form = ShoppingItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        messages.success(request, "Shopping list updated.")
    else:
        messages.error(request, "Could not add item: " + " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("shopping:list")


@login_required
def edit_item(request, pk):
    item = get_object_or_404(ShoppingListItem, pk=pk, user=request.user)
    form = ShoppingItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shopping list updated.")
        return redirect("shopping:list")
    return render(request, "shopping/edit_item.html", {"form": form, "item": item})


@login_required
@require_POST
def toggle_item(request, pk):
    item = get_object_or_404(ShoppingListItem, pk=pk, user=request.user)
    item.is_purchased = not item.is_purchased
    item.save(update_fields=["is_purchased"])
    return redirect("shopping:list")


@login_required
@require_POST
def delete_item(request, pk):
    get_object_or_404(ShoppingListItem, pk=pk, user=request.user).delete()
    messages.info(request, "Item removed.")
    return redirect("shopping:list")


@login_required
@require_POST
def clear_purchased(request):
    count, _ = ShoppingListItem.objects.filter(user=request.user, is_purchased=True).delete()
    messages.info(request, f"Cleared {count} purchased item{'s' if count != 1 else ''}.")
    return redirect("shopping:list")


@login_required
@require_POST
def clear_all(request):
    ShoppingListItem.objects.filter(user=request.user).delete()
    messages.info(request, "Shopping list cleared.")
    return redirect("shopping:list")


@login_required
@require_POST
def generate_from_plan(request):
    """Build the list from planned meals (this week by default), replacing earlier generated items."""
    try:
        start = datetime.date.fromisoformat(request.POST.get("start", ""))
        end = datetime.date.fromisoformat(request.POST.get("end", ""))
    except ValueError:
        start = monday_of(datetime.date.today())
        end = start + datetime.timedelta(days=6)

    plans = MealPlan.objects.filter(user=request.user, date__range=(start, end)).select_related("recipe")
    if not plans:
        messages.info(request, "Nothing is planned for that week yet, so there is nothing to shop for.")
        return redirect("shopping:list")

    profile = getattr(request.user, "profile", None)
    default_servings = profile.default_servings if profile else None
    totals = defaultdict(lambda: Decimal("0"))
    meta, unmeasured = {}, set()
    for plan in plans:
        factor = Decimal(default_servings or plan.recipe.servings) / Decimal(plan.recipe.servings)
        for ri in RecipeIngredient.objects.filter(recipe=plan.recipe).select_related("ingredient"):
            key = (ri.ingredient_id, ri.unit.strip().lower())
            meta[key] = ri
            if ri.quantity is None:
                unmeasured.add(key)
            else:
                totals[key] += ri.quantity * factor
    for key in unmeasured:
        totals.setdefault(key, None)

    ShoppingListItem.objects.filter(user=request.user, from_plan=True, is_purchased=False).delete()
    new_items = []
    for key, qty in totals.items():
        ri = meta[key]
        new_items.append(ShoppingListItem(
            user=request.user, ingredient=ri.ingredient, name=ri.ingredient.name, category=ri.ingredient.category,
            quantity=qty.quantize(Decimal("0.01")) if qty else None, unit=ri.unit.strip(), from_plan=True,
        ))
    ShoppingListItem.objects.bulk_create(new_items)
    messages.success(request, f"Shopping list updated with {len(new_items)} ingredients from your meal plan.")
    return redirect("shopping:list")
