import datetime

from django import forms

from config.forms import BootstrapFormMixin
from recipes.models import Cuisine, DietaryPreference, Recipe

from .models import MealPlan


class MealPlanForm(BootstrapFormMixin, forms.Form):
    recipe = forms.ModelChoiceField(queryset=Recipe.objects.order_by("title"), empty_label="Choose a recipe")
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    meal_type = forms.ChoiceField(choices=MealPlan.MealType.choices)


class GenerateMealPlanForm(BootstrapFormMixin, forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=datetime.date.today)
    days = forms.IntegerField(min_value=1, max_value=14, initial=7, label="Number of days")
    meals_per_day = forms.TypedChoiceField(
        choices=[(1, "1 (dinner)"), (2, "2 (lunch, dinner)"), (3, "3 (breakfast, lunch, dinner)"), (4, "4 (plus a snack)")],
        coerce=int, initial=3,
    )
    dietary_preference = forms.ModelChoiceField(queryset=DietaryPreference.objects.all(), required=False, empty_label="Any")
    cuisine = forms.ModelChoiceField(queryset=Cuisine.objects.all(), required=False, empty_label="Any")
    max_cooking_time = forms.TypedChoiceField(
        label="Maximum total time",
        choices=[("", "Any"), ("15", "15 minutes"), ("30", "30 minutes"), ("45", "45 minutes"), ("60", "60 minutes"), ("90", "90 minutes")],
        coerce=int, empty_value=None, required=False,
    )
    difficulty = forms.ChoiceField(choices=[("", "Any")] + list(Recipe.Difficulty.choices), required=False)
    calories_target = forms.IntegerField(
        label="Daily calorie target", required=False, min_value=800, max_value=6000,
        widget=forms.NumberInput(attrs={"placeholder": "Optional, e.g. 2000"}),
    )
    replace_existing = forms.BooleanField(required=False, label="Replace meals already planned in these slots")
