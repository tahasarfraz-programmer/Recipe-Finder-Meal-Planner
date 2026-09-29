from django import forms

from config.forms import BootstrapFormMixin

from .models import ShoppingListItem


class ShoppingItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ["name", "quantity", "unit", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Item, e.g. Basmati rice"}),
            "quantity": forms.NumberInput(attrs={"placeholder": "Qty", "step": "0.01", "min": "0"}),
            "unit": forms.TextInput(attrs={"placeholder": "Unit"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter an item name.")
        return name
