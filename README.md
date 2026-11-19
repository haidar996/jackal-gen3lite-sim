# Jackal J100 + Kinova Gen3 lite simulation (ROS 2 Jazzy, Gazebo Harmonic)

Clearpath Jackal J100 with a Kinova Gen3 lite 6-DOF arm and 2-finger gripper, simulated in Gazebo (gz Harmonic)
and visualised in RViz, using Clearpath's official stack driven by `config/robot.yaml`. Namespace: `j100_0001`.

## Requirements
- Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic
- Clearpath packages (clearpath_gz, clearpath_config, clearpath_viz, clearpath_manipulators(_description)), kortex_description, MoveIt

## Install
    bash scripts/install_deps.sh     # needs sudo

## Usage
    scripts/launch_sim.sh            # Gazebo (empty world); args pass through, e.g. world:=warehouse headless:=true rviz:=true
    scripts/launch_rviz.sh           # RViz (second terminal)
    ros2 launch clearpath_manipulators moveit.launch.py setup_path:=$PWD/config/ use_sim_time:=true   # optional MoveIt

Generated files (URDF, SRDF, controller yamls) are written into `config/` on every launch (gitignored).

## Keyboard teleop (base + arm via MoveIt Servo + gripper)
Colcon workspace in `src/` (package `jackal_gen3lite_teleop`). Build once, then run in three terminals:

    scripts/build.sh                    # colcon build --symlink-install
    scripts/launch_sim.sh               # 1. sim (add headless:=true if no GUI)
    scripts/launch_servo.sh             # 2. MoveIt Servo (servo_node, ns j100_0001; no move_group needed)
    scripts/teleop_keyboard.sh          # 3. keyboard node, run in a real terminal (raw key reading)

| Key | Action |
|---|---|
| Up / Down | base forward / backward (0.5 m/s) |
| Left / Right | base rotate left / right (1.0 rad/s) |
| Space | stop base and arm |
| W / X | EE up / down (+z / -z) |
| A / D | EE left / right (+y / -y) |
| Q / E | EE forward / backward (+x / -x) |
| O / C | gripper open (0.0) / close (0.8) |
| R | arm back to ready pose (also done automatically at teleop start; the straight-up spawn pose is singular for Servo) |
| H, Ctrl-C / ESC | help, quit |

Keys act while held (terminal key-repeat); motion stops ~0.4 s after the last press. Arm twists are in
`arm_0_base_link` (same orientation as `base_link`, so +x = robot forward), 0.08 m/s. Parameters, e.g.
`scripts/teleop_keyboard.sh -p linear_speed:=0.3 -p angular_speed:=0.8 -p arm_linear_speed:=0.05 -p key_timeout:=0.4`
(topic/action names are parameters too). Servo config: `src/jackal_gen3lite_teleop/config/servo.yaml`.

## Quick tests
    source /opt/ros/jazzy/setup.bash
    ros2 control list_controllers -c /j100_0001/controller_manager
    # drive base (TwistStamped!)
    ros2 topic pub -r 10 /j100_0001/cmd_vel geometry_msgs/msg/TwistStamped "{twist: {linear: {x: 0.3}}}"
    # move arm
    ros2 action send_goal /j100_0001/arm_0_joint_trajectory_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory \
      "{trajectory: {joint_names: [arm_0_joint_1,arm_0_joint_2,arm_0_joint_3,arm_0_joint_4,arm_0_joint_5,arm_0_joint_6], points: [{positions: [0.5,0.3,0.5,0,0.5,0], time_from_start: {sec: 3}}]}}"
    # gripper
    ros2 action send_goal /j100_0001/arm_0_gripper_controller/gripper_cmd control_msgs/action/GripperCommand "{command: {position: 0.5, max_effort: 10.0}}"

Joint states are on `/j100_0001/platform/joint_states` (arm + gripper + wheels); TF on `/j100_0001/tf`.

## Layout
    config/robot.yaml    robot definition (source of truth)
    scripts/             install_deps.sh, launch_sim.sh, launch_rviz.sh, build.sh, launch_servo.sh, teleop_keyboard.sh
    src/jackal_gen3lite_teleop/   keyboard_teleop node, servo.yaml, servo.launch.py (colcon package)
    docs/troubleshooting.md

## Demo videos
Recorded on a virtual display (Xvfb) while the robot is driven by the keyboard teleop with real keystrokes:
- [docs/demo_gazebo.mp4](docs/demo_gazebo.mp4): Gazebo 3D view following the robot
- [docs/demo_rviz.mp4](docs/demo_rviz.mp4): RViz view (fixed frame `odom`, RobotModel + TF), config in `src/jackal_gen3lite_teleop/rviz/demo.rviz`
