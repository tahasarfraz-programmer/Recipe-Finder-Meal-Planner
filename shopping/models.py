from django.conf import settings
from django.db import models

from recipes.models import IngredientCategory
from recipes.utils import format_quantity


class ShoppingListItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shopping_items")
    ingredient = models.ForeignKey("recipes.Ingredient", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=IngredientCategory.choices, default=IngredientCategory.OTHER)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=30, blank=True)
    is_purchased = models.BooleanField(default=False)
    from_plan = models.BooleanField(default=False, help_text="Created by 'Generate from meal plan'.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_purchased", "name"]
        indexes = [models.Index(fields=["user", "is_purchased"])]

    def __str__(self):
        return self.name

    @property
    def display_quantity(self):
        qty = format_quantity(self.quantity)
        return f"{qty} {self.unit}".strip() if qty else self.unit
