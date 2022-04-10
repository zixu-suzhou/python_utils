#!/bin/bash

i=2

while [ $i -ge 1 ]
do
  cd /opt/updater/denny/deploy/modules/camera_pipeline/scripts/
  sh run_camera.sh &
  sleep 180
  slay -s2 mfrlaunch
  sleep 120
  ((i--))
done
