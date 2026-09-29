from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.week_view, name="week"),
    path("add/", views.add_meal, name="add"),
    path("generate/", views.generate, name="generate"),
    path("<int:pk>/remove/", views.remove_meal, name="remove"),
    path("<int:pk>/cooked/", views.toggle_cooked, name="cooked"),
    path("<int:pk>/regenerate/", views.regenerate_meal, name="regenerate"),
]
