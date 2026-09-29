from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category, Cuisine, DietaryPreference, Favorite, Ingredient, Instruction,
    Recipe, RecipeIngredient, Review,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "emoji")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(DietaryPreference)
class DietaryPreferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)
    ordering = ("name",)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 3
    autocomplete_fields = ("ingredient",)


class InstructionInline(admin.StackedInline):
    model = Instruction
    extra = 3
    ordering = ("step_number",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "title", "category", "cuisine", "difficulty", "total_time", "calories", "featured", "created_at")
    list_display_links = ("thumbnail", "title")
    list_editable = ("featured",)
    list_filter = ("featured", "category", "cuisine", "difficulty", "diets", "created_at")
    search_fields = ("title", "description", "recipe_ingredients__ingredient__name")
    ordering = ("-created_at",)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("diets",)
    list_select_related = ("category", "cuisine")
    date_hierarchy = "created_at"
    inlines = [RecipeIngredientInline, InstructionInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "description", "image", "featured")}),
        ("Classification", {"fields": ("category", "cuisine", "diets", "difficulty")}),
        ("Timing & servings", {"fields": ("prep_time", "cook_time", "servings")}),
        ("Nutrition (per serving)", {"fields": ("calories", "protein", "carbohydrates", "fat", "fiber"), "classes": ("collapse",)}),
    )

    @admin.display(description="Image")
    def thumbnail(self, obj):
        return format_html('<img src="{}" alt="" style="width:56px;height:42px;object-fit:cover;border-radius:6px">', obj.image_url)

    @admin.display(description="Total (min)")
    def total_time(self, obj):
        return obj.total_time


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("recipe", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("recipe__title", "user__username", "comment")
    ordering = ("-created_at",)
    list_select_related = ("recipe", "user")
    autocomplete_fields = ("recipe", "user")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "created_at")
    search_fields = ("user__username", "recipe__title")
    ordering = ("-created_at",)
    list_select_related = ("recipe", "user")
