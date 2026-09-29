import hashlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from .filters import apply_sort, filter_context, filtered_recipes
from .forms import ReviewForm
from .models import Category, Favorite, Recipe, Review

PAGE_SIZE = 12


def favorite_ids(user):
    if not user.is_authenticated:
        return set()
    return set(Favorite.objects.filter(user=user).values_list("recipe_id", flat=True))


def safe_next(request, fallback):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return fallback


def home(request):
    featured = Recipe.objects.with_stats().filter(featured=True)[:8]
    popular_categories = Category.objects.annotate(recipe_count=Count("recipes")).filter(recipe_count__gt=0).order_by("-recipe_count", "name")[:8]
    latest = Recipe.objects.with_stats().order_by("-created_at")[:4]
    return render(request, "home.html", {
        "featured": featured,
        "popular_categories": popular_categories,
        "latest": latest,
        "fav_ids": favorite_ids(request.user),
    })


def recipe_list(request):
    """Browse page; /search/ uses the same view with the search heading."""
    qs = apply_sort(filtered_recipes(request.GET), request.GET.get("sort"))
    page_obj = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    context = filter_context(request.GET)
    context.update({
        "page_obj": page_obj,
        "fav_ids": favorite_ids(request.user),
        "is_search": request.resolver_match.url_name == "search",
    })
    return render(request, "recipes/recipe_list.html", context)


def recipe_detail(request, slug):
    recipe = get_object_or_404(Recipe.objects.with_stats().prefetch_related("diets"), slug=slug)

    servings = recipe.servings
    if request.GET.get("servings", "").isdigit():
        servings = min(max(int(request.GET["servings"]), 1), 48)
    elif request.user.is_authenticated and hasattr(request.user, "profile"):
        servings = request.user.profile.default_servings
    factor = servings / recipe.servings
    ingredients = [
        {"display": ri.scaled_display(factor), "category": ri.ingredient.category}
        for ri in recipe.recipe_ingredients.select_related("ingredient")
    ]

    reviews = list(recipe.reviews.select_related("user"))
    user_review = None
    is_favorite = False
    if request.user.is_authenticated:
        user_review = next((r for r in reviews if r.user_id == request.user.id), None)
        is_favorite = Favorite.objects.filter(user=request.user, recipe=recipe).exists()

    related = (
        Recipe.objects.with_stats().filter(category=recipe.category).exclude(pk=recipe.pk)[:4]
    )
    return render(request, "recipes/recipe_detail.html", {
        "recipe": recipe,
        "ingredients": ingredients,
        "instructions": recipe.instructions.all(),
        "reviews": reviews,
        "user_review": user_review,
        "review_form": ReviewForm(instance=user_review),
        "is_favorite": is_favorite,
        "servings": servings,
        "related": related,
        "fav_ids": favorite_ids(request.user),
        "og_image": request.build_absolute_uri(recipe.image_url),
        "meal_types": [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner"), ("snack", "Snack")],
    })


@cache_control(max_age=86400, public=True)
def recipe_placeholder(request, slug):
    """Generated SVG placeholder so recipes without a photo still look good."""
    recipe = get_object_or_404(Recipe.objects.select_related("category"), slug=slug)
    hue = int(hashlib.md5(slug.encode()).hexdigest(), 16) % 360
    emoji = escape(recipe.category.emoji or "🍽️")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" role="img" aria-label="Recipe placeholder">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="hsl({hue},55%,82%)"/><stop offset="1" stop-color="hsl({(hue + 40) % 360},60%,68%)"/>
</linearGradient></defs>
<rect width="800" height="600" fill="url(#g)"/>
<circle cx="400" cy="300" r="170" fill="rgba(255,255,255,.35)"/>
<text x="400" y="360" font-size="180" text-anchor="middle">{emoji}</text></svg>"""
    return HttpResponse(svg, content_type="image/svg+xml")


@login_required
@require_POST
def favorite_toggle(request, slug):
    recipe = get_object_or_404(Recipe, slug=slug)
    favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
    if created:
        messages.success(request, "Recipe added to favorites!")
    else:
        favorite.delete()
        messages.info(request, "Recipe removed from favorites.")
    return redirect(safe_next(request, recipe.get_absolute_url()))


@login_required
def favorites(request):
    base = Recipe.objects.filter(favorites__user=request.user)
    fav_created = Favorite.objects.filter(user=request.user, recipe=OuterRef("pk")).values("created_at")[:1]
    qs = filtered_recipes(request.GET, base=base).annotate(fav_created=Subquery(fav_created))
    if request.GET.get("sort"):
        qs = apply_sort(qs, request.GET.get("sort"))
    else:
        qs = qs.order_by("-fav_created")
    page_obj = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    context = filter_context(request.GET)
    context.update({"page_obj": page_obj, "fav_ids": favorite_ids(request.user)})
    return render(request, "recipes/favorites.html", context)


@login_required
@require_POST
def review_save(request, slug):
    """Create a review, or update the user's existing one (one per user/recipe)."""
    recipe = get_object_or_404(Recipe, slug=slug)
    existing = Review.objects.filter(user=request.user, recipe=recipe).first()
    form = ReviewForm(request.POST, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.recipe = recipe
        review.save()
        messages.success(request, "Review updated." if existing else "Review submitted successfully.")
    else:
        messages.error(request, "Please choose a star rating between 1 and 5.")
    return redirect(f"{recipe.get_absolute_url()}#reviews")


@login_required
@require_POST
def review_delete(request, slug):
    recipe = get_object_or_404(Recipe, slug=slug)
    review = get_object_or_404(Review, user=request.user, recipe=recipe)
    review.delete()
    messages.info(request, "Your review was deleted.")
    return redirect(f"{recipe.get_absolute_url()}#reviews")


def about(request):
    return render(request, "about.html")
