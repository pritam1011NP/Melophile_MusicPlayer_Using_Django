# urls.py - Add the lyrics fetch endpoint
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from . import views

app_name = "App"

urlpatterns = [
    path("", views.index, name="index"),
    path("fetch-lyrics/", views.fetch_lyrics, name="fetch_lyrics"),  # New endpoint
]