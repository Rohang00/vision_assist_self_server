import time

import cv2
from ultralytics import YOLO

from mqtt_handlers import *

camera = cv2.VideoCapture('/mnt/devssd/Personal/yolo_obj/video_samples/walking1.mp4')
# camera = cv2.VideoCapture('/mnt/devssd/Personal/yolo_obj/video_samples/elephant.mp4')


ret, frame = camera.read()
(h, w) = frame.shape[:2]

frame_center = w/2
center_x_plus_minus = 100

center_from_to = ((w/2)-center_x_plus_minus, (w/2) + center_x_plus_minus)
obj_pos = ''

model = YOLO()


last_prediction = 0
predection_threshold = 0.001

predection_confidence = 0.8
show_detections = True

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
previous_ids = []

client.connect(mqtt_broker, mqtt_port, 60)


try:
   while True:
      detected_dict = {}
      # time.sleep(0.1)
      ret, frame = camera.read()


      if ret:
         if time.time() > last_prediction + predection_threshold:

            frame = cv2.resize(frame, (int(w/1),int(h/1)))

            results = model.track(
               source = frame, show = show_detections, conf = predection_confidence,
               verbose = False, persist = True, classes = list(detection_dict.values())
            )         

            last_prediction = time.time()
            if len(results) > 0:
               cv2.line(frame, (int(w/2), 0), (int(w/2), h), (0,0,0), 2) 

            for result in results:

               if result.boxes.id is not  None:
                  for (box, cls, conf, id) in zip(result.boxes.xyxy, result.boxes.cls, result.boxes.conf, result.boxes.id):
                  # for (box, cls, conf) in zip(result.boxes.xyxy, result.boxes.cls, result.boxes.conf):
                     x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])

                     cv2.circle(frame, (x1, y1), 4, (0, 255, 0), -1) 
                     cv2.circle(frame, (x2, y2), 4, (0, 0, 255), -1)  

                     centroid = (int((x1+x2)/2), int((y1+y2)/2))

                     cv2.circle(frame, centroid, 4, (0, 255, 255), -1)

                     cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 1)
                  
                     name = list(detection_dict.keys())[list(detection_dict.values()).index(cls)]

                     cv2.putText(frame, name, (centroid[0], centroid[1] + 30), font, 0.5, (52, 52, 255), 1)
                     cv2.putText(frame, f'{str(id.item())}', (centroid[0] + 10, centroid[1]), font, 0.5, (52, 52, 255), 1)

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

                     # print(id.item())
                     # cv2.putText(frame, str(round(conf.item(),2)), (centroid[0], centroid[1] - 30), font, 0.5, (52, 52, 255), 1)

                  
                  # print(result.boxes.xyxy)   # box with xyxy format, (N, 4)
                  # result.boxes.xywh   # box with xywh format, (N, 4)
                  # result.boxes.xyxyn  # box with xyxy format but normalized, (N, 4)
                  # result.boxes.xywhn  # box with xywh format but normalized, (N, 4)
                  # print(result.boxes.conf)   # confidence score, (N, 1)
                  # print(result.boxes.cls)    # cls, (N, 1)
                  # cv2.circle(frame, (result.boxes.xyxy[0],result.boxes.xyxy[1]), 5, (0,255,0), -1)



               frame = cv2.resize(frame, (int(w/1),int(h/1)))
               cv2.imshow('original', frame)

               if cv2.waitKey(1) == ord('q'):
                  camera.release()
                  cv2.destroyAllWindows()
                  break
               
               new_items = [item for item in detected_ids if item not in previous_ids]
               previous_ids = detected_ids

               if len(detected_dict) > 0:
                  client.publish('detections', json.dumps(detected_dict))

      else:
         camera.release()
         cv2.destroyAllWindows()
         break

except KeyboardInterrupt:
   print('Graceful exit')