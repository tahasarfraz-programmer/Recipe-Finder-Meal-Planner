from django.urls import path

from . import views

app_name = "recipes"

urlpatterns = [
    path("recipes/", views.recipe_list, name="list"),
    path("search/", views.recipe_list, name="search"),
    path("favorites/", views.favorites, name="favorites"),
    path("about/", views.about, name="about"),
    path("recipes/<slug:slug>/", views.recipe_detail, name="detail"),
    path("recipes/<slug:slug>/placeholder.svg", views.recipe_placeholder, name="placeholder"),
    path("recipes/<slug:slug>/favorite/", views.favorite_toggle, name="favorite_toggle"),
    path("recipes/<slug:slug>/review/", views.review_save, name="review_save"),
    path("recipes/<slug:slug>/review/delete/", views.review_delete, name="review_delete"),
]
