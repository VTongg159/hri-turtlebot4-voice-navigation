"""Campus/TB4/Nav2 baseline, loading the already-generated SDF without temp-file races."""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess,
    AppendEnvironmentVariable,
)
from launch.conditions import UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare("tb4_voice_navigation")
    desc = FindPackageShare("nav2_minimal_tb4_description")
    model = PathJoinSubstitution([desc, "urdf", "standard", "turtlebot4.urdf.xacro"])
    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            AppendEnvironmentVariable(
                "GZ_SIM_RESOURCE_PATH", PathJoinSubstitution([pkg, "models"])
            ),
            # World is a plain SDF generated offline. No xacro process/temp file here.
            ExecuteProcess(
                cmd=[
                    "gz",
                    "sim",
                    "-r",
                    "-s",
                    PathJoinSubstitution([pkg, "worlds", "pairs_lab.sdf"]),
                ],
                output="screen",
                sigterm_timeout="2",
                sigkill_timeout="2",
            ),
            ExecuteProcess(
                cmd=[
                    "gz",
                    "sim",
                    "-g",
                    "--gui-config",
                    PathJoinSubstitution([pkg, "config", "pairs_lab_gui.config"]),
                ],
                condition=UnlessCondition(LaunchConfiguration("headless")),
                output="screen",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                output="screen",
                parameters=[
                    {
                        "use_sim_time": True,
                        "robot_description": ParameterValue(
                            Command(["xacro", " ", model]), value_type=str
                        ),
                    }
                ],
                remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("nav2_minimal_tb4_sim"), "launch", "spawn_tb4.launch.py"]
                    )
                ),
                launch_arguments={
                    "use_sim_time": "true",
                    "robot_name": "nav2_turtlebot4",
                    "x_pose": "-11.0",
                    "y_pose": "0.0",
                    "z_pose": "0.01",
                    "yaw": "0.0",
                }.items(),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", PathJoinSubstitution([pkg, "rviz", "pairs_lab.rviz"])],
                parameters=[{"use_sim_time": True}],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("nav2_bringup"), "launch", "bringup_launch.py"]
                    )
                ),
                launch_arguments={
                    "map": PathJoinSubstitution([pkg, "maps", "pairs_lab.yaml"]),
                    "params_file": PathJoinSubstitution([pkg, "config", "pairs_nav2_params.yaml"]),
                    "use_sim_time": "true",
                    "use_composition": "False",
                    "autostart": "true",
                }.items(),
            ),
        ]
    )
