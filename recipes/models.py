from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, F, Q
from django.urls import reverse
from django.utils.text import slugify

from .utils import format_quantity
from .validators import validate_image_extension, validate_image_size


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    emoji = models.CharField(max_length=8, blank=True, help_text="Shown on category tiles and placeholder images.")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Cuisine(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DietaryPreference(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RecipeQuerySet(models.QuerySet):
    def with_stats(self):
        """Attach rating stats and total time; avoids per-card queries."""
        return self.select_related("category", "cuisine").annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
            total_minutes=F("prep_time") + F("cook_time"),
        )


class Recipe(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField()
    image = models.ImageField(
        upload_to="recipes/%Y/%m/",
        blank=True,
        validators=[validate_image_extension, validate_image_size],
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="recipes")
    cuisine = models.ForeignKey(Cuisine, on_delete=models.PROTECT, related_name="recipes")
    diets = models.ManyToManyField(DietaryPreference, blank=True, related_name="recipes")
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.EASY)
    prep_time = models.PositiveSmallIntegerField(help_text="Minutes")
    cook_time = models.PositiveSmallIntegerField(help_text="Minutes")
    servings = models.PositiveSmallIntegerField(default=4)
    calories = models.PositiveIntegerField(null=True, blank=True, help_text="Per serving")
    protein = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text="Grams per serving")
    carbohydrates = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text="Grams per serving")
    fat = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text="Grams per serving")
    fiber = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text="Grams per serving")
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RecipeQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "title"]
        indexes = [
            models.Index(fields=["featured"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["title"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(servings__gte=1), name="recipe_servings_gte_1"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "recipe"
            slug, n = base, 2
            while Recipe.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("recipes:detail", args=[self.slug])

    @property
    def total_time(self):
        return self.prep_time + self.cook_time

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return reverse("recipes:placeholder", args=[self.slug])

    @property
    def has_nutrition(self):
        return any(v is not None for v in (self.calories, self.protein, self.carbohydrates, self.fat, self.fiber))


class IngredientCategory(models.TextChoices):
    VEGETABLES = "vegetables", "Vegetables"
    FRUITS = "fruits", "Fruits"
    MEAT = "meat", "Meat"
    SEAFOOD = "seafood", "Seafood"
    DAIRY = "dairy", "Dairy & Eggs"
    GRAINS = "grains", "Grains & Legumes"
    SPICES = "spices", "Spices & Herbs"
    PANTRY = "pantry", "Pantry"
    OTHER = "other", "Other"


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=IngredientCategory.choices, default=IngredientCategory.PANTRY)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="recipe_ingredients")
    quantity = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Leave empty for 'to taste'.")
    unit = models.CharField(max_length=30, blank=True, help_text="e.g. g, ml, tbsp, cloves")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_ingredient_per_recipe"),
        ]

    def __str__(self):
        return f"{self.display} ({self.recipe})"

    @property
    def display(self):
        return self.scaled_display(1)

    def scaled_display(self, factor):
        if self.quantity is None:
            return f"{self.ingredient.name} (to taste)"
        qty = format_quantity((self.quantity * Decimal(str(factor))).quantize(Decimal("0.01")))
        unit = self.unit.strip()
        if unit in {"", "pc", "piece", "pieces"}:
            return f"{qty} {self.ingredient.name}"
        return f"{qty} {unit} {self.ingredient.name}"


class Instruction(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="instructions")
    step_number = models.PositiveSmallIntegerField()
    instruction = models.TextField()

    class Meta:
        ordering = ["step_number"]
        constraints = [
            models.UniqueConstraint(fields=["recipe", "step_number"], name="unique_step_per_recipe"),
        ]

    def __str__(self):
        return f"{self.recipe} - step {self.step_number}"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_favorite_per_user"),
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.recipe}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipe", "-created_at"])]
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_review_per_user"),
            models.CheckConstraint(condition=Q(rating__gte=1) & Q(rating__lte=5), name="review_rating_1_to_5"),
        ]

    def __str__(self):
        return f"{self.user} rated {self.recipe} {self.rating}/5"
