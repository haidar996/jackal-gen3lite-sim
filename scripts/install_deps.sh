#!/usr/bin/env bash
set -e
sudo apt update
sudo apt install -y \
  ros-jazzy-clearpath-simulator \
  ros-jazzy-clearpath-common \
  ros-jazzy-clearpath-config \
  ros-jazzy-clearpath-manipulators-description \
  ros-jazzy-clearpath-desktop \
  ros-jazzy-kortex-description \
  ros-jazzy-robotiq-description \
  ros-jazzy-moveit \
  ros-jazzy-moveit-servo
echo "Done. Now run: source /opt/ros/jazzy/setup.bash"
