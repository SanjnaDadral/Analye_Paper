from django.contrib import admin
from django.urls import path, include

# Remove or comment out these two lines if they exist:
# from django.contrib.staticfiles.urls import staticfiles_urlpatterns
# urlpatterns += staticfiles_urlpatterns()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analyzer.urls')),   # ← your app urls
]

# Only add this in DEVELOPMENT (local), NOT in production
# from django.conf import settings
# from django.conf.urls.static import static

# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)