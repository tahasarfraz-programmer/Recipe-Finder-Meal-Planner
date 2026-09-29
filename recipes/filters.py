"""Search, filtering and sorting for recipe listings."""
from django.db.models import F

from .models import Category, Cuisine, DietaryPreference, Recipe

STOPWORDS = {
    "recipe", "recipes", "meal", "meals", "food", "foods", "dish", "dishes",
    "and", "with", "for", "the", "a", "of", "in", "to", "me", "some",
}
QUICK_WORDS = {"quick", "fast", "speedy"}
EASY_WORDS = {"easy", "simple", "beginner"}

TIME_CHOICES = [
    ("15", "Under 15 minutes"),
    ("30", "Under 30 minutes"),
    ("60", "Under 60 minutes"),
    ("60plus", "60+ minutes"),
]

SORT_CHOICES = [
    ("newest", "Newest"),
    ("rating", "Top rated"),
    ("time", "Quickest"),
    ("calories", "Lowest calories"),
    ("title", "Name (A-Z)"),
]


def _term_query(term):
    """A term matches if it appears in any of the searchable fields."""
    from django.db.models import Q

    variants = {term}
    if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
        variants.add(term[:-1])
    q = Q()
    for v in variants:
        q |= (
            Q(title__icontains=v)
            | Q(description__icontains=v)
            | Q(category__name__icontains=v)
            | Q(cuisine__name__icontains=v)
            | Q(diets__name__icontains=v)
            | Q(recipe_ingredients__ingredient__name__icontains=v)
        )
    return q


def filtered_recipes(params, base=None):
    """Return an annotated Recipe queryset filtered by the GET params.

    Filters are combined with AND across groups, OR within categories,
    cuisines and difficulty, and AND across selected dietary preferences.
    """
    ids = (Recipe.objects.all() if base is None else base).annotate(_minutes=F("prep_time") + F("cook_time"))

    for term in params.get("q", "").lower().split():
        term = term.strip(",.!?")
        if not term or term in STOPWORDS:
            continue
        if term in QUICK_WORDS:
            ids = ids.filter(_minutes__lte=30)
        elif term in EASY_WORDS:
            ids = ids.filter(difficulty=Recipe.Difficulty.EASY)
        else:
            ids = ids.filter(_term_query(term))

    categories = params.getlist("category")
    if categories:
        ids = ids.filter(category__slug__in=categories)
    cuisines = params.getlist("cuisine")
    if cuisines:
        ids = ids.filter(cuisine__slug__in=cuisines)
    for diet in params.getlist("diet"):
        ids = ids.filter(diets__slug=diet)
    difficulties = [d for d in params.getlist("difficulty") if d in Recipe.Difficulty.values]
    if difficulties:
        ids = ids.filter(difficulty__in=difficulties)

    time = params.get("time", "")
    if time in {"15", "30", "60"}:
        ids = ids.filter(_minutes__lte=int(time))
    elif time == "60plus":
        ids = ids.filter(_minutes__gte=60)

    return Recipe.objects.with_stats().filter(pk__in=ids.values("pk"))


def apply_sort(qs, sort):
    if sort == "rating":
        return qs.order_by(F("avg_rating").desc(nulls_last=True), "-review_count", "title")
    if sort == "time":
        return qs.order_by("total_minutes", "title")
    if sort == "calories":
        return qs.order_by(F("calories").asc(nulls_last=True), "title")
    if sort == "title":
        return qs.order_by("title")
    return qs.order_by("-created_at", "title")


def filter_context(params):
    selected = {
        "category": params.getlist("category"),
        "cuisine": params.getlist("cuisine"),
        "diet": params.getlist("diet"),
        "difficulty": params.getlist("difficulty"),
        "time": params.get("time", ""),
    }
    active = sum(len(v) if isinstance(v, list) else (1 if v else 0) for v in selected.values())
    return {
        "categories": Category.objects.all(),
        "cuisines": Cuisine.objects.all(),
        "diets": DietaryPreference.objects.all(),
        "difficulty_choices": Recipe.Difficulty.choices,
        "time_choices": TIME_CHOICES,
        "sort_choices": SORT_CHOICES,
        "selected": selected,
        "active_filter_count": active,
        "q": params.get("q", "").strip(),
        "sort": params.get("sort", "newest"),
    }
