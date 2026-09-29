import datetime

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from config.forms import BootstrapAuthenticationForm
from planner.models import MealPlan
from recipes.models import Favorite, Recipe
from shopping.models import ShoppingListItem

from .forms import ProfileForm, RegisterForm, UserUpdateForm
from .models import Profile


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = BootstrapAuthenticationForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Recipe Finder, {user.username}!")
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


def _counts(user):
    return {
        "favorites_count": Favorite.objects.filter(user=user).count(),
        "planned_count": MealPlan.objects.filter(user=user).count(),
        "cooked_count": MealPlan.objects.filter(user=user, is_cooked=True).count(),
        "shopping_count": ShoppingListItem.objects.filter(user=user).count(),
    }


@login_required
def dashboard(request):
    today = datetime.date.today()
    todays = {p.meal_type: p for p in MealPlan.objects.filter(user=request.user, date=today).select_related("recipe", "recipe__category")}
    slots = [(value, label, todays.get(value)) for value, label in MealPlan.MealType.choices]
    upcoming = (
        MealPlan.objects.filter(user=request.user, date__gt=today).select_related("recipe").order_by("date")[:5]
    )
    suggestions = Recipe.objects.with_stats().filter(featured=True).order_by("?")[:4]
    context = {"today": today, "slots": slots, "upcoming": upcoming, "suggestions": suggestions,
               "fav_ids": set(Favorite.objects.filter(user=request.user).values_list("recipe_id", flat=True))}
    context.update(_counts(request.user))
    return render(request, "accounts/dashboard.html", context)


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    user_form = UserUpdateForm(request.POST or None, instance=request.user)
    profile_form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    if request.method == "POST":
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        messages.error(request, "Please correct the errors below.")
    context = {"user_form": user_form, "profile_form": profile_form, "profile": profile_obj}
    context.update(_counts(request.user))
    return render(request, "accounts/profile.html", context)
