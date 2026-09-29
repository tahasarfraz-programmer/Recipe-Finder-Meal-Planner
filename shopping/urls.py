from django.urls import path

from . import views

app_name = "shopping"

urlpatterns = [
    path("", views.shopping_list, name="list"),
    path("add/", views.add_item, name="add"),
    path("generate/", views.generate_from_plan, name="generate"),
    path("clear-purchased/", views.clear_purchased, name="clear_purchased"),
    path("clear-all/", views.clear_all, name="clear_all"),
    path("<int:pk>/edit/", views.edit_item, name="edit"),
    path("<int:pk>/toggle/", views.toggle_item, name="toggle"),
    path("<int:pk>/delete/", views.delete_item, name="delete"),
]
