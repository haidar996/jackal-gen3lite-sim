import os

import xacro
import yaml
from ament_index_python.packages import get_package_share_directory
from clearpath_config.clearpath_config import ClearpathConfig
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def launch_setup(context, *args, **kwargs):
    setup_path = LaunchConfiguration('setup_path').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context) == 'true'
    namespace = ClearpathConfig(os.path.join(setup_path, 'robot.yaml')).get_namespace()

    urdf_path = os.path.join(setup_path, 'robot.urdf.xacro')
    srdf_path = os.path.join(setup_path, 'robot.srdf')
    robot_description = {'robot_description': xacro.process_file(urdf_path).toxml()}
    robot_description_semantic = {'robot_description_semantic': xacro.process_file(srdf_path).toxml()}

    moveit_path = os.path.join(setup_path, 'manipulators', 'config', 'moveit.yaml')
    move_group_params = load_yaml(moveit_path)[namespace]['move_group']['ros__parameters']
    kinematics = {'robot_description_kinematics': move_group_params['robot_description_kinematics']}
    limits = {'robot_description_planning': move_group_params['robot_description_planning']}

    package_dir = get_package_share_directory('jackal_gen3lite_teleop')
    servo_params = {'moveit_servo': load_yaml(os.path.join(package_dir, 'config', 'servo.yaml'))}

    servo_node = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        namespace=namespace,
        output='screen',
        parameters=[
            servo_params,
            robot_description,
            robot_description_semantic,
            kinematics,
            limits,
            {'use_sim_time': use_sim_time},
        ],
        remappings=[
            ('/tf', 'tf'),
            ('/tf_static', 'tf_static'),
            ('joint_states', 'platform/joint_states'),
        ],
    )
    return [servo_node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('setup_path', default_value='/etc/clearpath/'),
        DeclareLaunchArgument('use_sim_time', default_value='true', choices=['true', 'false']),
        OpaqueFunction(function=launch_setup),
    ])
