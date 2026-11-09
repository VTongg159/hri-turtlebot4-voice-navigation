from glob import glob
from pathlib import Path
from setuptools import setup

package = "tb4_voice_navigation"
setup(
    name=package,
    version="0.1.0",
    packages=[package],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package]),
        ("share/" + package, ["package.xml"]),
    ]
    + [
        ("share/" + package + "/" + folder, [p for p in glob(folder + "/*") if Path(p).is_file()])
        for folder in ["config", "maps", "launch", "worlds", "rviz"]
    ]
    + [
        ("share/" + package + "/" + str(path.parent), [str(path)])
        for path in Path("models").rglob("*")
        if path.is_file()
    ],
    install_requires=["setuptools", "numpy", "PyYAML"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="HRI Lab",
    maintainer_email="hri@example.com",
    description="Vietnamese voice navigation with validated semantic maps for Jazzy",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "map_segmentation = tb4_voice_navigation.map_segmentation:main",
            "command_parser_node = tb4_voice_navigation.command_parser_node:main",
            "voice_navigation_node = tb4_voice_navigation.voice_navigation_node:main",
            "region_visualization_node = tb4_voice_navigation.region_visualization_node:main",
            "voice_recognition_node = tb4_voice_navigation.voice_recognition_node:main",
            "keyboard_command = tb4_voice_navigation.keyboard_command:main",
            "push_to_talk = tb4_voice_navigation.push_to_talk:main",
        ]
    },
)
