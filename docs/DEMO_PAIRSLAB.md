# Demo PAIRS Lab — scene 5 khu nghiên cứu

Cập nhật 09/11/2026. **Đã thực hiện ngày09/11/2026:** ba câu đã đạt T15 qua microphone thật. Tổng6 lượt gồm3 lượt thành công; giữ cả các lượt chưa đạt. Kết quả ở VOICE_TEST_RESULTS.md. Video quay bổ sung một câu UAV cùng tour đủ5phòng ở VIDEO_DEMO_RESULTS.md. Không dùng các câu cũ “phòng học/phòng thí nghiệm” vì scene đã có tên phòng chuyên biệt.

## Tham quan scene

Chạy voice_navigation.launch.py start_sim:=true (enable_asr:=false nếu chỉ xem scene). AMCL tự khởi tạo pose spawn. Dùng scripts/pairslab_camera.py lần lượt overview / uav / manipulation / hri / go2 / turtlebot / branding. Quay góc tổng quan trước, rồi cận cảnh G1, Go2 và hai logo gốc. Các robot trưng bày đứng tĩnh; chỉ TurtleBot navigation đang được điều hướng thật.

## Ba câu để thử microphone sau khi người dùng tiếp tục

Khởi động ASR trong một pipeline duy nhất (enable_asr:=true), chờ MODEL_READY, dùng push_to_talk. Nhấn Enter bắt đầu, nói, Enter dừng. Đợi terminal SUCCEEDED trước câu tiếp theo.

1. **“Đi đến phòng UAV.”** → A.
2. **“Đi đến phòng chó robot.”** → E, khu Unitree Go2.
3. **“Đi từ phòng UAV qua hành lang đến phòng robot hình người.”** → A → C → D, khu Unitree G1.

Bổ sung: “Đi đến phòng tay máy” → B; “Đi đến phòng TurtleBot” → F. “Dừng lại” qua PTT mới hoặc /voice/cancel service. Phải ghi rõ hủy bằng voice hay service trong nghiệm thu.

## Lưu bằng chứng thật

```bash
mkdir -p evidence/voice_demo/pairslab
ros2 topic echo /voice/asr_status --qos-durability transient_local > evidence/voice_demo/pairslab/asr.log
ros2 topic echo /voice/parsed_command > evidence/voice_demo/pairslab/parser.log
ros2 topic echo /voice/navigation_status --qos-durability transient_local > evidence/voice_demo/pairslab/navigation.log
```

Muốn giữ audio gốc: tạo evidence/voice_demo/pairslab/audio rồi set recordings_dir của voice_recognition_node tới đó. Voice_demo đã được Git ignore. Mỗi lượt ghi expected_sentence riêng với transcript thực, parser waypoints, terminal Nav2 và video/audio cùng lượt; không điền transcript kỳ vọng thay kết quả nhận dạng thật.

| Câu | Transcript thật | Nav2 | Video/log |
|---|---|---|---|
| Phòng UAV | Đi đến phòng UAV | SUCCEEDED → A, lượt1 | Phiên ba câu cũ chỉ có audio/log |
| Phòng chó robot | Đi đến phòng cho robot | SUCCEEDED → E, lượt3 | Phiên ba câu cũ chỉ có audio/log |
| UAV → sảnh → humanoid | Đi từ phòng UAV qua Hành Lang đến phòng robot Hình Người | SUCCEEDED A→C→D, lượt2 | Phiên ba câu cũ chỉ có audio/log |

Các test Nav2/native và input keyboard đã thực thi lưu riêng trong evidence/pairslab_redesign/, không được gọi là voice PASS.
