from django.conf import settings
from django.db import models


class MealPlan(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_plans")
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MealType.choices)
    recipe = models.ForeignKey("recipes.Recipe", on_delete=models.CASCADE, related_name="meal_plans")
    is_cooked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "meal_type"]
        indexes = [models.Index(fields=["user", "date"])]
        constraints = [
            models.UniqueConstraint(fields=["user", "date", "meal_type"], name="one_meal_per_slot"),
        ]

    def __str__(self):
        return f"{self.user} - {self.date} {self.meal_type}: {self.recipe}"
