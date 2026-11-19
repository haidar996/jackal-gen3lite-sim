#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec ros2 launch clearpath_gz simulation.launch.py \
  setup_path:="$ROOT/config/" world:=empty "$@"
