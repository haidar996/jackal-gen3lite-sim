# Troubleshooting / notes

- **Default world `warehouse` is slow**: it downloads many models from Fuel on first launch (internet needed), and the
  controller spawners time out ("Failed to acquire lock") until the world finishes loading. `launch_sim.sh` defaults to `world:=empty`.
- **cmd_vel is `geometry_msgs/TwistStamped`** (Jazzy), topic `/j100_0001/cmd_vel`. Plain Twist is ignored.
- **No `/j100_0001/joint_states`**: joint states are on `/j100_0001/platform/joint_states`.
- **`Couldn't open joystick /dev/input/ps4`** error: harmless, no gamepad attached. Remove `controller: ps4` from robot.yaml to silence.
- **IMU "free fall" warnings** at start: harmless (robot spawns at z=0.3 and drops).
- **MoveIt** (`clearpath_manipulators moveit.launch.py`): starts and connects to the trajectory controller. Logs
  `Group 'arm_0_gripper' is not a chain` and `No 3D sensor plugin(s)` errors: benign. move_group may segfault on Ctrl-C shutdown.
- **Gripper action controller deprecation warning**: upstream, harmless.
- Links without collision geometry (fenders, gps) warn in the MoveIt collision updater: harmless.
- Killing processes: do not run `pkill -f` with a pattern that appears in your own shell command line (it kills the shell).
  Use bracket tricks: `pkill -f "[r]os2 launch"; pkill -f "[g]z sim"; pkill -f "[r]uby"`.
- **Teleop / Servo** (needs `ros-jazzy-moveit-servo`): start order sim -> `launch_servo.sh` -> `teleop_keyboard.sh`. The teleop node calls
  servo's `switch_command_type` (TWIST) at startup; if servo is not up it only warns and the arm keys do nothing.
- Servo logs `Detected jump back in time. Clearing TF buffer` repeatedly (sim-time TF): harmless.
- Keyboard node must run in a real terminal (it needs a tty); it restores terminal settings on exit. If the terminal is left odd, run `reset`.
- Arm twist frame is `arm_0_base_link` (identity rotation to `base_link`). Gripper joint range is -0.1..0.96 rad; open=0.0, close=0.8 (params `gripper_open/close`).
- Servo drives the arm via the `arm_0_joint_trajectory_controller/joint_trajectory` topic; it can conflict with MoveIt/action goals if both are active at once.
- Python-node gotcha (fixed): do not name a Node method `handle` (shadows rclpy internals).

## Arm does not respond to W/X/A/D/Q/E (fixed 2026-11-19)
Symptoms: Servo status `Very close to a singularity, emergency stop`, arm frozen.
Causes and fixes:
1. The arm spawns at all-zeros (straight up) = kinematic singularity. Teleop now moves the arm to
   `READY_POSE` (`[0, 0.6, 1.8, 0, 0.9, 0]`) at startup; press **R** to return to it anytime.
2. Default Servo singularity thresholds (17/30) are too tight for the small Gen3 lite; raised to
   100/200 in `config/servo.yaml`.
3. Servo starts in JOINT_JOG mode; teleop now retries `switch_command_type` (TWIST) until Servo confirms,
   so start order no longer matters.
4. Teleop used to stream zero twists constantly, which kept Servo publishing "hold" trajectories and
   overrode trajectory goals. It now only publishes while an arm key is held.
Diagnose: `ros2 topic echo /j100_0001/servo_node/status`.
