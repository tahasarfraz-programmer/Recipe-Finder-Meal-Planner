from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from recipes.validators import validate_image_extension, validate_image_size


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, validators=[validate_image_extension, validate_image_size])
    dietary_preferences = models.ManyToManyField("recipes.DietaryPreference", blank=True, related_name="profiles")
    favorite_cuisines = models.ManyToManyField("recipes.Cuisine", blank=True, related_name="profiles")
    default_servings = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(20)])

    def __str__(self):
        return f"Profile of {self.user}"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username
