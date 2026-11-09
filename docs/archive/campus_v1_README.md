# Bài 7 — Phân vùng bản đồ và điều hướng bằng giọng nói tiếng Việt

Ubuntu 24.04 · ROS 2 Jazzy · Gazebo Harmonic · TurtleBot 4 tối giản từ Nav2.
Workspace độc lập, giữ nguyên tuần 4/5. Bản đồ Semantic Campus: 4 phòng có nội thất + hành lang, 14 × 10 m, 5 vùng A–E.

![Gazebo thật](docs/gazebo_campus.png)
![Phân vùng](docs/segmented_campus.png)

## Trạng thái nghiệm thu

**Đã triển khai:** map trinary/semantic, polygon editor, goal có clearance/connectivity, Whisper local tiếng Việt push-to-talk, parser rule-based, action client Nav2 tuần tự, busy/cancel/timeout, preflight path, TF/AMCL validation, markers RViz, launch tích hợp, keyboard test và kiểm thử lỗi thật.

**Đã kiểm chứng:** 71 unit tests; pipeline transcript bàn phím → parser → Nav2 thật chạy A→C→B, A→B, semantic alias và bỏ qua nguồn đã ở gần; từ chối busy; cancel có terminal status=5; thiếu Nav2/TF; thiếu microphone qua lỗi ALSA thật. Vật cản collision thật chặn phòng A làm Nav2 abort status=6/error=208; controller FAILED, không gửi waypoint C. Xem `docs/phase_status.md` và `evidence/` để phân biệt từng loại test.

**Chưa nghiệm thu:** ba câu nói tiếng Việt từ người thật và T15 microphone → ASR → Nav2 end-to-end. Người dùng chưa thể thử microphone trong phiên làm việc. Model đã tải/nạp thật; VAD trên tín hiệu silence tổng hợp cho transcript rỗng, điều đó không thay thế thử giọng nói thật. Không có video demo voice được dựng hoặc kết quả ASR giả.

## Cài đặt và build

Chạy từ thư mục gốc workspace này. Mở terminal ROS sạch, tránh source chồng workspace tuần cũ.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=19
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements-asr.txt
python scripts/download_model.py --model small
python -m colcon build --base-paths src --symlink-install --packages-select tb4_voice_navigation
source install/setup.bash
python -m colcon test --packages-select tb4_voice_navigation --event-handlers console_direct+
colcon test-result --verbose
```

Dependencies ROS/hệ thống cần có: `nav2_bringup`, `nav2_minimal_tb4_sim`, `nav2_minimal_tb4_description`, `nav2_simple_commander`, `ros_gz_sim`, `ros_gz_bridge`, `rviz2`, `rclpy`, `tf2_ros_py`, `nav2_msgs`, `geometry_msgs`, `std_msgs`, `std_srvs`, `visualization_msgs`, `sensor_msgs`, `lifecycle_msgs`, OpenCV/NumPy/PyYAML/Matplotlib/pytest, `alsa-utils` (`arecord`). Môi trường này đã có các package đó; không thay đổi package hệ thống. ASR/PDF được cài trong .venv. Thu âm dùng ALSA vì PortAudio không có trên máy; không phụ thuộc sounddevice. Không cần API key, không gửi audio lên dịch vụ ngoài.

**Build bằng Python trong .venv** để entry points có interpreter chứa faster-whisper. .venv dùng system-site-packages để thấy rclpy Jazzy. Không source install cũ sau khi đổi workspace. Model small là đa ngôn ngữ; không dùng small.en. Lần tải đầu cần mạng, khoảng vài trăm MB; node mặc định `local_files_only=true` nên các lần chạy sau offline. Revision model thực tế và packages nằm trong `evidence/whisper_model_revision.txt`, `venv_packages.txt`.

## Chạy toàn hệ thống

Terminal 1, khởi chạy mới từ đầu:

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source install/setup.bash
export ROS_DOMAIN_ID=19
ros2 launch tb4_voice_navigation voice_navigation.launch.py start_sim:=true
```

Terminal 2, chỉ với robot vừa spawn trong campus:

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source install/setup.bash
export ROS_DOMAIN_ID=19
python scripts/initialize_localization.py --fresh-spawn
ros2 run tb4_voice_navigation push_to_talk
```

`initialize_localization.py` chỉ publish initial pose AMCL tại `(-5.5,0,0)` và chờ TF/lifecycle, không teleport hoặc gửi navigation goal. **Không chạy lại ở pose spawn sau khi robot đã di chuyển.** Khi robot đã có pose khác, dùng RViz2 “2D Pose Estimate” đúng vị trí thực. Đây là map mới có tọa độ map=world; không dùng offset tuần 4.

Nếu simulator/Nav2 đã chạy, chỉ chạy pipeline:

```bash
ros2 launch tb4_voice_navigation voice_navigation.launch.py start_sim:=false
```

Không chạy hai pipeline/controller cùng lúc. Launch nạp trực tiếp world SDF có sẵn và quản lý Gazebo server bằng ExecuteProcess, tránh race tạo file tạm và shell process bị bỏ lại. `headless:=true` tắt cửa sổ Gazebo; launch simulator tối giản vẫn mở RViz2. `enable_asr:=false` dành cho kiểm thử bàn phím; đó không phải demo voice.

## Nói lệnh

Đợi log `MODEL_READY` trên `/voice/asr_status`. Trong push-to-talk: Enter bắt đầu ghi → nói → Enter dừng. Ghi âm tự dừng sau 12 giây; VAD/no-speech/logprob/RMS/clipping gates kiểm tra trước khi publish transcript. Khi đang nhận dạng, start mới bị từ chối. Không có microphone hoặc âm thanh không hợp lệ thì node báo lỗi và không publish transcript. Xem status ở terminal khác:

```bash
ros2 topic echo /voice/asr_status --qos-durability transient_local
ros2 topic echo /voice/navigation_status --qos-durability transient_local
```

Các câu hỗ trợ:

- “Đi đến khu vực A.” / “Di chuyển đến phòng học.”
- “Robot đến phòng thí nghiệm.”
- “Đi từ A đến B.” → current → A → B, chỉ bỏ qua A khi đang ở gần A.
- “Đi từ phòng A qua hành lang C rồi đến phòng B.”
- “Đi đến A, sau đó đến B.”
- “Đi đến khu vực Z.” → lỗi UNKNOWN_REGION, không gửi goal.
- “Dừng lại.” / “Hủy điều hướng.” → hủy goal qua action cancellation.

Controller mặc định từ chối lệnh mới khi bận. Có service hủy độc lập với microphone (hữu ích khi ASR/model đang bận):

```bash
ros2 service call /voice/cancel std_srvs/srv/Trigger '{}'
```

Ghi âm qua service thay cho terminal PTT:

```bash
ros2 service call /voice/record/start std_srvs/srv/Trigger '{}'
ros2 service call /voice/record/stop std_srvs/srv/Trigger '{}'
# Bỏ âm thanh vừa thu, không phát transcript:
ros2 service call /voice/record/discard std_srvs/srv/Trigger '{}'
```

Whisper chạy theo từng đoạn sau khi dừng ghi, không phải streaming. Vì vậy lệnh dừng bằng voice có độ trễ ASR và cần một phiên ghi âm mới; service cancel có thể gọi trong khi ASR bận. Nếu gain cao/clipping, chỉnh input gain trong cài đặt âm thanh; `arecord -l`/`arecord -L` giúp chọn thiết bị. Ví dụ `audio_device:=plughw:2,0`; chỉ số card phải kiểm tra lại trên máy dùng thực tế, không giả định cố định. Tham số model/audio_device/goal_timeout/regions_file/use_sim_time được expose trong launch, các ngưỡng khác ở config/voice_config.yaml.

## Bản đồ và vùng

| ID | Tên | Goal map x,y (m) | Yaw (rad) | Clearance (m) |
|---|---|---|---|---|
| A | Phòng học | -3.5, 2.5 | +1.5708 | 1.354 |
| B | Phòng thí nghiệm | 3.5, 2.1 | +1.5708 | 1.028 |
| C | Hành lang | 0, 0 | 0 | 1.065 |
| D | Phòng họp | -3.5, -1.95 | -1.5708 | 0.515 |
| E | Khu nghỉ | 3.4, -2.2 | -1.5708 | 0.991 |

Occupancy `maps/campus.pgm`/`campus.yaml`: 300 × 220 ô, 0.05 m/ô, origin `[-7.5,-5.5,0]`. Sinh từ cùng collision geometry với world, **không phải map SLAM đã quét**. Mặt bàn cao trên chiều cao robot không được tô kín thành tường; chân bàn được raster như collision thật. Unknown không được coi là free, planner `allow_unknown=false`. Vùng là polygon thủ công, nhãn mang ý nghĩa bài tập. Goal phải trong vùng/free, đủ clearance 0.35 m và nối với anchor trên lưới đã loại ô thiếu clearance; runtime vẫn cần planner/costmap thật để xử lý thay đổi môi trường.

```bash
ros2 run tb4_voice_navigation map_segmentation src/tb4_voice_navigation/config/regions.yaml --edit
ros2 run tb4_voice_navigation map_segmentation src/tb4_voice_navigation/config/regions.yaml --output docs/segmented_campus.png
ros2 run tb4_voice_navigation map_segmentation src/tb4_voice_navigation/config/regions.yaml --auto --output docs/watershed_suggestions.npy
```

Editor: chuột trái thêm đỉnh, chuột phải undo; `n` nhập ID/tên/aliases qua terminal và lưu; ID trùng thay thế vùng cũ. `g` nhập goal x/y/yaw để sửa; `q` thoát. Không có goal hợp lệ thì từ chối vùng. Watershed chỉ tạo gợi ý cần duyệt, không bảo đảm tách đúng mọi phòng. Goal tự chọn theo clearance, không mặc định centroid.

```bash
python src/tb4_voice_navigation/scripts/generate_training_world.py
```

Sinh lại asset sau khi sửa hình học; phải kiểm tra lại polygon/goal và chạy lại navigation. Bản đồ cũ còn ở maps/map.pgm/yaml. Muốn tạo map SLAM riêng: chạy simulation + `ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true`, không chạy đồng thời AMCL/map_server; điều khiển robot quét đủ các phòng bằng teleop phù hợp interface thực tế rồi `ros2 run nav2_map_server map_saver_cli -f campus_slam`. SLAM/teleop trên campus mới chưa được kiểm thử trong phiên này; chuyển map mới cần lập lại regions.

## Interface và cấu trúc

| Interface | Kiểu / vai trò |
|---|---|
| /voice/transcript | std_msgs/String; ASR thật hoặc keyboard test |
| /voice/parsed_command | std_msgs/String; JSON type/waypoints/command_id/error |
| /voice/asr_status | std_msgs/String JSON, MODEL_READY/RECORDING/TRANSCRIPT/lỗi |
| /voice/navigation_status | std_msgs/String JSON, state/event/busy/waypoint/action terminal status |
| /semantic_regions/markers | visualization_msgs/MarkerArray; polygon/nhãn/goal/đích đang đi trong map mét |
| /voice/planned_path | nav_msgs/Path thật từ ComputePathToPose |
| /navigate_to_pose | NavigateToPose action, name configurable |
| /compute_path_to_pose | ComputePathToPose action, name configurable |

Markers nối waypoint chỉ biểu thị **thứ tự các đích**, không phải đường robot được phép cắt qua tường. `/voice/planned_path` hiển thị đường planner thật. RViz config đã thêm hai display tương ứng. `/map`, `/scan`, `/odom`, `/tf`, `/tf_static`, `/amcl_pose` đã xác minh thực tế.

Code tại `src/tb4_voice_navigation/tb4_voice_navigation/`; config/maps/worlds/rviz/launch được cài qua setup.py. ASR/model chạy worker riêng để callback start/stop/cancel không bị block bởi inference. Controller gửi từng goal, chỉ tiếp tục khi terminal action SUCCEEDED/error_code=0; lỗi bất kỳ dừng chuỗi. Timeout dùng wall clock để vẫn phát hiện khi sim clock dừng. Nếu cancel chưa có terminal result, trạng thái CANCELING vẫn giữ khóa busy; không tự mở khóa khi chưa biết goal cũ đã kết thúc.

## Kiểm thử tái lập

Chạy simulator/Nav2 và một pipeline duy nhất, localization đã đúng:

```bash
# Test parser/controller độc lập microphone:
ros2 run tb4_voice_navigation keyboard_command
python -u scripts/test_live_pipeline.py
# T12: tự chèn/xóa collider test trong Gazebo; chạy sau test trên, cần campus:
python -u scripts/test_unreachable.py
# Chạy khi mission chính đã idle; timeout test tạo controller riêng, dùng topic test:
python -u scripts/test_live_failures.py --timeout-test
python scripts/verify_local_asr.py
python scripts/check_scan_alignment.py
```

Không chạy các test điều hướng song song. `test_unreachable.py` đợi kết quả 7 scenario chính, chặn cửa phòng A, kiểm tra FAILED/no next waypoint, rồi gỡ model test và clear costmap trong finally. Test failure dùng action/Nav2/ALSA thật; không có action server giả. `verify_local_asr.py` dùng silence tổng hợp có khai báo rõ, chỉ kiểm tra model/VAD không sinh transcript, không xác nhận độ chính xác tiếng Việt. Kết quả mới cập nhật file trong evidence; sao lưu trước nếu cần lưu nhiều lượt.

`test_live_pipeline.py` phát transcript bàn phím để đo integration, không nhận là ASR PASS. Last feedback JSON baseline nằm trước terminal result, không phải pose cuối chính xác. Một lượt navigation không đủ đánh giá độ tin cậy thống kê. Kịch bản quay video và form nghiệm thu microphone tại `docs/DEMO.md`. Báo cáo hiện tại: `docs/week7_report.pdf`; báo cáo Phase 1–2 cũ giữ để tham chiếu.

## Hạn chế còn lại

Chưa có người nói thật trong phiên này, chưa đo WER/độ trễ ASR thực và chưa có video T15. GUI editor chưa kiểm thử tương tác tự động; watershed chưa đo chất lượng định lượng. Primitive nội thất giúp chạy offline, không phải mô phỏng toàn bộ Create3/TB4 vật lý. Các log lỗi phát hiện trong phát triển được sửa và kiểm thử lại; chỉ trạng thái trong phase_status.md và JSON kết quả cuối là nghiệm thu. Repository Git đã chuẩn bị local, chưa push/public.
