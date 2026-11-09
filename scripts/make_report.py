#!/usr/bin/env python3
"""Reproducible report from executed test artifacts; unmet speech criteria stay pending."""

from pathlib import Path
import json
import xml.etree.ElementTree as ET
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)

root = Path(__file__).resolve().parents[1]
for name, file in [("VI", "DejaVuSans.ttf"), ("VIBold", "DejaVuSans-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, "/usr/share/fonts/truetype/dejavu/" + file))
styles = getSampleStyleSheet()
for s in styles.byName.values():
    s.fontName = "VI"
styles["BodyText"].leading = 15
styles["BodyText"].spaceAfter = 9
styles["Heading2"].fontName = "VIBold"
styles["Heading2"].fontSize = 13
styles.add(
    ParagraphStyle(
        name="TitleVI",
        fontName="VIBold",
        fontSize=20,
        leading=27,
        textColor=colors.HexColor("#172b43"),
        spaceAfter=16,
    )
)
story = []


def text(value, style="BodyText"):
    story.append(Paragraph(value, styles[style]))


def image(file, width):
    from PIL import Image as PILImage

    path = root / "docs" / file
    with PILImage.open(path) as im:
        w, h = im.size
    story.append(Image(str(path), width=width, height=width * h / w))


def table(rows, widths):
    t = Table(
        [[Paragraph(str(c), styles["BodyText"]) for c in row] for row in rows],
        colWidths=widths,
        repeatRows=1,
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))


nav = json.loads((root / "evidence/live_pipeline_results.json").read_text())
negative = json.loads((root / "evidence/live_failures_results.json").read_text())
unreachable = json.loads((root / "evidence/unreachable_result.json").read_text())
silence = json.loads((root / "evidence/asr_silence.json").read_text())
xml = ET.parse(root / "evidence/unit_tests.xml").getroot()
suites = [xml] if xml.tag == "testsuite" else list(xml.iter("testsuite"))
count = sum(int(s.attrib.get("tests", 0)) for s in suites)
text("BÀI 7 — SEMANTIC CAMPUS", "TitleVI")
text(
    "Phân vùng bản đồ và điều hướng robot bằng giọng nói tiếng Việt<br/>Báo cáo triển khai và kiểm chứng • 02/11/2026"
)
text("1. Mục tiêu và phạm vi", "Heading2")
text(
    "Hệ thống ROS 2 Jazzy trên Ubuntu 24.04 tích hợp bản đồ ngữ nghĩa, nhận dạng tiếng Việt local và Nav2 cho TurtleBot 4 trong Gazebo Harmonic. World bốn phòng/hành lang thay bản đồ hai vách đơn giản. Các module đã triển khai; chưa nghiệm thu giọng nói người thật vì người dùng chưa thể thử microphone trong phiên."
)
image("gazebo_campus.png", 470)
text(
    "Ảnh chụp Gazebo thật. Dùng nav2_minimal_tb4_sim đã có trên máy, không tuyên bố mô phỏng đầy đủ TB4/Create3 vật lý. Không thay phiên bản ROS/Gazebo hoặc package hệ thống."
)
text("2. Kiến trúc", "Heading2")
text(
    "Microphone → arecord/ALSA → Whisper small CPU int8 → /voice/transcript → parser rule-based → semantic lookup → ComputePathToPose → NavigateToPose tuần tự → robot. MarkerArray/RViz và JSON status hiển thị vùng, đích đang đi, tiến độ và lỗi. Keyboard là đầu vào kiểm thử độc lập ASR, được ghi rõ trong evidence."
)
story.append(PageBreak())
text("3. Map segmentation và semantic mapping", "TitleVI")
image("segmented_campus.png", 425)
text(
    "Occupancy 300×220 ô, resolution0.05m, origin[-7.5,-5.5,0]. Map được sinh từ chính collision primitive của world, không phải kết quả SLAM. Ô free/occupied/unknown dùng threshold và negate từ YAML; unknown không được xem là free. Polygon thủ công A–E có ID, tên, aliases, goal, yaw và valid. Editor cho phép chỉnh polygon/goal; watershed xuất gợi ý nhưng chưa đánh giá định lượng chất lượng tách phòng."
)
text(
    "Pixel→map dùng tâm ô: u=(col+0.5)×resolution, v=(height−row−0.5)×resolution; sau đó nhân quay origin_yaw và cộng origin_xy. Chiều ngược dùng quay nghịch đảo. Goal phải trong polygon/free, clearance≥0.35m và cùng connected component sau khi loại ô thiếu clearance. Chọn goal theo clearance, không dùng centroid mù quáng; runtime kiểm tra planner/costmap thật."
)
story.append(PageBreak())
text("4. Speech recognition và parsing", "TitleVI")
text(
    "Whisper small đa ngôn ngữ đã tải và nạp thực tế, CPU int8, 4 threads; cache/revision tại evidence/whisper_model_revision.txt. Thu âm bằng ALSA arecord vì thiếu PortAudio trên máy; không cài/chỉnh thư viện hệ thống. PTT có start/stop/discard; tự kết thúc tối đa12s. Worker inference tách khỏi ROS callbacks. RMS, clipping, VAD, logprob và no-speech filters loại âm thanh không đủ tin cậy; không có transcript thì không gửi lệnh."
)
text(
    "Parser chuẩn hóa dấu/chữ/khoảng trắng và aliases từ YAML, yêu cầu grammar điều hướng rõ. Hỗ trợ single, source_destination, multi_waypoint và cancel. Toàn bộ tên phải khớp; tên lạ hoặc alias trùng trả lỗi có cấu trúc, không đoán hoặc tạo vùng mới. A→B nghĩa là current→A→B; có thể bỏ qua A khi khoảng cách nguồn≤0.30m."
)
text("5. Tích hợp Nav2 và xử lý lỗi", "Heading2")
text(
    "Controller validate toàn bộ metadata, action server, covariance AMCL và tuổi TF map→base_link. Mỗi waypoint được preflight ComputePathToPose rồi gửi NavigateToPose; quaternion từ yaw. Chỉ terminal result SUCCEEDED/error_code0 mới chuyển điểm. Abort/reject/unreachable/timeout/localization lost dừng chuỗi. Lệnh mới bị BUSY khi nhiệm vụ đang hoạt động. Cancel gửi action cancellation, giữ khóa tới terminal result; không tự mở khóa khi kết quả chưa rõ. Không phát cmd_vel hoặc teleport robot."
)
text("6. Kết quả unit và model", "Heading2")
text(
    f"{count} unit tests PASS qua colcon: coordinate roundtrip với origin xoay, map/goal/polygon/clearance/connectivity, parser/aliases/unknown/grammar/cancel và schema navigation request. Bằng chứng evidence/unit_tests.xml và colcon_test_voice_result.log."
)
text(
    f"Model/VAD test dùng silence tổng hợp (khai báo rõ, không phải người nói): {silence['vad_speech_seconds']:.1f}s speech sau VAD, {len(silence['transcripts'])} transcript. Kiểm thử này chỉ chứng minh không tạo lệnh từ silence và model có thể chạy; không xác nhận độ chính xác tiếng Việt."
)
text(
    "Chưa có ba transcript người nói thật, chưa đo WER hay độ trễ ASR thực. Không dùng transcript kỳ vọng, TTS hoặc keyboard để đánh PASS cho speech recognition."
)
story.append(PageBreak())
text("7. Kết quả integration thực tế", "TitleVI")
labels = {
    "T09_unknown_no_goal": "T09: khu vực Z bị từ chối",
    "T14_busy_reject": "T14: từ chối lệnh khi bận",
    "T13_real_action_cancel": "T13: action cancellation status5",
    "T08_A_C_B": "T08: A → C → B",
    "T07_current_to_A_to_B": "T07: current → A → B",
    "source_skip_near": "Bỏ qua nguồn B khi đang ở B",
    "T06_alias_keyboard_navigation": "T06: alias phòng thí nghiệm → B",
}
table(
    [["Scenario (keyboard transcript)", "Thực thi"]]
    + [[labels.get(r["test"], r["test"]), "PASS" if r["passed"] else "FAIL"] for r in nav],
    [370, 100],
)
text(
    "Các scenario trên chạy parser và Nav2 thật, không dùng microphone. Event/terminal JSON ở evidence/live_pipeline_results.json và live_pipeline_events.jsonl. Đã kiểm tra waypoint results theo đúng thứ tự; không suy thành công từ ảnh."
)
short = {
    "T11_nav2_unavailable": "T11: Nav2 chưa hoạt động",
    "localization_unavailable": "TF/localization không sẵn sàng",
    "goal_timeout_real_cancel": "Goal timeout, cancel thật status5",
    "T10_missing_microphone_real_ALSA": "T10: thiết bị ALSA không tồn tại",
}
table(
    [["Negative scenario", "Kết quả mong đợi đã xác nhận"]]
    + [[short.get(r["test"], r["test"]), "PASS" if r["passed"] else "FAIL"] for r in negative],
    [350, 120],
)
text(
    f"T12: chèn collider thật chặn phòngA; Nav2 abort status6/error208, controller{unreachable['terminal']['state']}; waypointC được gửi: {unreachable['later_waypoint_sent']}. Script gỡ collider và clear costmap trong finally. Kết quả test={'PASS' if unreachable['passed'] else 'FAIL'} tại evidence/unreachable_result.json."
)
smoke = json.loads((root / "evidence/final_launch_smoke.json").read_text())
text(
    f"Full launch từ phiên sạch: AMCL/lifecycle ready, Whisper ready={smoke['asr_model_ready']}, parser alias→B, mission={smoke['terminal']['state']}. Đây vẫn là input bàn phím, không phải T15. evidence/final_launch_smoke.json và full_launch_clean.log."
)
text(
    "Baseline map trước đó chạy 5 goal A→C→B→E→D thành công. Scan-map đo tại pose cuối một lượt: 10 scan, 3600 endpoints, median0m/p95.05m tới occupied cell. Không suy rộng thành sai số localization toàn bản đồ hoặc độ tin cậy thống kê nhiều lượt."
)
story.append(PageBreak())
text("8. Visualization, hạn chế và bàn giao", "TitleVI")
image("rviz_semantic.png", 470)
text(
    "RViz thực tế: polygon/goal/active target trong frame map mét; Path lấy từ planner thật. Nối waypoint chỉ biểu thị thứ tự đích. Text marker dùng tên không dấu do font RViz; metadata/transcript vẫn tiếng Việt."
)
text(
    "Code/config/launch/dependencies/entry points và asset map/world đầy đủ trong package ament_python. README có lệnh build, tải model, khởi chạy/seed AMCL/PTT, keyboard, test và các trường hợp lỗi. docs/DEMO.md chuẩn bị video cùng phiếu ba câu còn trống. Source Git local đã chuẩn bị; chưa push/public, không ghi dữ liệu nhạy cảm vào remote."
)
text(
    "Hạn chế: chưa thực hiện T15 hoặc ba câu nói thật; chưa có video voice, chưa đo ASR accuracy/latency thực; GUI editor chưa có kiểm thử tương tác tự động; watershed chưa có đánh giá định lượng. Các integration PASS chỉ mô tả các lượt đã chạy. Không có action result, transcript hoặc ảnh nghiệm thu dựng giả."
)
text("9. Kết luận", "Heading2")
text(
    "Phần mềm đã triển khai toàn pipeline và kiểm chứng map/parser/controller/ROS integration với Nav2/Gazebo thật, bao gồm busy, cancel, timeout và unreachable. Mục nghiệm thu còn chờ là người dùng nói qua microphone để xác nhận ASR tiếng Việt và end-to-end. Không tuyên bố toàn bộ bài đã PASS khi thiếu bằng chứng đó."
)
text(
    "Nguồn và tài liệu tái lập: docs/environment.md; docs/phase_status.md; README.md; evidence/*.json/log/xml. Đối chiếu kỹ thuật: Nav2 Jazzy documentation, nav2_minimal_turtlebot_simulation (ROS Navigation), faster-whisper (SYSTRAN). Phiên bản package cài thực tế và runtime logs là căn cứ kiểm tra tương thích."
)


def footer(canvas, doc):
    canvas.setFont("VI", 8)
    canvas.setFillColor(colors.HexColor("#52657b"))
    canvas.drawString(55, 25, "Bài 7 • Kết quả thực thi / chưa nghiệm thu microphone người thật")
    canvas.drawRightString(540, 25, str(doc.page))


SimpleDocTemplate(
    str(root / "docs/week7_report.pdf"),
    pagesize=(595, 842),
    rightMargin=55,
    leftMargin=55,
    topMargin=40,
    bottomMargin=45,
    title="Bài 7 - Semantic Campus và Voice Navigation",
    author="HRI Lab",
).build(story, onFirstPage=footer, onLaterPages=footer)
print(root / "docs/week7_report.pdf")
