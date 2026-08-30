from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

urlpatterns = [
    path("", lambda request: redirect("menu:list")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("menu/", include("menu.urls")),
    path("inventory/", include("inventory.urls")),
    path("tables/", include("tables.urls")),
    path("orders/", include("orders.urls")),
    path("dashboard/", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
