#!/usr/bin/env bash
set -e
trial_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$trial_root"
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source install/setup.bash
export ROS_DOMAIN_ID=19
mkdir -p evidence/voice_demo/pairslab_live
script -q -f -e -c '.venv/bin/python -u scripts/live_voice_trial.py' evidence/voice_demo/pairslab_live/terminal.log
