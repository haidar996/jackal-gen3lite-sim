#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
colcon build --symlink-install "$@"
