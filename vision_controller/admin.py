from django.contrib import admin
from django.contrib.auth.models import Group, User

from .models import DetectionSetting, VideoSample

admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(VideoSample)
class VideosSampleAdmin(admin.ModelAdmin):
   list_display = ('id', 'title', 'active')
   list_display_links = list_display
   search_fields = ('title', )

@admin.register(DetectionSetting)
class DetectionSettingAdmin(admin.ModelAdmin):
   list_display = (
      'source', 'show_detections', 'predection_confidence', 'mqtt_broker', 
      'mqtt_port'
   )

   def has_add_permission(self, *args, **kwargs):
      return False if self.model.objects.count() > 0 else super().has_add_permission(*args, **kwargs)

   def has_delete_permission(self, *args, **kwargs):
      return False
