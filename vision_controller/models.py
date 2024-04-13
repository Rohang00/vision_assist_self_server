import os

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class VideoSample(models.Model):
   title = models.CharField(max_length = 255)
   video = models.FileField(
      upload_to = 'video_samples/',
      validators=[
         FileExtensionValidator(
               allowed_extensions=['mp4'])]
   )
   active = models.BooleanField(default =  False)

   class Meta:
      ordering = ('id',)

   def __str__(self):
      return self.title

   def save(self, *args, **kwargs):
      old_video = False

      if self.pk:
         old_video_file = VideoSample.objects.get(pk=self.pk).video
         if old_video_file:
            old_video = True

         VideoSample.objects.filter(active=True).update(active=False)

         super().save(*args, **kwargs)

         new_video_file = self.video

         if old_video and old_video_file != new_video_file:
            if os.path.isfile(old_video_file.path):
               os.remove(old_video_file.path)
      else:
         return super().save(*args, **kwargs)


@receiver(post_delete, sender=VideoSample)
def delete_featured_video(instance, **kwargs):
   if instance.video:
      video_path = instance.video.path
      if os.path.isfile(video_path):
         os.remove(video_path)


class DetectionSetting(models.Model):
   source_choices = (
      ('camera', 'Camera'),
      ('video_file', 'Video File')
   )
   source = models.CharField(
      max_length = 15, 
      choices = source_choices
   )

   camera_id = models.PositiveSmallIntegerField(default = 0)

   center_x_plus_minus = models.PositiveSmallIntegerField(default = 100)
   predection_threshold= models.FloatField(default = 0.001)
   predection_confidence= models.FloatField(default = 0.8)

   show_detections = models.BooleanField(default = False)
   frame_update_delay = models.FloatField(default = 0.1)
   
   mqtt_broker = models.CharField(max_length = 50, default = 'localhost')
   mqtt_port = models.PositiveSmallIntegerField(default = 1883)

   def __str__(self) -> str:
      return 'detecion_setting'

