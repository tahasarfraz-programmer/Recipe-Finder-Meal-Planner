from django.contrib import admin

from .models import MealPlan


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "meal_type", "recipe", "is_cooked")
    list_filter = ("meal_type", "is_cooked", "date")
    search_fields = ("user__username", "recipe__title")
    ordering = ("-date",)
    list_select_related = ("user", "recipe")
    autocomplete_fields = ("recipe", "user")
