"""Small helpers for building test data."""
from decimal import Decimal

from .models import Category, Cuisine, DietaryPreference, Ingredient, Instruction, Recipe, RecipeIngredient


def make_recipe(title="Test Chicken Pasta", category="Dinner", cuisine="Italian", diets=(), **kwargs):
    cat, _ = Category.objects.get_or_create(name=category, defaults={"slug": category.lower(), "emoji": "🍝"})
    cui, _ = Cuisine.objects.get_or_create(name=cuisine, defaults={"slug": cuisine.lower()})
    defaults = dict(description=f"{title} description", prep_time=10, cook_time=20, servings=4, calories=500)
    defaults.update(kwargs)
    recipe = Recipe.objects.create(title=title, category=cat, cuisine=cui, **defaults)
    for name in diets:
        diet, _ = DietaryPreference.objects.get_or_create(name=name, defaults={"slug": name.lower().replace(" ", "-")})
        recipe.diets.add(diet)
    return recipe


def add_ingredient(recipe, name, quantity="100", unit="g", category="pantry"):
    ingredient, _ = Ingredient.objects.get_or_create(name=name, defaults={"category": category})
    return RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, quantity=Decimal(quantity), unit=unit)


def add_step(recipe, number, text):
    return Instruction.objects.create(recipe=recipe, step_number=number, instruction=text)
