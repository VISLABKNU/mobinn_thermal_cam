#!/usr/bin/env python
# -*- coding: utf-8 -*-
#purethermal1-uvc-capture
"""
needs purethermal1 dir

"""

from uvctypes import *
import time
import cv2
import numpy as np
try:
  from queue import Queue
except ImportError:
  from Queue import Queue
import platform
# import fire_detect_yolo as fireyolo

import rospy
from sensor_msgs.msg  import Image
from std_msgs.msg import Float32MultiArray, MultiArrayDimension

# initialize the node
rospy.init_node('thermal_node', anonymous=True)

# define the publisher
pub = rospy.Publisher('thermal_image', Float32MultiArray, queue_size=1000)

thermal_array = Float32MultiArray()

# thermal_array.data = [0.0] * (120 * 160)

# Define the layout of the array (120 rows, 160 columns)
# thermal_array.layout.dim = [
#     MultiArrayDimension(label="height", size=120, stride=120*160),
#     MultiArrayDimension(label="width", size=160, stride=160)
# ]

# Initialize the data field with zeros (120*160 elements)

# define the multiarray
# thermal_array.data = [0.0] * 3


import rospy
from sensor_msgs.msg import Image
import std_msgs.msg
import numpy as np

def numpy_to_image_msg(thermal_array):
    img_msg = Image()
    
    # Fill in the necessary fields
    img_msg.header = std_msgs.msg.Header()
    img_msg.height = thermal_array.shape[0]
    img_msg.width = thermal_array.shape[1]
    img_msg.encoding = 'rgb8'  # Change this if you have a different encoding
    img_msg.is_bigendian = 0
    img_msg.step = img_msg.width * 2  # Assuming 16-bit data
    img_msg.data = thermal_array.tobytes()  # Convert the NumPy array to bytes
    
    return img_msg


BUF_SIZE = 2
q = Queue(BUF_SIZE)

def py_frame_callback(frame, userptr):

  array_pointer = cast(frame.contents.data, POINTER(c_uint16 * (frame.contents.width * frame.contents.height)))
  data = np.frombuffer(
    array_pointer.contents, dtype=np.dtype(np.uint16)
  ).reshape(
    frame.contents.height, frame.contents.width
  ) 

  if frame.contents.data_bytes != (2 * frame.contents.width * frame.contents.height):
    return

  if not q.full():
    q.put(data)

PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)


def ktoc(val):
  return (val - 27315) / 100.0

def raw_to_8bit(data):
  cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
  np.right_shift(data, 8, data)
  return cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)


def display_temperature(img, val_k, loc, color):
  val = ktoc(val_k)
  cv2.putText(img,"{0:.1f} C".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
  
  x, y = loc
  cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
  cv2.line(img, (x, y - 2), (x, y + 2), color, 1)



def main(vis = False):
  ctx = POINTER(uvc_context)()
  dev = POINTER(uvc_device)()
  devh = POINTER(uvc_device_handle)()
  ctrl = uvc_stream_ctrl()

  res = libuvc.uvc_init(byref(ctx), 0)
  if res < 0:
    print("uvc_init error")
    exit(1)

  try:
    res = libuvc.uvc_find_device(ctx, byref(dev), PT_USB_VID, PT_USB_PID, 0) 
    if res < 0:
      print("uvc_find_device error")
      exit(1)

    try:
      res = libuvc.uvc_open(dev, byref(devh))
      if res < 0:
        print("uvc_open error")
        exit(1)

      print("device opened!")

      print_device_info(devh)
      print_device_formats(devh)

      frame_formats = uvc_get_frame_formats_by_guid(devh, VS_FMT_GUID_Y16)
      # frame_formats = uvc_get_frame_formats_by_guid(devh, VS_FMT_GUID_YUYV)


      if len(frame_formats) == 0:
        print("device does not support Y16")
        exit(1)

      libuvc.uvc_get_stream_ctrl_format_size(devh, byref(ctrl), UVC_FRAME_FORMAT_Y16,
        frame_formats[0].wWidth, frame_formats[0].wHeight, int(1e7 / frame_formats[0].dwDefaultFrameInterval)
      )
      res = libuvc.uvc_start_streaming(devh, byref(ctrl), PTR_PY_FRAME_CALLBACK, None, 0)
      if res < 0:
        print("uvc_start_streaming failed: {0}".format(res))
        exit(1)
      # res = 0
      try:
        while True:
          data = q.get(True, 500)

          if data is None:
            break
          c_thermal = ktoc(data) # the info will need

          # thermal_array = np.array(c_thermal)

          # thermal_array = numpy_to_image_msg(thermal_array)

          # rospy.loginfo(f"\n ##### Thermal Image ##### {c_thermal.shape}")

          # publish the data

          
          

          if c_thermal.max() > 50.0:
            print("Fire Suspection detected."*100)
            # fireyolo.yolo_inference()
          print(c_thermal.shape) # 120,160
          # print("\n ##### type of c_thermal",type(c_thermal))
          # print(f"Max : {c_thermal.max()}, Min : {c_thermal.min()}")
          max_index = np.argmax(c_thermal)
          max_coords = np.unravel_index(max_index, c_thermal.shape)
          # print(f"Max Coords : {max_coords}")
          # rospy.loginfo(f"\n ##### Thermal Image ##### {np.argmax(c_thermal)}")
          # original code
          # thermal_array.data = [c_thermal.max(), max_coords[1] / 160 , max_coords[0] / 120] # max_temp, x, y
          # full map
          # rospy.loginfo(f"\n ##### Thermal Image ##### {c_thermal}")
          thermal_array.data = c_thermal.flatten().tolist() # max_temp, x, y

          # rospy.loginfo(f"\n ##### Thermal Image ##### {thermal_array}")

          # publish thermal_array
          pub.publish(thermal_array)



        ############for visualization############
          if vis:
            # data = cv2.resize(data[:,:], (640, 480))
            data = cv2.resize(data[:,:], (160, 120))

            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
            img = raw_to_8bit(data)
            display_temperature(img, minVal, minLoc, (255, 0, 0))
            display_temperature(img, maxVal, maxLoc, (0, 0, 255))
            cv2.imshow('Lepton Radiometry', img)
        ############for visualization############
          if cv2.waitKey(1) & 0xFF == ord('q'):
            break

          # pub.publish(thermal_array)
          
        cv2.destroyAllWindows()
      finally:
        libuvc.uvc_stop_streaming(devh)

      print("done")
    finally:
      libuvc.uvc_unref_device(dev)
  finally:
    libuvc.uvc_exit(ctx)

if __name__ == '__main__':
  #to see the visualization : vis = True
  vis = True
  main(vis = vis)
