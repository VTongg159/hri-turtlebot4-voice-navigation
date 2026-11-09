# Phase 1 — khảo sát và baseline

Môi trường kiểm tra ngày 02/11/2026 (Asia/Ho_Chi_Minh).

- Ubuntu 24.04.4 LTS; Python 3.12.3; ROS_DISTRO=jazzy; ROS_DOMAIN_ID=19.
- Gazebo CLI chọn Sim 8.11.0 từ ROS vendor; libgz-sim8 hệ thống là 8.14.0. Hai bản cùng tồn tại; baseline thực thi bằng ROS vendor thành công. Không thay đổi thư viện hệ thống.
- Nav2 1.3.12; AMCL, map_server, lifecycle manager, SLAM Toolbox, TF2, ros_gz_bridge, RViz2, colcon có sẵn.
- Không có package turtlebot4_gz_bringup. Có nav2_minimal_tb4_sim 1.0.1 và nav2_minimal_tb4_description: dùng mô hình TB4 tối giản của Nav2, không tuyên bố bao phủ toàn bộ chức năng Create3/TB4 vật lý.
- Ryzen 7 7735HS, RAM 14 GiB, RTX 4050 6 GiB. Ổ đĩa ban đầu trống 8.9 GiB. Dùng faster-whisper CPU int8, giới hạn thread để chia tài nguyên với simulator.
- cv2, numpy, yaml, pytest có sẵn. Bổ sung faster-whisper, sounddevice, reportlab vào .venv riêng, không nâng cấp package hệ thống. Cần tải model đa ngôn ngữ; cache small ban đầu chỉ 2.6 MiB, chưa đủ.
- ALSA capture card 2 ALC256 Analog; arecord default thu 32000 mẫu / 2 giây thành công. Điều này chỉ xác minh mở/ghi thiết bị; chưa xác minh nhận dạng tiếng Việt. Mẫu có clipping, cần chỉnh gain trước demo.

Tái sử dụng map và world từ hri_turtlebot4_week04, commit b412a8d1b3b3ea4b11e84ce653cd70803f493f12, giữ nguyên workspace cũ. Map 239 x 199 pixels, resolution 0.05m, origin [-2.470,-2.493,0]. World spawn [-3.5,-2.5,0] tương ứng map [0,0,0] theo bài cũ, đã kiểm tra bằng AMCL/TF. Đây là bản đồ không gian mở có hai vách, A/B/C là nhãn do người dùng đặt.

## Baseline thật

Chạy launch simulation của tuần 4 headless:=True, sau đó nav2_bringup bringup_launch.py với map/params tuần 4, use_sim_time:=true, use_composition:=False. Publish /initialpose [0,0,0] (chỉ khởi tạo AMCL, không teleport). Goal đầu bị reject vì lifecycle chưa active; giữ log baseline_goal.log. Sau Managed nodes are active gửi lại /navigate_to_pose tới [0.8,0,0].

**PASS chuyển động và action result:** evidence/baseline_goal_retry.log có SUCCEEDED, error_code=0; evidence/nav2.log có Begin navigating / Reached the goal / Goal succeeded. Robot feedback đổi từ ~[0.02,0.02] tới ~[0.57,0.01], trong tolerance Nav2 0.25m. Chưa chứng minh riêng khả năng tránh vật cản động.

Các interface phát hiện thực tế nằm trong evidence/topics.txt, actions.txt, nodes.txt. Có /map, /scan, /odom, /tf, /tf_static, /amcl_pose; /navigate_to_pose và /navigate_through_poses đúng type Nav2. evidence/tf_map_base.log xác minh TF map→base_link. Chưa có pipeline voice khi chạy baseline.

## Kiến trúc và kế hoạch

1. ament_python tb4_voice_navigation độc lập, giữ asset map/world và params đã chạy.
2. Phase 2: semantic map trinary, polygon editor, goal có clearance, connectivity; unit tests tọa độ. Auto watershed chỉ gợi ý, người dùng duyệt.
3. Phase 3: faster-whisper multilingual CPU int8; push-to-talk start/stop qua service; VAD, giới hạn thời gian, kiểm tra âm thanh; lưu transcript thật. Bàn phím để test độc lập.
4. Phase 4: parser rule-based với aliases; NavigateToPose tuần tự; TF tươi, state machine, cancel/timeout, busy; kiểm tra path bằng Nav2 trước mỗi waypoint.
5. Phase 5: launch riêng baseline/pipeline; MarkerArray map frame, goal/route/active target. Test thật với Nav2.
6. Phase 6: pytest + colcon, ma trận T01–T15, README, PDF thực nghiệm, kịch bản video. Không public/push khi chưa được cho phép.

Nguồn đối chiếu: https://docs.nav2.org/jazzy/getting_started/build_and_install/local_installation/ ; https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation/tree/jazzy ; https://github.com/SYSTRAN/faster-whisper . Bản cài và log thực tế là căn cứ quyết định tương thích.

## Cập nhật theo yêu cầu đổi bản đồ

Người dùng yêu cầu thay bản đồ sơ sài bằng bố cục đẹp, phù hợp bài tập. Đã tạo Semantic Campus trong workspace mới, không đổi file gốc. Bản đồ mới có origin [-7.5,-5.5,0], spawn map = world [-5.5,0,0], KHÔNG dùng offset world/map của bài tuần 4. Xem README.md, docs/phase_status.md và evidence/campus_navigation.json cho kết quả năm waypoint trên world mới; kết quả baseline tuần 4 ở trên chỉ là lịch sử khảo sát.

## Cập nhật Phase 3–6

Đã tải small Whisper đa ngôn ngữ, nạp CPU int8 thật. PortAudio không có nên thu bằng arecord/ALSA có sẵn; sounddevice không dùng trong implementation. Đã triển khai ASR/parser/controller/markers/PTT/launch đầy đủ. Evidence hiện tại và trạng thái nghiệm thu nằm ở phase_status.md; báo cáo mới week7_report.pdf thay báo cáo tiến độ Phase1–2 về tình trạng phần mềm. T15/ba câu nói thật vẫn chưa thực hiện theo xác nhận người dùng.

## Scene PAIRS Lab — 09/11/2026

Đổi mặc định sang pairs_lab.sdf (28×20m), pairs_lab.yaml (origin[-14.5,-10.5,0]), pairs_regions.yaml (A–F), spawn[-11,0,0]. Unitree G1/Go2 mesh chính thức, UR5e/UR3e, X500 và TB4 exhibits; license/commit ở PAIRSLAB_ASSETS.md. Nguồn assets đã vendor để chạy offline. AMCL tự khởi tạo pose của robot vừa spawn trong pairs_nav2_params.yaml. Microphone test tạm hoãn theo yêu cầu đổi môi trường; chưa có speech/T15 thật. Kết quả scene mới tách riêng evidence/pairslab_redesign, báo cáo pairslab_scene_report.pdf.
