from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("ui.urls")),
    path("health/", include("operations.urls")),
    path("admin/", admin.site.urls),
]
