#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
exec ros2 launch clearpath_viz view_robot.launch.py namespace:=j100_0001 use_sim_time:=true "$@"
