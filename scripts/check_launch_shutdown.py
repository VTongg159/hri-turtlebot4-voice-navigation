#!/usr/bin/env python3
"""Stop ONLY this workspace's active full launcher and verify its Gazebo server exits."""

from pathlib import Path
import json
import argparse
import os
import signal
import time

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="evidence/launch_shutdown.json")
args = parser.parse_args()
launchers = []
servers = []
for proc in Path("/proc").glob("[0-9]*"):
    try:
        a = (proc / "cmdline").read_bytes().decode().split("\0")
        comm = (proc / "comm").read_text().strip()
    except (OSError, UnicodeError):
        continue
    if not a or "bash" in a[0]:
        continue
    if all(v in a for v in ["launch", "tb4_voice_navigation", "voice_navigation.launch.py"]):
        launchers.append(int(proc.name))
    if (
        comm == "ruby"
        and any(
            "/worlds/" + name in " ".join(a) for name in ["semantic_campus.sdf", "pairs_lab.sdf"]
        )
        and "-s" in " ".join(a)
    ):
        servers.append(int(proc.name))
if len(launchers) != 1 or len(servers) != 1:
    raise SystemExit(f"Expected one own launcher/server: {launchers}/{servers}")
start = time.monotonic()
os.kill(launchers[0], signal.SIGINT)


def active(pid):
    try:
        # An exited zombie process cannot publish simulation data.
        return (Path(f"/proc/{pid}") / "stat").read_text().split(") ", 1)[1].split()[0] != "Z"
    except OSError:
        return False


while time.monotonic() - start < 12 and any(active(p) for p in servers):
    time.sleep(0.1)
result = dict(
    test="full_launch_Gazebo_shutdown",
    passed=not any(active(p) for p in servers),
    launcher_pids=launchers,
    server_pids=servers,
    elapsed_s=round(time.monotonic() - start, 2),
)
Path(args.output).write_text(json.dumps(result, indent=2))
print(result, flush=True)
assert result["passed"]
