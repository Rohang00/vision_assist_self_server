import json
import threading
import time

import cv2
import numpy as np
import paho.mqtt.client as mqtt
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators import gzip
from ultralytics import YOLO

from .models import DetectionSetting, VideoSample

run_frame_generator = False
video_source_running = False
update_video_frame = False
new_frame_to_encode = False

video_source_obj = None

run_object_detection = False
obj_detection_running = False


client = mqtt.Client('vision_assist')

def on_connect(client, userdata, flags, rc):
   pass
   # print(f'Connected @ {time.time()}')

def on_disconnect(client, userdata, rc):
   pass
   # print(f'Disconnected @ {time.time()}')


client.on_connect = on_connect
client.on_disconnect = on_disconnect


setting =  DetectionSetting.objects.first()


client.connect(setting.mqtt_broker, setting.mqtt_port, 60)

class VideoSource(object):

   def get_video_source(self):

      if setting.source == 'video_file':
         return VideoSample.objects.filter(active = True).first().video.path
      elif setting.source == 'camera':
         return setting.camera_id
      else:
         return 0

   def start(self):
      global video_source_running, run_frame_generator, update_video_frame

      self.video = cv2.VideoCapture(self.get_video_source())
      self.grabbed, self.frame = self.video.read()
      self.object_detected_frame = self.frame
      update_video_frame = True
      threading.Thread(target=self.update, args=(), daemon=True).start()
      video_source_running = True


   def __del__(self):
      self.video.release()

   def get_frame_to_stream(self):
      global new_frame_to_encode

      if not run_object_detection:
         image = self.frame

      else:
         image = self.object_detected_frame

      _, jpeg = cv2.imencode('.jpg', image)
      return jpeg.tobytes()

   def update(self):
      update_delay = 0

      if setting.source == 'video_file':
         update_delay = setting.frame_update_delay

      global new_frame_to_encode

      while update_video_frame:
         time.sleep(update_delay)
         self.grabbed, self.frame = self.video.read()
         new_frame_to_encode = True
         if not self.grabbed:
            close_video_and_streaming()

         if not run_object_detection:
            new_frame_to_encode = True
         
   def stop(self):
      global video_source_running, run_frame_generator, update_video_frame, run_object_detection

      update_video_frame = False
      run_frame_generator = False
      video_source_running = False
      run_object_detection = False
      self.video.release()

   def start_object_detection(self):
      global run_object_detection

      run_object_detection = True
      threading.Thread(target=self.object_detection, args=(), daemon=True).start()


   def object_detection(self):
      global new_frame_to_encode, video_source_obj, obj_detection_running
      predection_threshold = setting.predection_threshold
      center_x_plus_minus = setting.center_x_plus_minus
      predection_confidence = setting.predection_confidence
      show_detections = setting.show_detections

      (h, w) = self.frame.shape[:2]
      frame_center = w/2

      center_from_to = ((w/2)-center_x_plus_minus, (w/2) + center_x_plus_minus)

      obj_pos = ''

      last_prediction = 0

      font = cv2.FONT_ITALIC

      detection_dict = {
      'person' : 0,
      'bicycle' : 1,
      'car' : 2,
      'motorcycle' : 3,
      'bus' : 5,
      'truck' : 7,
      'traffic light' : 9,
      'fire hydrant' : 10,
      'stop sign' : 11,
      'bench' : 13,
      'cat' : 15,
      'dog' : 16,
      'cow' : 19,
      }

      detected_ids = []

      yolo_model = YOLO()

      while run_object_detection:
         obj_detection_running = True

         detected_dict = {}

         if self.grabbed:
            if time.time() > last_prediction + predection_threshold:
               object_detection_frame = self.frame.copy()
               results = yolo_model.track(
                  source = object_detection_frame, show = show_detections, conf = predection_confidence,
                  verbose = False, persist = True, classes = list(detection_dict.values())
               )

               last_prediction = time.time()
               
               if len(results) > 0:
                  cv2.line(object_detection_frame, (int(w/2), 0), (int(w/2), h), (0,0,0), 2) 

               for result in results:

                  if result.boxes.id is not  None:
                     for (box, cls, conf, id) in zip(result.boxes.xyxy, result.boxes.cls, result.boxes.conf, result.boxes.id):
                     # for (box, cls, conf) in zip(result.boxes.xyxy, result.boxes.cls, result.boxes.conf):
                        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])

                        cv2.circle(object_detection_frame, (x1, y1), 4, (0, 255, 0), -1) 
                        cv2.circle(object_detection_frame, (x2, y2), 4, (0, 0, 255), -1)  

                        centroid = (int((x1+x2)/2), int((y1+y2)/2))

                        cv2.circle(object_detection_frame, centroid, 4, (0, 255, 255), -1)

                        cv2.rectangle(object_detection_frame, (x1, y1), (x2, y2), (255, 255, 0), 1)
                     
                        name = list(detection_dict.keys())[list(detection_dict.values()).index(cls)]

                        cv2.putText(object_detection_frame, name, (centroid[0], centroid[1] + 30), font, 0.5, (52, 52, 255), 1)
                        cv2.putText(object_detection_frame, f'{str(id.item())}', (centroid[0] + 10, centroid[1]), font, 0.5, (52, 52, 255), 1)

                        if id.item() not in detected_ids:
                           centroid_x = centroid[0]

                           if centroid_x <= center_from_to[0]:
                              obj_pos = 'l'
                           
                           elif centroid_x >= center_from_to[1]:
                              obj_pos = 'r'

                           elif centroid_x >= center_from_to[0] and centroid_x <= center_from_to[1]:
                              obj_pos = 'c'

                           detected_dict[str(id.item())] = [name, obj_pos]

                        detected_ids.append(id.item())
                        detected_ids = list(set(detected_ids))

               if len(detected_dict) > 0:
                  client.publish('detections', json.dumps(detected_dict))

            self.object_detected_frame = object_detection_frame   
            new_frame_to_encode = True

      obj_detection_running = False

   def stop_object_detection(self):
      global run_object_detection
      run_object_detection = False         


def frame_generator(video_source_obj):
   global new_frame_to_encode
   while run_frame_generator:
      if new_frame_to_encode:
         frame = video_source_obj.get_frame_to_stream()
         yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

         new_frame_to_encode = False


def close_video_and_streaming():
   global video_source_obj, run_frame_generator, run_object_detection
   run_frame_generator = False
   run_object_detection = False
   if video_source_obj:
      video_source_obj.stop()
      del video_source_obj
      video_source_obj = None


@gzip.gzip_page
def feed(request):
   global video_source_obj, run_frame_generator, run_object_detection, obj_detection_running
   feed_command = request.GET.get('feed_command') 

   if feed_command == 'open_video_and_streaming':
      if not video_source_running:
         video_source_obj = VideoSource()
         video_source_obj.start()
         run_frame_generator = True
         return StreamingHttpResponse(
            frame_generator(video_source_obj), 
            content_type="multipart/x-mixed-replace;boundary=frame"
         )

      elif video_source_running and not run_frame_generator:
         run_frame_generator = True
         return StreamingHttpResponse(
            frame_generator(video_source_obj), 
            content_type="multipart/x-mixed-replace;boundary=frame"
         )
      
      else:
         return HttpResponse('video open and streaming already')

   elif feed_command == 'close_video_and_streaming':
      if video_source_running and video_source_obj:
         close_video_and_streaming()
         return HttpResponse('closed video and streaming')
      
      return HttpResponse('video and streaming not running')


   elif feed_command == 'stop_streaming':
      if run_frame_generator:
         run_frame_generator = False
         run_object_detection = False
         return HttpResponse('stopped streaming')

      else:
         return HttpResponse('streaming not running')

   elif feed_command == 'start_object_detection':
      if video_source_obj and not obj_detection_running:
         video_source_obj.start_object_detection()
         return HttpResponse('started object detection')

      elif obj_detection_running:
         return HttpResponse('obj detection already running')

      else:
         return HttpResponse('no action')

   elif feed_command == 'stop_object_detection':
      if video_source_obj and obj_detection_running:
         video_source_obj.stop_object_detection()
         return HttpResponse('object detection stopped')
      
      elif video_source_obj and not obj_detection_running:
         return HttpResponse('object detection stopped already')
      
      else:
         return HttpResponse('no action')

   elif feed_command is None:
      return HttpResponse('no command')

   else:
      return HttpResponse(f'{feed_command} not found')
