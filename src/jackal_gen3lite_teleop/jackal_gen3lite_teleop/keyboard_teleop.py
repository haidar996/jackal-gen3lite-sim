#!/usr/bin/env python3
import os
import select
import sys
import termios
import time
import tty

import rclpy
from rclpy.signals import SignalHandlerOptions
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory, GripperCommand
from geometry_msgs.msg import TwistStamped
from moveit_msgs.srv import ServoCommandType
from rclpy.action import ActionClient
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectoryPoint

ARM_JOINTS = [
    'arm_0_joint_1',
    'arm_0_joint_2',
    'arm_0_joint_3',
    'arm_0_joint_4',
    'arm_0_joint_5',
    'arm_0_joint_6',
]

READY_POSE = [0.0, 0.6, 1.8, 0.0, 0.9, 0.0]

HELP = """
Jackal + Gen3 lite keyboard teleop   (hold a key; releasing stops after a short timeout)
---------------------------------------------------------------
 Base:     Up/Down = forward/backward   Left/Right = rotate left/right   Space = stop
 Arm EE:   W/X = up/down (+z/-z)   A/D = left/right (+y/-y)   Q/E = forward/backward (+x/-x)
 Gripper:  O = open   C = close
 Other:    R = arm to ready pose   H = help   Ctrl-C or ESC = quit
 (arm starts straight up = singular for Servo, so it is moved to the ready pose at startup)
---------------------------------------------------------------
"""

ARROW_KEYS = {
    '\x1b[A': (1.0, 0.0),
    '\x1b[B': (-1.0, 0.0),
    '\x1b[D': (0.0, 1.0),
    '\x1b[C': (0.0, -1.0),
    '\x1bOA': (1.0, 0.0),
    '\x1bOB': (-1.0, 0.0),
    '\x1bOD': (0.0, 1.0),
    '\x1bOC': (0.0, -1.0),
}

ARM_KEYS = {
    'w': (0, 0, 1),
    'x': (0, 0, -1),
    'a': (0, 1, 0),
    'd': (0, -1, 0),
    'q': (1, 0, 0),
    'e': (-1, 0, 0),
}

NO_MOTION = (0, 0, 0)
SERVO_SETTLE_TIME = 1.0


def map_key(key):
    if key in ARROW_KEYS:
        return ('base',) + ARROW_KEYS[key]
    lower = key.lower()
    if lower in ARM_KEYS:
        return ('arm',) + ARM_KEYS[lower]
    if lower == 'o':
        return ('grip', 'open')
    if lower == 'c':
        return ('grip', 'close')
    if lower == 'h':
        return ('help',)
    if lower == 'r':
        return ('ready',)
    if key == ' ':
        return ('stop',)
    if key == '\x03' or key == '\x1b':
        return ('quit',)
    return None


def split_keys(text):
    keys = []
    i = 0
    while i < len(text):
        is_arrow = text[i] == '\x1b' and i + 2 < len(text) and text[i + 1] in '[O'
        if is_arrow:
            keys.append(text[i:i + 3])
            i += 3
        else:
            keys.append(text[i])
            i += 1
    return keys


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        ns = '/j100_0001'
        self.declare_parameter('base_topic', ns + '/cmd_vel')
        self.declare_parameter('servo_twist_topic', ns + '/servo_node/delta_twist_cmds')
        self.declare_parameter('servo_switch_service', ns + '/servo_node/switch_command_type')
        self.declare_parameter('gripper_action', ns + '/arm_0_gripper_controller/gripper_cmd')
        self.declare_parameter(
            'arm_traj_action', ns + '/arm_0_joint_trajectory_controller/follow_joint_trajectory')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('arm_frame', 'arm_0_base_link')
        self.declare_parameter('linear_speed', 0.5)
        self.declare_parameter('angular_speed', 1.0)
        self.declare_parameter('arm_linear_speed', 0.08)
        self.declare_parameter('rate', 20.0)
        self.declare_parameter('key_timeout', 0.4)
        self.declare_parameter('gripper_open', 0.0)
        self.declare_parameter('gripper_close', 0.8)
        self.declare_parameter('gripper_effort', 10.0)

        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.arm_speed = self.get_parameter('arm_linear_speed').value
        self.key_timeout = self.get_parameter('key_timeout').value
        self.base_frame = self.get_parameter('base_frame').value
        self.arm_frame = self.get_parameter('arm_frame').value
        self.gripper_effort = self.get_parameter('gripper_effort').value
        self.gripper_positions = {
            'open': self.get_parameter('gripper_open').value,
            'close': self.get_parameter('gripper_close').value,
        }

        base_topic = self.get_parameter('base_topic').value
        arm_topic = self.get_parameter('servo_twist_topic').value
        self.base_publisher = self.create_publisher(TwistStamped, base_topic, 10)
        self.arm_publisher = self.create_publisher(TwistStamped, arm_topic, 10)

        gripper_action = self.get_parameter('gripper_action').value
        arm_action = self.get_parameter('arm_traj_action').value
        switch_service = self.get_parameter('servo_switch_service').value
        self.gripper_client = ActionClient(self, GripperCommand, gripper_action)
        self.arm_client = ActionClient(self, FollowJointTrajectory, arm_action)
        self.switch_client = self.create_client(ServoCommandType, switch_service)

        self.base_command = (0.0, 0.0)
        self.base_time = 0.0
        self.arm_command = NO_MOTION
        self.arm_time = 0.0
        self.arm_was_active = False
        self.arm_last_publish = 0.0
        self.ready_pending = False

        self.twist_mode_ready = False
        self.twist_mode_future = None
        self.twist_mode_time = 0.0

        rate = self.get_parameter('rate').value
        self.create_timer(1.0 / rate, self.tick)

    def go_to_ready_pose(self, wait=False):
        timeout = 3.0 if wait else 0.1
        if not self.arm_client.wait_for_server(timeout_sec=timeout):
            self.get_logger().warn('arm trajectory action not available')
            return

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ARM_JOINTS
        point = JointTrajectoryPoint()
        point.positions = READY_POSE
        point.time_from_start = Duration(sec=3)
        goal.trajectory.points = [point]

        send_future = self.arm_client.send_goal_async(goal)
        if not wait:
            return

        rclpy.spin_until_future_complete(self, send_future, timeout_sec=3.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=6.0)

    def update_twist_mode(self):
        if self.twist_mode_ready:
            if not self.switch_client.service_is_ready():
                self.twist_mode_ready = False
            return

        if self.twist_mode_future is not None:
            if not self.twist_mode_future.done():
                return
            response = self.twist_mode_future.result()
            self.twist_mode_future = None
            if response is not None and response.success:
                self.twist_mode_ready = True
                return

        if time.monotonic() - self.twist_mode_time < 1.0:
            return
        if not self.switch_client.service_is_ready():
            return

        self.twist_mode_time = time.monotonic()
        request = ServoCommandType.Request()
        request.command_type = ServoCommandType.Request.TWIST
        self.twist_mode_future = self.switch_client.call_async(request)

    def handle_action(self, action, now):
        kind = action[0]
        if kind == 'base':
            self.base_command = (action[1], action[2])
            self.base_time = now
        elif kind == 'arm':
            self.arm_command = action[1:]
            self.arm_time = now
        elif kind == 'stop':
            self.base_command = (0.0, 0.0)
            self.arm_command = NO_MOTION
        elif kind == 'grip':
            self.send_gripper(action[1])
        elif kind == 'ready':
            self.arm_command = NO_MOTION
            self.ready_pending = True
        elif kind == 'help':
            print(HELP.replace('\n', '\r\n'), end='', flush=True)

    def send_gripper(self, which):
        if not self.gripper_client.server_is_ready():
            self.get_logger().warn('gripper action server not available')
            return
        goal = GripperCommand.Goal()
        goal.command.position = float(self.gripper_positions[which])
        goal.command.max_effort = float(self.gripper_effort)
        self.gripper_client.send_goal_async(goal)

    def publish_base(self, stamp, now):
        linear, angular = (0.0, 0.0)
        if now - self.base_time < self.key_timeout:
            linear, angular = self.base_command

        msg = TwistStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = self.base_frame
        msg.twist.linear.x = linear * self.linear_speed
        msg.twist.angular.z = angular * self.angular_speed
        self.base_publisher.publish(msg)

    def publish_arm(self, stamp, now):
        direction = NO_MOTION
        if now - self.arm_time < self.key_timeout:
            direction = self.arm_command

        active = direction != NO_MOTION
        if not active and not self.arm_was_active:
            return
        self.arm_was_active = active

        msg = TwistStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = self.arm_frame
        msg.twist.linear.x = direction[0] * self.arm_speed
        msg.twist.linear.y = direction[1] * self.arm_speed
        msg.twist.linear.z = direction[2] * self.arm_speed
        self.arm_publisher.publish(msg)
        self.arm_last_publish = now

    def tick(self):
        now = time.monotonic()
        stamp = self.get_clock().now().to_msg()
        self.publish_base(stamp, now)
        self.update_twist_mode()
        self.publish_arm(stamp, now)
        self.send_pending_ready_pose(now)

    def send_pending_ready_pose(self, now):
        if not self.ready_pending:
            return
        if self.arm_was_active or now - self.arm_last_publish < SERVO_SETTLE_TIME:
            return
        self.ready_pending = False
        self.go_to_ready_pose()

    def stop_everything(self):
        for _ in range(3):
            self.base_command = (0.0, 0.0)
            self.arm_command = NO_MOTION
            self.tick()


def read_keys(fd, wait):
    ready, _, _ = select.select([sys.stdin], [], [], wait)
    if not ready:
        return ''
    return os.read(fd, 64).decode(errors='ignore')


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = KeyboardTeleop()
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        print('Moving arm to ready pose...', flush=True)
        node.go_to_ready_pose(wait=True)
        node.update_twist_mode()
        print(HELP)
        tty.setcbreak(fd)
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            text = read_keys(fd, 0.01)
            if text == '\x1b':
                break
            for key in split_keys(text):
                action = map_key(key)
                if action is None:
                    continue
                if action[0] == 'quit':
                    raise KeyboardInterrupt
                node.handle_action(action, time.monotonic())
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        try:
            node.stop_everything()
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print('\nbye')


if __name__ == '__main__':
    main()
