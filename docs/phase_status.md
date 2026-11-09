> **Nghiệm thu bổ sung 09/11/2026:** T15 và ba câu tiếng Việt qua microphone thật đã PASS sau các lượt thử lại. Xem [VOICE_TEST_RESULTS.md](VOICE_TEST_RESULTS.md); các trạng thái “chưa thực hiện” bên dưới thuộc lịch sử trước buổi thử.

> **Cập nhật 09/11/2026:** Môi trường mặc định đã chuyển sang PAIRS Lab 5 khu nghiên cứu. Tài liệu bên dưới là lịch sử campus v1; trạng thái mới tại [PAIRSLAB_STATUS.md](PAIRSLAB_STATUS.md), demo mới tại [DEMO_PAIRSLAB.md](DEMO_PAIRSLAB.md).

# Nghiệm thu theo phase — cập nhật 02/11/2026

## Phase 1 — môi trường và baseline

**Đã thực thi:** Ubuntu 24.04/Jazzy/Harmonic, minimal TB4, AMCL/map_server/lifecycle/Nav2. Baseline map cũ SUCCEEDED; campus mới năm waypoint A→C→B→E→D SUCCEEDED. Bằng chứng: environment.md, evidence/baseline_goal_retry.log, campus_navigation.json, campus_simulation.log, campus_topics/actions/nodes.txt và campus_tf.log. Không thay package hệ thống. Chưa đánh giá độ tin cậy nhiều lượt hoặc robot vật lý.

## Phase 2 — map và semantic

**Đã triển khai/kiểm chứng:** world bốn phòng, hành lang, collision-derived map (không gọi là SLAM), polygon thủ công A–E, goal/yaw/aliases, free/occupied/unknown, clearance/connectivity, coordinate transform hai chiều có origin yaw. Goal validation: evidence/goals_validation.yaml. Scan/map: 10 scan/3600 endpoints, median=0m/p95=.05m tại pose đo; evidence/scan_alignment.json. Ảnh segmentation và screenshot Gazebo thật trong docs/. Editor thủ công đã có nhưng chưa kiểm thử thao tác GUI của người dùng; watershed xuất dữ liệu được, chưa đánh giá chất lượng phòng tự động.

## Phase 3 — speech recognition

**Đã triển khai:** voice_recognition_node sử dụng arecord/ALSA thật, Whisper small đa ngôn ngữ local CPU int8, PTT start/stop/discard, ghi tối đa12s, VAD/RMS/logprob/no-speech/clipping gates, error/status/transcript. Không dùng PortAudio vì môi trường thiếu thư viện đó; không thay hệ thống. Model tải/nạp thực tế: evidence/model_download.log, whisper_model_revision.txt, voice_pipeline_final.log / ready_for_demo.log.

**Đã kiểm chứng riêng:** model/VAD silence test cho transcript rỗng (input tổng hợp ghi rõ trong evidence/asr_silence.json); T10 thiết bị ALSA không tồn tại → ASR_ERROR, node vẫn chạy, không transcript. Đây không phải demo speech thật.

**Chưa nghiệm thu tiêu chí phase3:** chưa có ba câu tiếng Việt người thật. Người dùng xác nhận chưa thể thử microphone. Không tạo transcript hoặc kết quả ASR giả.

## Phase 4 — parser/controller

**Đã triển khai:** parser độc lập ASR, so khớp alias chính xác sau normalize, lỗi có cấu trúc, single/source_destination/multi_waypoint/cancel. Controller validate tất cả vùng trước nhiệm vụ, chờ server và AMCL/TF tươi, preflight ComputePathToPose, NavigateToPose tuần tự, quaternion yaw, feedback/terminal result, dừng chuỗi khi thất bại. Busy/cancel/timeouts và giữ khóa khi cancellation chưa có terminal result. Không gửi cmd_vel để thay Nav2, không set pose Gazebo.

**Đã thực thi với Nav2 thật:** 7 scenario integration keyboard trong evidence/live_pipeline_results.json. A→C→B; current(B)→A→B; B→C bỏ qua nguồn đã ở gần; alias phòng thí nghiệm→B; Z reject/no goal; busy reject; cancellation status5. Transcript keyboard được ghi rõ, không đánh dấu ASR PASS.

**Test failure thật:** evidence/live_failures_results.json: Nav2 không sẵn sàng, TF không có, timeout goal có cancel status5, thiết bị microphone sai. evidence/unreachable_result.json: collider thật chặn phòngA, Nav2 abort status6/error208, controllerFAILED, waypointC không được gửi. Script gỡ test model và clear costmaps sau khi xong.

## Phase 5 — tích hợp và visualization

**Đã triển khai:** voice_navigation.launch.py, tùy chọn start_sim/headless/ASR, config thông số, terminal PTT và keyboard. MarkerArray trong frame map mét: polygon, tên, goal/yaw, active target; Path thật từ planner. RViz hiển thị tên không dấu do giới hạn font của text marker; metadata/ASR/parser vẫn tiếng Việt. Đường nối các đích chỉ biểu thị thứ tự, không thay đường Nav2. Screenshot thật: docs/rviz_semantic.png.

**Chưa nghiệm thu T15:** chưa có người nói → ASR → robot tới đích. Code đầy đủ, model và pipeline khởi động thật; test integration đã tách microphone theo yêu cầu. Không gọi keyboard test là voice end-to-end.

## Phase 6 — bàn giao

Source ament_python/entrypoints/dependencies/config/maps/worlds/launch/RViz; README tái lập, unit tests, test scripts thật, ảnh, báo cáo PDF docs/week7_report.pdf, kịch bản video docs/DEMO.md. Repository Git local đã chuẩn bị, chưa push/public. Chưa có video voice thực tế và phiếu ba câu vẫn trống. Báo cáo Phase1–2 cũ giữ riêng để tham chiếu, đã được báo cáo mới thay thế về tiến độ hiện tại.

## Ma trận T01–T15

| ID | Trạng thái | Bằng chứng |
|---|---|---|
| T01 | Unit PASS | test_read_real_map |
| T02 | Unit PASS | roundtrip và known_pixel_centres, origin xoay |
| T03 | Unit PASS | wall/unknown goal reject |
| T04 | Unit PASS | goal outside polygon reject |
| T05 | Unit PASS | parser single A; test hợp lệ trong pytest |
| T06 | Unit + simulation integration PASS | alias→B; live_pipeline_results.json |
| T07 | Unit + simulation integration PASS | current→A→B; source skip gần nguồn |
| T08 | Unit + simulation integration PASS | A→C→B, waypoint result đúng thứ tự |
| T09 | Unit + ROS integration PASS | Z→UNKNOWN_REGION/REJECTED, không gửi goal |
| T10 | Live ALSA negative PASS | thiết bị không tồn tại; không crash/transcript |
| T11 | Live ROS negative PASS | NAV2_NOT_READY |
| T12 | Simulation negative PASS | collider thật, Nav2 abort208, stop chain |
| T13 | Simulation PASS | cancel action terminal status5 |
| T14 | ROS/Nav2 integration PASS | BUSY, lệnh mới bị reject |
| T15 | CHƯA THỰC HIỆN | người dùng chưa thể nói vào microphone |

Colcon unit suite: evidence/colcon_test_voice.log, colcon_test_voice_result.log. Mọi PASS ở trên đều dựa vào source test hoặc log/JSON thực thi; không suy từ kiến trúc hoặc ảnh.

## Lỗi phát hiện và xử lý khi phát triển

Runtime phát hiện trùng thuộc tính `Node.handle`; đổi thành goal_handle. QoS status depth1 gây mất sự kiện BUSY trong subscriber test; tăng bộ đệm status và chạy lại toàn bộ integration. Test server-timeout ban đầu quá ngắn cho discovery AMCL; thêm warmup và dùng server_timeout3s riêng trong test. Log/kết quả cuối của các test đều PASS; không dùng lượt thất bại để xác nhận nghiệm thu. Các lỗi dự kiến trong negative tests là kết quả mong đợi của test, không phải lỗi còn chưa xử lý.

## Kiểm chứng cuối từ phiên sạch

71 unit tests PASS (thêm regression UUID ROS dạng numpy-backed). evidence/final_launch_smoke.json: full launch mới, AMCL/lifecycle active, model ASR ready, parser alias→B và action SUCCEEDED/error0. Bằng chứng server tại evidence/full_launch_clean.log; initial pose chỉ AMCL tại full_launch_localization.log.

Các lần restart phát hiện race file world tạm ở launch vendor và Gazebo server bị orphan bởi shell wrapper; baseline.launch.py nay nạp SDF có sẵn bằng ExecuteProcess trực tiếp. Kiểm tra dừng sạch nằm ở evidence/launch_shutdown.json. Lỗi so sánh UUID array trong feedback được sửa sang bytes và có unit regression; lượt smoke cuối đã nhận feedback/result thành công. Các file full_launch.log/full_launch_final.log/full_launch_verified.log là lượt phát triển không PASS; không dùng chúng làm kết quả nghiệm thu.
