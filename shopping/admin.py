from django.contrib import admin

from .models import ShoppingListItem


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "quantity", "unit", "category", "is_purchased", "created_at")
    list_filter = ("category", "is_purchased")
    search_fields = ("name", "user__username")
    ordering = ("-created_at",)
    list_select_related = ("user",)
