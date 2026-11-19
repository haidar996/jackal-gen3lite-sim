#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/install/setup.bash"
exec ros2 run jackal_gen3lite_teleop keyboard_teleop --ros-args -p use_sim_time:=true "$@"
