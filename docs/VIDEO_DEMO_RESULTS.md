# Kết quả quay demo PAIRS Lab — 09/11/2026

Bản nộp: [PAIRS_Lab_Demo_1080p.mp4](../submission/PAIRS_Lab_Demo_1080p.mp4), **4:26**, 1920×1080, 15fps, AAC. Toàn bộ file giải mã không lỗi. [Kịch bản và lời dẫn](KICH_BAN_QUAY_PAIRSLAB.md); [mốc thời gian](../submission/CHAPTERS.md); [ảnh báo cáo](../submission/figures/).

Cảnh giọng nói mới: **“Đi đến phòng UAV”** → ASR → parser A → Nav2 SUCCEEDED. Audio microphone và hình thuộc cùng lượt quay. Giữ tốc độ1x, không dùng audio từ phiên nghiệm thu ba câu trước. Câu quay mới có2 lượt ghi: lượt đầu NO_SPEECH, lượt sau đạt; bản dựng chỉ giữ lượt đạt, raw/WAV/log chứa đủ hai lượt. Ba câu cũ vẫn có kết quả riêng trong VOICE_TEST_RESULTS.md.

Tour còn lại dùng **lệnh văn bản**, có nhãn nguồn và tăng tốc2x. Các đích đạt theo thứ tự A→B→D→C→F, sau đó E→C. Đủ năm phòng UAV, tay máy, HRI G1, chó robot Go2, TurtleBot và sảnh PAIRS/ĐHQGHN.

| Vùng | Pose TF tại SUCCEEDED (m) | Trong vùng | Nav2 |
|---|---|---|---|
| A | Xem video voice và receipt cùng lượt | Xác nhận tại đầu tour; xem lưu ý | SUCCEEDED / microphone |
| B | (0.020, 3.429) | True | status4 / error0 |
| D | (9.035, 3.432) | True | status4 / error0 |
| C | (0.030, 0.049) | True | status4 / error0 |
| F | (6.863, -3.449) | True | status4 / error0 |
| E | (-6.897, -3.453) | True | status4 / error0 |
| C | (-0.225, -0.100) | True | status4 / error0 |

Lưu ý dữ liệu: pose A đã được kiểm tra trong vùng khi bắt đầu tour ở mã director, nhưng chưa được ghi thành trường riêng trong receipt phiên này; video voice có HUD pose thật. B/C/D/E/F có pose dạng số và inside_region trong coverage.json. Không bổ sung ngược một số đo A chưa lưu.

**Lỗi được giữ nguyên:** lần F→E đầu bị LOCALIZATION_LOST, covariance x vừa vượt0.5; nhiệm vụ bị hủy. Dùng request_nomotion_update để cập nhật laser lúc đứng yên, không đổi vị trí robot/hạ ngưỡng. E→C sau đó đạt. Bản dựng cắt phần đi E thất bại/chờ khắc phục, nhãn “Nối sau cập nhật AMCL; có cắt dựng” hiện ở đoạn tiếp; raw03 và log vẫn chứa lỗi. Không tuyên bố tour là một lượt liên tục không lỗi.

Giọng nói ghép theo wall time RECORDING của cùng WAV với thời điểm bắt đầu screen capture; có sai số khởi động thiết bị/capture dưới mức giây. Các model robot trưng bày tĩnh; TB4 Nav2 di chuyển thật trong mô phỏng.

Bằng chứng local ở deliverables/pairslab_demo_20261109/: render_manifest.json (hash/thông số/các đoạn cắt), coverage.json, navigation_results.json (bao gồm lỗi), navigation_resume_results.json, voice/filmed_acceptance.json, voice/events.jsonl, voice/asr.jsonl, ros_events.jsonl, clips gốc1x và audio WAV. Prototype HUD tĩnh được giữ riêng trong evidence/video_demo/recorder_tests/ và không dùng trong bản nộp.
