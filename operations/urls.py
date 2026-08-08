from django.urls import path

from .views import health


app_name = "operations"

urlpatterns = [
    path("", health, name="health"),
]
