from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from recipes import views as recipe_views

admin.site.site_header = "Recipe Finder administration"
admin.site.site_title = "Recipe Finder admin"
admin.site.index_title = "Manage recipes, users and content"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", recipe_views.home, name="home"),
    path("", include("accounts.urls")),
    path("meal-planner/", include("planner.urls")),
    path("shopping-list/", include("shopping.urls")),
    path("", include("recipes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
