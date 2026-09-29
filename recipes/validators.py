from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

validate_image_extension = FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])


def validate_image_size(image):
    if image and image.size > MAX_IMAGE_SIZE:
        raise ValidationError("Images must be 5 MB or smaller.")
