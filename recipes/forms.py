from django import forms

from config.forms import BootstrapFormMixin

from .models import Review


class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    rating = forms.IntegerField(min_value=1, max_value=5, widget=forms.HiddenInput)

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "What did you think? (optional)"}),
        }

    def clean_comment(self):
        comment = self.cleaned_data.get("comment", "").strip()
        if len(comment) > 2000:
            raise forms.ValidationError("Reviews can be at most 2000 characters.")
        return comment
