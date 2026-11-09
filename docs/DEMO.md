> **Nghiệm thu bổ sung 09/11/2026:** T15 và ba câu tiếng Việt qua microphone thật đã PASS sau các lượt thử lại. Xem [VOICE_TEST_RESULTS.md](VOICE_TEST_RESULTS.md); các trạng thái “chưa thực hiện” bên dưới thuộc lịch sử trước buổi thử.

> **Cập nhật 09/11/2026:** Môi trường mặc định đã chuyển sang PAIRS Lab 5 khu nghiên cứu. Tài liệu bên dưới là lịch sử campus v1; trạng thái mới tại [PAIRSLAB_STATUS.md](PAIRSLAB_STATUS.md), demo mới tại [DEMO_PAIRSLAB.md](DEMO_PAIRSLAB.md).

# Kịch bản video và nghiệm thu giọng nói thật

Ngày chuẩn bị: 02/11/2026. **Chưa quay video/chưa thực hiện ba câu nói thật.**

## Chuẩn bị

Build bằng Python .venv và tải modelsmall theo README. Chạy voice_navigation.launch.py start_sim:=true; seed localization chỉ trên robot vừa spawn. Đợi MODEL_READY, TF và Nav2 active. Mở Gazebo toàn cảnh, RViz Semantic Regions/Voice Planned Path, terminal ASR và navigation status. Dùng headphone để tránh loa phát âm thanh vào mic. Chỉnh input gain nếu CLIPPED_AUDIO; thử `arecord -l` trước khi chọn thiết bị.

Ghi log thật (các terminal riêng):

```bash
mkdir -p evidence/voice_demo
ros2 topic echo /voice/asr_status --qos-durability transient_local > evidence/voice_demo/asr.log
ros2 topic echo /voice/parsed_command > evidence/voice_demo/parser.log
ros2 topic echo /voice/navigation_status --qos-durability transient_local > evidence/voice_demo/navigation.log
ros2 bag record -o evidence/voice_demo/rosbag /voice/transcript /voice/parsed_command /voice/navigation_status /voice/asr_status /amcl_pose /tf /tf_static /semantic_regions/markers /voice/planned_path
```

Chỉ bắt đầu nói sau khi PTT báo đang ghi. Mỗi nhiệm vụ đợi terminal SUCCEEDED/FAILED/CANCELED trước lệnh mới, ngoại trừ cảnh kiểm tra busy/cancel có chủ đích. Dùng chức năng quay màn hình của Ubuntu/Gazebo thật, không tạo ảnh kết quả thay thế.

## Các cảnh

1. **Map segmentation (20–30s):** world bốn phòng, occupancy trinary và ảnh màu A–E; chỉ vào các polygon và goal. Nói rõ map từ collision geometry, không phải SLAM.
2. **Single + câu nói #1:** PTT, nói “Đi đến khu vực A.” Dừng ghi, chụp transcript thật và parser A; quay robot qua cửa A; chỉ đánh PASS khi Nav2 terminal SUCCEEDED.
3. **Semantic + câu nói #2:** nói “Đi đến phòng thí nghiệm.” Transcript có thể khác dấu/cách viết; parser phải match aliasB. Quay đường planner và robot đến B.
4. **Source→destination:** từ B hoặc C, nói “Đi từ khu vực A đến khu vực B.” Cần có WAYPOINT_SUCCEEDED A trước B, không teleport. Nếu xuất phát ngay A có SOURCE_ALREADY_REACHED; nên quay từ vị trí khác A để minh họa đầy đủ.
5. **Invalid:** nói “Đi đến khu vực Z.” Xem UNKNOWN_REGION và REJECTED, không có GOAL_ACCEPTED cho câu đó.
6. **Multi + câu nói #3:** nói “Đi từ phòng A qua hành lang C rồi đến phòng B.” Hiển thị thứ tự A,C,B; mỗi waypoint phải có result SUCCEEDED trước điểm sau.
7. **Busy/cancel:** khi đang chạy, nhập câu mới để thấy BUSY; sau đó nói “Dừng lại” bằng phiên PTT mới hoặc gọi /voice/cancel để thấy terminal action status5 và mission CANCELED. Nếu dùng service phải ghi rõ là hủy qua service, không gọi đó là voice cancel PASS.

## Phiếu kết quả (để trống tới khi thực thi)

| Lần | Câu nói chuẩn | Transcript thật | Parser | Nav2 terminal | Độ trễ ASR | Bằng chứng |
|---|---|---|---|---|---|---|
| 1 | Đi đến khu vực A | Chưa thử | Chưa thử | Chưa thử | Chưa đo | Chưa có |
| 2 | Đi đến phòng thí nghiệm | Chưa thử | Chưa thử | Chưa thử | Chưa đo | Chưa có |
| 3 | Đi từ phòng A qua hành lang C rồi đến phòng B | Chưa thử | Chưa thử | Chưa thử | Chưa đo | Chưa có |

T15 chỉ PASS khi âm thanh người nói thật → ASR → parser → action → robot đạt đích, với log và video cùng lượt. Không điền transcript kỳ vọng thay transcript thật; không dùng TTS phát ra loa để thay người nói trong nghiệm thu. Có thể tính command accuracy/ASR latency sau nhiều lượt, không suy từ test silence hoặc keyboard integration.

Ctrl+C dừng rosbag/log/video khi xong; lưu audio/video/rosbag ngoài Git nếu có dữ liệu riêng tư. Repository chưa được cho phép public; không tự push.

Nếu cần giữ audio gốc trong buổi nghiệm thu, tạo thư mục trước rồi bật tùy chọn (mặc định không lưu audio):

```bash
mkdir -p evidence/voice_demo/audio
ros2 param set /voice_recognition_node recordings_dir evidence/voice_demo/audio
ros2 param set /voice_recognition_node audit_file evidence/voice_demo/asr.jsonl
```

Thư mục voice_demo được Git ignore. Đo ASR latency từ thời điểm kết thúc ghi đến TRANSCRIPT; giá trị này cần timestamp ghi thực tế, không suy từ thời gian navigation.
