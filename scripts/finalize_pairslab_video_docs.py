#!/usr/bin/env python3
"""Update report links only after a rendered, verified filmed demo exists."""

from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
s = root / "deliverables/pairslab_demo_20261109"
m = json.loads((s / "render_manifest.json").read_text())
assert m["decode_check"] == "PASS" and m["coverage"]["passed"]
video = root / m["final_video"]
assert hashlib.sha256(video.read_bytes()).hexdigest() == m["final_sha256"]
assert all(
    r["terminal"]["state"] == "SUCCEEDED" and r["arrival_pose"]["inside_region"]
    for r in m["coverage"]["results"]
)
seconds = round(m["duration_s"])
duration = f"{seconds // 60}:{seconds % 60:02d}"
readme = f"""# PAIRS Lab — bộ video và ảnh báo cáo

Mở **[PAIRS_Lab_Demo_1080p.mp4](PAIRS_Lab_Demo_1080p.mp4)** — {duration}, 1920×1080, 15fps; audio AAC. Xem [mốc video](CHAPTERS.md) và [kịch bản](../../docs/KICH_BAN_QUAY_PAIRSLAB.md).

Nội dung: logo PAIRS/ĐHQGHN, tổng quan, UAV/X500, tay máy UR5e/UR3e, HRI/Unitree G1, chó robot/Unitree Go2, TurtleBot. Câu “{m["voice"]["actual_transcript"]}” do người dùng nói qua microphone trong chính lượt quay; robot đến A. Phần đi B→D→C→F, nối E→C dùng lệnh văn bản qua parser/Nav2, ghi nhãn và tăng tốc2x. Không tuyên bố các phòng sau được gọi bằng giọng nói.

Cảnh microphone có2 lượt ghi: lượt đầu NO_SPEECH, lượt sau nhận đúng và đến A; bản dựng chỉ dùng lượt đạt, raw/audio/log giữ cả hai.

Lượt F→E đầu bị LOCALIZATION_LOST. Sau cập nhật laser lúc đứng yên cho AMCL hội tụ, lần E→C đạt. Bản dựng bỏ đoạn thử E thất bại và chờ khắc phục, có nhãn đoạn nối; clip gốc và log vẫn giữ. Đây là bản có cắt dựng, không phải một lượt liên tục không lỗi. Không teleport hoặc hạ ngưỡng kiểm tra định vị.

- `stills/`: ảnh Gazebo thật, gồm 7 góc giới thiệu, ảnh đến đích và tổng kết; dùng trực tiếp trong báo cáo.
- `01_environment_master.mp4`: cảnh giới thiệu gốc1x.
- `02_voice_master_silent.mp4` + `voice/audio/`: video gốc và microphone cùng lượt quay; phần `edited/02_voice_real.mp4` đã ghép audio theo wall time RECORDING. Có sai số khởi động capture/thiết bị dưới mức giây, không cam kết khớp từng frame.
- `03_navigation_master.mp4`: lượt tour đầu, giữ nguyên cả lần E thất bại.
- `04_navigation_resume.mp4`: quay tiếp E→C sau cập nhật AMCL.
- `coverage.json`, `navigation_results.json`, `navigation_resume_results.json`, `voice/filmed_acceptance.json`, `ros_events.jsonl`: bằng chứng nguồn lệnh, command_id, terminal Nav2 và pose.
- `render_manifest.json`, `decode_check.log`: thông số dựng, SHA256 và kiểm tra giải mã toàn bộ.

Báo cáo cập nhật: [pairslab_scene_report.pdf](../../docs/pairslab_scene_report.pdf). Giữ bộ này local; chưa publish/push. G1/Go2/X500/UR và TB4 trưng bày là model tĩnh; robot chạy Nav2 là TurtleBot4 riêng.
"""
(s / "README.md").write_text(readme)
result = f"""# Kết quả quay demo PAIRS Lab — 09/11/2026

Bản nộp: [PAIRS_Lab_Demo_1080p.mp4](../deliverables/pairslab_demo_20261109/PAIRS_Lab_Demo_1080p.mp4), **{duration}**, 1920×1080, 15fps, AAC. Toàn bộ file giải mã không lỗi. [Kịch bản và lời dẫn](KICH_BAN_QUAY_PAIRSLAB.md); [mốc thời gian](../deliverables/pairslab_demo_20261109/CHAPTERS.md); [ảnh báo cáo](../deliverables/pairslab_demo_20261109/stills/).

Cảnh giọng nói mới: **“{m["voice"]["actual_transcript"]}”** → ASR → parser A → Nav2 SUCCEEDED. Audio microphone và hình thuộc cùng lượt quay. Giữ tốc độ1x, không dùng audio từ phiên nghiệm thu ba câu trước. Câu quay mới có2 lượt ghi: lượt đầu NO_SPEECH, lượt sau đạt; bản dựng chỉ giữ lượt đạt, raw/WAV/log chứa đủ hai lượt. Ba câu cũ vẫn có kết quả riêng trong VOICE_TEST_RESULTS.md.

Tour còn lại dùng **lệnh văn bản**, có nhãn nguồn và tăng tốc2x. Các đích đạt theo thứ tự A→B→D→C→F, sau đó E→C. Đủ năm phòng UAV, tay máy, HRI G1, chó robot Go2, TurtleBot và sảnh PAIRS/ĐHQGHN.

| Vùng | Pose TF tại SUCCEEDED (m) | Trong vùng | Nav2 |
|---|---|---|---|
| A | Xem video voice và receipt cùng lượt | Xác nhận tại đầu tour; xem lưu ý | SUCCEEDED / microphone |
"""
for r in m["coverage"]["results"]:
    p = r["arrival_pose"]
    result += f"| {r['region']} | ({p['x']:.3f}, {p['y']:.3f}) | {p['inside_region']} | status4 / error0 |\n"
result += """
Lưu ý dữ liệu: pose A đã được kiểm tra trong vùng khi bắt đầu tour ở mã director, nhưng chưa được ghi thành trường riêng trong receipt phiên này; video voice có HUD pose thật. B/C/D/E/F có pose dạng số và inside_region trong coverage.json. Không bổ sung ngược một số đo A chưa lưu.

**Lỗi được giữ nguyên:** lần F→E đầu bị LOCALIZATION_LOST, covariance x vừa vượt0.5; nhiệm vụ bị hủy. Dùng request_nomotion_update để cập nhật laser lúc đứng yên, không đổi vị trí robot/hạ ngưỡng. E→C sau đó đạt. Bản dựng cắt phần đi E thất bại/chờ khắc phục, nhãn “Nối sau cập nhật AMCL; có cắt dựng” hiện ở đoạn tiếp; raw03 và log vẫn chứa lỗi. Không tuyên bố tour là một lượt liên tục không lỗi.

Giọng nói ghép theo wall time RECORDING của cùng WAV với thời điểm bắt đầu screen capture; có sai số khởi động thiết bị/capture dưới mức giây. Các model robot trưng bày tĩnh; TB4 Nav2 di chuyển thật trong mô phỏng.

Bằng chứng local ở deliverables/pairslab_demo_20261109/: render_manifest.json (hash/thông số/các đoạn cắt), coverage.json, navigation_results.json (bao gồm lỗi), navigation_resume_results.json, voice/filmed_acceptance.json, voice/events.jsonl, voice/asr.jsonl, ros_events.jsonl, clips gốc1x và audio WAV. Prototype HUD tĩnh được giữ riêng trong evidence/video_demo/recorder_tests/ và không dùng trong bản nộp.
"""
(root / "docs/VIDEO_DEMO_RESULTS.md").write_text(result)
p = root / "README.md"
t = p.read_text().replace(
    "Chưa có video quay màn hình của buổi thử.",
    f"Đã quay video demo bổ sung {duration}, đủ5phòng và sảnh, có một lệnh microphone cùng lượt; xem [video và kết quả](docs/VIDEO_DEMO_RESULTS.md). Tour văn bản tăng tốc2x, có đoạn nối sau mất định vị được ghi rõ.",
)
p.write_text(t)
p = root / "docs/PAIRSLAB_STATUS.md"
t = p.read_text().replace(
    "- Chưa có video quay màn hình của buổi voice demo; dữ liệu nghiệm thu là audio thật + transcript/parser/Nav2 event log. Một phiên thử không xác nhận độ chính xác ASR tổng quát.",
    f"- Đã bổ sung video {duration}, đủ5phòng+sảnh: một câu microphone mới→A; tour văn bản ghi nhãn2x. Có lần mất định vị ở F→E, cập nhật AMCL đứng yên rồi E→C đạt; bản dựng ghi rõ đoạn nối. Xem VIDEO_DEMO_RESULTS.md. Phiên ba câu trước vẫn có audio/log riêng và retries; không suy thành độ chính xác ASR tổng quát.",
)
p.write_text(t)
p = root / "docs/DEMO_PAIRSLAB.md"
t = p.read_text().replace(
    "Kết quả ở VOICE_TEST_RESULTS.md; chưa quay video màn hình.",
    "Kết quả ở VOICE_TEST_RESULTS.md. Video quay bổ sung một câu UAV cùng tour đủ5phòng ở VIDEO_DEMO_RESULTS.md.",
)
p.write_text(t)
e = root / "evidence/pairslab_redesign"
receipt = dict(
    status="PASS",
    video=m["final_video"],
    duration_s=m["duration_s"],
    resolution=m["resolution"],
    capture_fps=m["capture_fps"],
    sha256=m["final_sha256"],
    decode_check="PASS",
    visited=m["coverage"]["visited"],
    real_voice_transcript=m["voice"]["actual_transcript"],
    real_voice_command_id=m["voice"]["command_id"],
    real_voice_trials=m["voice"]["trials"],
    voice_editing_note=m["voice"]["editing_note"],
    navigation_source=m["navigation_source"],
    editing_note=m["editing_note"],
    manifest=str((s / "render_manifest.json").relative_to(root)),
    results=m["coverage"]["results"],
)
(e / "video_acceptance.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False))
p = e / "acceptance_summary.json"
d = json.loads(p.read_text())
d["video_demo"] = receipt
p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
print("Docs updated after verified render:", video)
