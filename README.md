# PAIRS Lab Voice Navigation

A ROS 2 Jazzy project for Vietnamese voice commands, semantic map segmentation,
and TurtleBot 4 navigation in Gazebo Harmonic.

The 28 × 20 m lab has six regions: UAV (A), manipulation (B), lobby (C),
HRI / Unitree G1 (D), quadrupeds / Unitree Go2 (E), and TurtleBot (F).
The exhibit robots are static; a separate TurtleBot 4 moves with Nav2.

## Setup

Use Ubuntu 24.04 with ROS 2 Jazzy and Gazebo Harmonic installed.
Run these commands from the repository root:

```bash
source /opt/ros/jazzy/setup.bash
sudo apt install python3-venv python3-colcon-common-extensions python3-rosdep alsa-utils
rosdep update
rosdep install --from-paths src --ignore-src -r -y

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements-asr.txt
python scripts/download_model.py --model small
python -m colcon build --base-paths src --symlink-install
source install/setup.bash
```

Whisper runs locally on CPU with int8 inference. Download the model once before
launching; subsequent runs use the local cache.

## Run

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source install/setup.bash
export ROS_DOMAIN_ID=19
ros2 launch tb4_voice_navigation voice_navigation.launch.py start_sim:=true
```

In another terminal, source the same environment and set the same domain:

```bash
ros2 run tb4_voice_navigation push_to_talk
```

Wait for `MODEL_READY`. Press Enter to record, speak, then press Enter to stop.
Each recording is limited to 12 seconds. Example commands:

- `Đi đến phòng UAV` — go to A.
- `Đi từ khu vực A đến khu vực B` — visit A, then B, from the current position.
- `Đi từ A qua C đến D` — visit A, C, and D in order.
- `Dừng lại` — cancel the current mission.

Unknown regions are rejected. Wait for the current mission to finish before
issuing another destination command. For typed input, run
`ros2 run tb4_voice_navigation keyboard_command`.

```bash
# Navigation status
ros2 topic echo /voice/navigation_status --qos-durability transient_local

# Immediate cancellation
ros2 service call /voice/cancel std_srvs/srv/Trigger '{}'
```

Use `enable_asr:=false` to launch without speech recognition. Use
`ros2 launch tb4_voice_navigation baseline.launch.py` for Gazebo, RViz, and Nav2
alone. Start only one simulation and navigation pipeline per ROS domain.

## Maps and scene

Runtime files live in `src/tb4_voice_navigation/`:

- `config/pairs_regions.yaml`: region polygons, aliases, and validated goals.
- `maps/pairs_lab.{pgm,yaml}`: occupancy grid, 0.05 m/cell.
- `worlds/pairs_lab.sdf` and `models/`: scene and bundled assets.
- `config/voice_config.yaml`: recording, preprocessing, and ASR settings.

Segmentation uses supervised polygons intersected with free cells. The map is
derived from world collision geometry. Goals must be in free, reachable cells
with sufficient clearance; Nav2 performs runtime path checks.

```bash
# Edit region polygons and goals
ros2 run tb4_voice_navigation map_segmentation \
  src/tb4_voice_navigation/config/pairs_regions.yaml --edit

# Change the Gazebo camera
python scripts/pairslab_camera.py overview
```

The spawn pose is `(-11, 0, 0)` in the map frame. AMCL initializes it on launch.
`scripts/initialize_localization.py --fresh-spawn` is only for a robot still at
that spawn pose.

## Development

```bash
python -m pip install -r requirements-dev.txt
ruff check src/tb4_voice_navigation scripts
ruff format --check src/tb4_voice_navigation scripts
python -m colcon test --packages-select tb4_voice_navigation
colcon test-result --verbose
```

Optional scene authoring tools are listed in `requirements-scene.txt`.
The generators in `src/tb4_voice_navigation/scripts/` rebuild assets and scene
files; revalidate goals after changing geometry.

## License

Original code is licensed under Apache-2.0. Third-party assets retain their own
licenses; see [ASSETS.md](ASSETS.md), [NOTICE](NOTICE), and the license files
under `src/tb4_voice_navigation/models/`.
