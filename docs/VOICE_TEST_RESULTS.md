# Nghiệm thu giọng nói thật — 09/11/2026

**T15 PASS:** người dùng nói qua microphone thật → Whisper tiếng Việt local → parser → Nav2 → TurtleBot4 trong PAIRS Lab. Ba câu đều đã có lượt kết thúc SUCCEEDED. Không dùng keyboard/TTS để tạo transcript nghiệm thu.

| Câu | Transcript thật của lượt đạt | Waypoints thực hiện | Lượt đạt | Nav2 |
|---|---|---|---|---|
| 1 | Đi đến phòng UAV | A | 1 | SUCCEEDED |
| 2 | Đi đến phòng cho robot | E | 3 | SUCCEEDED |
| 3 | Đi từ phòng UAV qua Hành Lang đến phòng robot Hình Người | A → C → D | 2 | SUCCEEDED |

## Những lượt chưa đạt đã giữ nguyên

Tổng6 lượt ghi,3 lượt thành công. Chỉ1/3 câu thành công ngay lượt đầu; không gọi đây là nhận dạng chính xác100%. Câu2 được thử3 lần, câu3 được thử2 lần.

| Lượt | Câu | Kết quả ASR | Xử lý |
|---|---|---|---|
| 2 | 2 | đi đến phòng chó rối | UNKNOWN_REGION; không gửi goal mới |
| 3 | 2 | NO_SPEECH | Không phát transcript |
| 5 | 3 | đi từ phẩm UAV qua hành lang đến phẩm robot hình người | UNKNOWN_REGION; không gửi goal mới |

Lượt đạt câu2 có transcript “cho robot” thiếu dấu; parser chuẩn hóa dấu nên khớp đúng alias “chó robot”. Không sửa transcript gốc. Những từ sai khác như “chó rối” hoặc “phẩm UAV” bị từ chối thay vì đoán vùng.

## Bằng chứng và phép đối chiếu

- Kết quả thô: evidence/voice_demo/pairslab_live/results.json.
- Event ROS: evidence/voice_demo/pairslab_live/events.jsonl; logASR: asr.jsonl; terminal.log ghi cả các lần thử lại.
- AudioWAV gốc16kHz/mono/16bit: evidence/voice_demo/pairslab_live/audio/. Thư mục voice_demo được Git ignore.
- Receipt đã kiểm tra: evidence/pairslab_redesign/voice_acceptance.json. Script scripts/summarize_voice_trials.py đối chiếu transcript↔parser↔command_id↔terminal result, thứ tự từng waypoint, action status4/error0 và SHA256/duration của audio thật.

| Câu đạt | Thời gian trạng thái TRANSCRIBING → TRANSCRIPT (s) | Transcript → kết thúc nhiệm vụ (s) |
|---|---|---|
| 1 | 1.800 | 56.304 |
| 2 | 1.600 | 22.496 |
| 3 | 1.900 | 78.059 |

Các thời gian trên tính từ timestamp trạng thái đã publish trong cùng lượt; không phải kết quả benchmark WER hay latency của mọi môi trường. Chỉ một người dùng, một phiên thử và có retries.

## Còn lại để nộp bài

Phiên ba câu này có audio/log, chưa có video cùng lượt. Đã quay bổ sung một câu UAV và tour đủ5phòng: xem VIDEO_DEMO_RESULTS.md và ../submission/README.md. Source public được người dùng cho phép trong yêu cầu bàn giao; raw WAV vẫn giữ local. Sau dọn mã đã build và chạy lại87unit test đạt.
