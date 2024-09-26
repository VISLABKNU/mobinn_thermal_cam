#!/bin/bash

#PYTHON_SCRIPT_PATH="/home/mobinn/catkin_ws/src/pure_thermal/scripts/uvc-radiometry.py"
PYTHON_SCRIPT_PATH="/home/mobinn/catkin_ws/src/mobinn_thermal_cam/scripts/uvc-radiometry.py"
echo "1" | sudo -S -E python3 "$PYTHON_SCRIPT_PATH"
