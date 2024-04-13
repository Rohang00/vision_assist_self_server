from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Vision Assist SuperAdmin'
admin.site.site_title = 'Vision Assist Admin'
admin.site.site_url = ''
admin.site.index_title = 'Vision Assist'


from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/vision-controller/', include('vision_controller.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
