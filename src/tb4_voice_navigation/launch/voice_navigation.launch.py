"""Voice pipeline; optionally bring up the furnished campus simulation."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare("tb4_voice_navigation")
    regions = LaunchConfiguration("regions_file")
    shared = {
        "regions_file": regions,
        "use_sim_time": ParameterValue(LaunchConfiguration("use_sim_time"), value_type=bool),
    }
    voice_config = PathJoinSubstitution([pkg, "config", "voice_config.yaml"])
    return LaunchDescription(
        [
            DeclareLaunchArgument("start_sim", default_value="false"),
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("enable_asr", default_value="true"),
            DeclareLaunchArgument(
                "regions_file",
                default_value=PathJoinSubstitution([pkg, "config", "pairs_regions.yaml"]),
            ),
            DeclareLaunchArgument("model", default_value="small"),
            DeclareLaunchArgument("audio_device", default_value="default"),
            DeclareLaunchArgument("goal_timeout", default_value="180.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([pkg, "launch", "baseline.launch.py"])
                ),
                condition=IfCondition(LaunchConfiguration("start_sim")),
                launch_arguments={"headless": LaunchConfiguration("headless")}.items(),
            ),
            Node(
                package="tb4_voice_navigation",
                executable="command_parser_node",
                parameters=[shared],
                output="screen",
            ),
            Node(
                package="tb4_voice_navigation",
                executable="voice_navigation_node",
                parameters=[
                    voice_config,
                    shared,
                    {
                        "goal_timeout": ParameterValue(
                            LaunchConfiguration("goal_timeout"), value_type=float
                        )
                    },
                ],
                output="screen",
            ),
            Node(
                package="tb4_voice_navigation",
                executable="region_visualization_node",
                parameters=[shared],
                output="screen",
            ),
            Node(
                package="tb4_voice_navigation",
                executable="voice_recognition_node",
                condition=IfCondition(LaunchConfiguration("enable_asr")),
                parameters=[
                    voice_config,
                    {
                        "model": LaunchConfiguration("model"),
                        "audio_device": LaunchConfiguration("audio_device"),
                    },
                ],
                output="screen",
            ),
        ]
    )
