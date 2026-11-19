#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/install/setup.bash"
exec ros2 launch jackal_gen3lite_teleop servo.launch.py setup_path:="$ROOT/config/" use_sim_time:=true "$@"
