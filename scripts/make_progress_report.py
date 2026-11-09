#!/usr/bin/env python3
"""Build a progress report from recorded navigation/scan results, not invented data."""

from pathlib import Path
import json
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
pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(
    TTFont("DejaVuBold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
)
styles = getSampleStyleSheet()
for style in styles.byName.values():
    style.fontName = "DejaVu"
styles.add(
    ParagraphStyle(
        name="TitleVI",
        fontName="DejaVuBold",
        fontSize=21,
        leading=29,
        textColor=colors.HexColor("#172b43"),
        spaceAfter=20,
    )
)
styles["BodyText"].leading = 16
styles["BodyText"].spaceAfter = 10
styles["Heading2"].fontName = "DejaVuBold"
story = []


def text(value, style="BodyText"):
    story.append(Paragraph(value, styles[style]))


def image(name, width):
    from PIL import Image as PILImage

    path = root / "docs" / name
    with PILImage.open(path) as im:
        w, h = im.size
    story.append(Image(str(path), width=width, height=width * h / w))


text("BÀI 7 — SEMANTIC CAMPUS", "TitleVI")
text("Báo cáo tiến độ Phase 1–2 • 02/11/2026 • Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic")
text("Mục tiêu và kiến trúc", "Heading2")
text(
    "Thay bản đồ hai vách đơn giản bằng không gian bốn phòng, hành lang và nội thất để phục vụ phân vùng và điều hướng giọng nói. Pipeline dự kiến: microphone → ASR tiếng Việt → parser → semantic map → action Nav2 → TurtleBot 4. Báo cáo này xác nhận phần map và baseline; phần voice chưa hoàn thành."
)
image("gazebo_campus.png", 470)
text(
    "Ảnh chụp cửa sổ Gazebo thực tế. Mô hình TB4 tối giản từ nav2_minimal_tb4_sim; không dùng robot mô phỏng giả hoặc kết quả action dựng sẵn."
)
story.append(PageBreak())
text("Phân vùng và tọa độ", "TitleVI")
image("segmented_campus.png", 425)
text(
    "Occupancy 300 × 220 ô, 0.05 m/ô, origin [-7.5,-5.5,0]. Map prior được sinh từ cùng các collision primitive của world; không gọi đây là kết quả SLAM. Unknown bị loại khỏi không gian đi được. Polygon thủ công xác định A–E, alias và yaw; editor cho phép chỉnh sửa. Watershed chỉ là gợi ý chưa đánh giá định lượng chất lượng phân vùng."
)
text(
    "Pixel → map dùng tâm ô và đảo trục hàng ảnh, sau đó quay theo origin yaw và tịnh tiến. Chiều ngược dùng phép quay nghịch đảo. Goal phải thuộc polygon, nằm trên free cell, clearance ≥ 0.35 m và cùng thành phần navigable với anchor (-5.5,0). Clearance trừ nửa đường chéo ô để kiểm tra bảo thủ."
)
story.append(PageBreak())
text("Kết quả thực thi và giới hạn", "TitleVI")
nav = json.loads((root / "evidence/campus_navigation.json").read_text())
scan = json.loads((root / "evidence/scan_alignment.json").read_text())
rows = [["Waypoint", "Result", "Thời gian (s)", "Recovery"]] + [
    [r["region"], r["result"], str(r["elapsed_wall_s"]), str(r["recoveries"])] for r in nav
]
table = Table(rows, colWidths=[85, 145, 130, 90])
table.setStyle(
    TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ]
    )
)
story.append(table)
story.append(Spacer(1, 16))
text(
    "Kết quả trên lấy từ evidence/campus_navigation.json và log action thật. Thời gian là wall-clock của một lượt, không phải thống kê nhiều lần. Last feedback trong JSON không phải pose cuối chính xác tại terminal result."
)
text(
    f"Đo khớp LiDAR: {scan['scan_count']} scan, {scan['endpoint_count']} endpoints, median={scan['quantiles_m']['0.5']:.2f} m, p95={scan['quantiles_m']['0.95']:.2f} m tới occupied cell gần nhất. Dùng TF theo timestamp scan. Đây là phép đo tại pose cuối lượt, không chứng minh độ chính xác toàn cục."
)
text(
    "29 unit tests PASS: map classification, phép đổi tọa độ với origin xoay, polygon lỗi, goal occupied/unknown/ngoài vùng/thiếu clearance, semantic lookup và kết nối cửa. Bằng chứng: evidence/pytest.xml; build: evidence/build.log; colcon test: evidence/colcon_test_result.log. Các bước tái lập ở README.md."
)
text("Hạn chế và bước tiếp theo", "Heading2")
text(
    "Chưa nghiệm thu T05–T15: ASR, parser, controller giọng nói, cancel/busy/timeout và end-to-end microphone thật. Chưa đánh giá vật cản động, nhiều lượt navigation hoặc chất lượng watershed. Cần kiểm tra gain microphone vì mẫu probe có clipping. Repository chưa được public. Bản đồ mới đã có baseline để tiếp tục tích hợp giọng nói."
)
text(
    "Kết luận: campus mới đáp ứng bước chuẩn bị map/semantic và đã chạy thật năm waypoint. Không tuyên bố hoàn thành toàn bộ bài thực hành."
)
SimpleDocTemplate(
    str(root / "docs/phase1_2_report.pdf"),
    pagesize=(595, 842),
    rightMargin=55,
    leftMargin=55,
    topMargin=45,
    bottomMargin=45,
).build(story)
print(root / "docs/phase1_2_report.pdf")
