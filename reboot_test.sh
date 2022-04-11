#!/bin/bash

i=10000
run=0

while [ $i -ge 1 ]
do
  echo 'running' $run 'times'
  cd /opt/updater/denny/deploy/modules/camera_pipeline/scripts/
  sh run_camera.sh &
  sleep 60
  slay -s2 mfrlaunch
  sleep 50
  ((i--))
  ((run++))
done
