#!/usr/bin/env python3
"""Scene addendum using real screenshots and execution results."""

from pathlib import Path
import json
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table, TableStyle, PageBreak

root = Path(__file__).resolve().parents[1]
e = root / "evidence/pairslab_redesign"
nav = json.loads((e / "navigation.json").read_text())
pipe = json.loads((e / "pipeline.json").read_text())
scan = json.loads((e / "scan_alignment.json").read_text())
assert len(nav) == 6 and all(r["result"] == "SUCCEEDED" for r in nav)
assert pipe["passed"]
voice_path = e / "voice_acceptance.json"
voice = json.loads(voice_path.read_text()) if voice_path.exists() else None
film_dir = root / "deliverables/pairslab_demo_20261109"
film_manifest = film_dir / "render_manifest.json"
film = json.loads(film_manifest.read_text()) if film_manifest.exists() else None
for name, file in [("VI", "DejaVuSans.ttf"), ("VIBold", "DejaVuSans-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, "/usr/share/fonts/truetype/dejavu/" + file))
styles = getSampleStyleSheet()
for s in styles.byName.values():
    s.fontName = "VI"
styles["BodyText"].leading = 15
styles["BodyText"].spaceAfter = 8
styles["Heading2"].fontName = "VIBold"
styles.add(
    ParagraphStyle(
        name="TitleVI",
        fontName="VIBold",
        fontSize=21,
        leading=28,
        textColor=colors.HexColor("#14283f"),
        spaceAfter=15,
    )
)
story = []


def text(value, style="BodyText"):
    story.append(Paragraph(value, styles[style]))


def image(file, w):
    from PIL import Image as PILImage

    p = root / "docs" / file
    with PILImage.open(p) as im:
        x, y = im.size
    story.append(Image(str(p), width=w, height=w * y / x))


def table(rows, widths):
    t = Table(
        [[Paragraph(str(v), styles["BodyText"]) for v in row] for row in rows],
        colWidths=widths,
        repeatRows=1,
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e1f0f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)


text("PAIRS ROBOTICS RESEARCH LAB", "TitleVI")
text(
    "Bài thực hành 7 — cập nhật môi trường 09/11/2026<br/>Ubuntu24.04 / ROS2 Jazzy / Gazebo Harmonic"
)
image("pairslab_overview.png", 475)
text(
    "Bố cục 28×20m, năm khu nghiên cứu nối với sảnh triển lãm rộng4m; cửa danh nghĩa2.2m, sáu đích điều hướng. Mesh robot, logo, signage và nội thất được đóng gói để chạy offline. Ảnh chụp từ Gazebo thật."
)
table(
    [
        ["ID", "Không gian", "Thiết bị chính"],
        ["A", "UAV", "X500, lồng thử bay, mocap"],
        ["B", "Tay máy", "UR5e + UR3e, bàn thao tác"],
        ["C", "Sảnh PAIRS", "Logo PAIRS + ĐHQGHN gốc"],
        ["D", "HRI humanoid", "Unitree G1 29DoF"],
        ["E", "Chó robot", "Hai Unitree Go2, bậc địa hình"],
        ["F", "Robot di động", "Hai TB4, docks, làn thử"],
    ],
    [35, 145, 295],
)
story.append(PageBreak())
text("UNITREE / HRI & LEGGED ROBOTICS", "TitleVI")
image("pairslab_hri.png", 475)
text(
    "G1 dùng URDF/STL chính thức Unitree, pose từ forward kinematics, đứng trên sân HRI. Máy trạm và vị trí tương tác tách khỏi lối robot điều hướng."
)
image("pairslab_go2.png", 475)
text(
    "Go2 dùng DAE/URDF gốc Unitree; một robot trên sân thử và một trên bàn bảo trì. Các bậc có collision. G1/Go2 trong scene là exhibit tĩnh, chưa có controller đi bộ; robot Nav2 là một TurtleBot4 mô phỏng riêng."
)
story.append(PageBreak())
text("MANIPULATION / UAV", "TitleVI")
image("pairslab_manipulation.png", 475)
text(
    "UR5e/UR3e lấy từ ur_description Jazzy3.5.1, có bục và không gian thao tác riêng. Source meshes giữ nguyên; đặt pose bằng chuỗi joint transforms."
)
image("pairslab_uav.png", 475)
text(
    "X500 lấy từ PX4 x500_base sẵn có, giữ mesh và license. Chỉ copy visuals, bỏ plugin motor/sensor; các legacy material script được chuyển sang RGBA/PBR tương đương cho Harmonic. Đây là exhibit, không tuyên bố UAV đang bay tự hành."
)
story.append(PageBreak())
text("BRANDING / SEMANTIC MAP", "TitleVI")
image("pairslab_branding.png", 475)
text(
    "Logo PAIRS Lab và ĐHQGHN là ảnh gốc được đối chiếu với mẫu người dùng, copy nguyên PNG không vẽ lại; gắn thành texture riêng trên biển hiệu và nền sảnh. Nguồn/model commit/license ở PAIRSLAB_ASSETS.md và asset_manifest.json."
)
image("pairslab_segmentation.png", 365)
text(
    "Map580×420 ô, resolution0.05m, origin[-14.5,-10.5,0]; sinh từ cùng collision geometry, không gọi là SLAM. Goal thuộc free/polygon, clearance≥0.38m và cùng navigable component với spawn(-11,0). Unknown không xem là free. Runtime vẫn kiểm tra Nav2 planner/costmap thật."
)
story.append(PageBreak())
text("KẾT QUẢ KIỂM CHỨNG", "TitleVI")
table(
    [["Waypoint", "Result", "Wall time(s)", "Recovery"]]
    + [[r["region"], r["result"], r["elapsed_wall_s"], r["recoveries"]] for r in nav],
    [70, 170, 135, 100],
)
text(
    "Sáu goal đều có terminal action result thật; chi tiết navigation.json/log. Đây là baseline Nav2, không dùng microphone. Một lượt thành công không xác nhận độ tin cậy thống kê nhiều lượt."
)
text(
    "87 unit tests PASS: toàn bộ suite cũ và các test map mới, doorway connectivity, aliases UAV/HRI/Go2/TurtleBot, mesh/texture URI portable, nguồn Unitree và static exhibits. gz sdf -k trả Valid. Bằng chứng unit_test_result.log/pytest.xml và sdf_validation.log."
)
text(
    f"Pipeline mới: input bàn phím ‘Đi đến phòng TurtleBot’ → F → {pipe['terminal']['state']}. Bằng chứng pipeline.json và verified_launch.log. AMCL tự nhận pose spawn ngay khi mở mô phỏng mới; không teleport và không chờ người dùng nhập pose quá muộn."
)
text(
    f"Đo scan/map tại pose thử: {scan['scan_count']} scans, {scan['endpoint_count']} endpoints, median={scan['quantiles_m']['0.5']:.3f}m, p95={scan['quantiles_m']['0.95']:.3f}m. Không suy rộng thành sai số localization toàn scene; còn outliers và chưa đánh giá nhiều vị trí."
)
text("Giới hạn và bước tiếp theo", "Heading2")
text(
    "T15 đã PASS với ba câu người nói thật, có các lượt thử lại; chi tiết ở trang nghiệm thu giọng nói tiếp theo. Video demo có audio cùng lượt quay đã được bổ sung ở phần cuối báo cáo. Robot trưng bày chưa có motion controller; editor/watershed chưa đánh giá chất lượng phòng tự động."
    if voice
    else "T15 và ba câu người nói thật chưa thực hiện. Robot trưng bày chưa có motion controller; editor/watershed chưa đánh giá chất lượng phòng tự động."
)
text(
    "Cách chạy/tái tạo: README.md; công cụ camera pairslab_camera.py; generator generate_pairslab_world.py; model assets Unitree commit725b59b6de39a26c425632120c89f23c49a36f1e. Giữ bản campus cũ và log cũ để truy vết; chưa push/public repository."
)
if voice:
    assert voice["status"] == "PASS"
    story.append(PageBreak())
    text("NGHIỆM THU GIỌNG NÓI THẬT", "TitleVI")
    text(
        "Ngày09/11/2026, người dùng thực hiện trực tiếp qua microphone. Luồng: audio thật → Whisper CPU int8 → transcript → parser → Nav2 → TurtleBot4 trong Gazebo. Ba câu đều có lượt đạt SUCCEEDED; không dùng keyboard/TTS thay microphone."
    )
    table(
        [["Câu", "Transcript thật của lượt đạt", "Route", "Lượt đạt"]]
        + [
            [
                r["trial"],
                r["actual_transcript"],
                " → ".join(r["visited_waypoints"]),
                r["attempts_required"],
            ]
            for r in voice["successes"]
        ],
        [35, 290, 95, 55],
    )
    text(
        "Kết quả:3 câu thành công sau tổng6 lượt ghi; chỉ1/3 câu đạt ngay lượt đầu. Có2 transcript sai (“chó rối”, “phẩm UAV…”) bị UNKNOWN_REGION và1 NO_SPEECH; các lượt này được giữ nguyên, không sửa thành PASS. Transcript “cho robot” ở lượt đạt câu2 thiếu dấu nhưng parser chuẩn hóa dấu khớp đúng “chó robot”."
    )
    table(
        [["Câu", "ASR phase(s)", "Transcript → mission end(s)", "Nav2"]]
        + [
            [
                r["trial"],
                f"{r['asr_phase_wall_s']:.3f}",
                f"{r['transcript_to_mission_end_wall_s']:.3f}",
                r["nav_result"],
            ]
            for r in voice["successes"]
        ],
        [45, 130, 200, 100],
    )
    text(
        "ASR phase đo giữa các trạng thái TRANSCRIBING và TRANSCRIPT đã publish. Một người dùng, một phiên có retries; không suy thành độ chính xác ASR tổng quát hoặc WER=0."
    )
    text(
        "Bằng chứng: voice_acceptance.json đối chiếu actual_transcript với parser.command_id, thứ tự WAYPOINT_SUCCEEDED và terminal action status4/error0. AudioWAV16kHz mono/16bit được kiểm tra duration và SHA256. Raw results/events/ASR/terminal log và audio giữ trong evidence/voice_demo/pairslab_live/, được Git ignore. Script tái kiểm tra: scripts/summarize_voice_trials.py."
    )
    text(
        (
            "Video demo bổ sung đã quay riêng với một câu microphone thật và tour đủ năm phòng; xem phần sau. "
            if film
            else "Còn cần quay video demo. "
        )
        + "Repository chưa push/public. Mọi lượt voice chưa đạt vẫn được ghi rõ trong VOICE_TEST_RESULTS.md."
    )

if film:
    assert film["decode_check"] == "PASS" and film["coverage"]["passed"]
    story.append(PageBreak())
    text("VIDEO DEMO VÀ TUYẾN THAM QUAN", "TitleVI")
    text(
        "Bản dựng: PAIRS_Lab_Demo_1080p.mp4; 1920×1080, 15fps, "
        + f"{film['duration_s'] / 60:.2f}"
        + " phút. Mở từ deliverables/pairslab_demo_20261109/. Kịch bản: docs/KICH_BAN_QUAY_PAIRSLAB.md; các mốc thời gian: CHAPTERS.md trong thư mục video."
    )
    text(
        "Phần giọng nói ghi ở tốc độ thật, audio lấy từ microphone cùng lượt quay: “"
        + film["voice"]["actual_transcript"]
        + "”. Transcript thật đi qua parser và Nav2 đến A; command_id: "
        + film["voice"]["command_id"]
        + ". Các phòng tiếp theo sử dụng lệnh văn bản, được ghi nhãn nguồn và tăng tốc 2x trong bản dựng."
    )
    text(
        "Phiên voice quay mới có2 lượt ghi: lượt đầu NO_SPEECH, lượt sau nhận đúng và đến A. Bản dựng chỉ dùng lượt đạt; raw video/WAV/log giữ cả hai. Không tính đây là thành công ngay lượt đầu."
    )
    rows = [["ID", "Khu nghiên cứu", "Pose đến đích (m)", "Kết quả"]]
    rows.append(["A", "UAV", "Xem raw voice + filmed_acceptance.json", "SUCCEEDED / voice"])
    for r in film["coverage"]["results"]:
        pos = r["arrival_pose"]
        rows.append(
            [
                r["region"],
                {"B": "Tay máy", "D": "HRI / G1", "C": "Sảnh", "F": "TurtleBot", "E": "Go2"}[
                    r["region"]
                ],
                f"({pos['x']:.2f}, {pos['y']:.2f})",
                "SUCCEEDED / trong vùng" if pos["inside_region"] else "Ngoài vùng",
            ]
        )
    table(rows, [35, 130, 175, 135])
    text(
        "Lưu ý thực nghiệm: lần đi F→E đầu bị LOCALIZATION_LOST (covariance x vượt ngưỡng0.5). Nhiệm vụ được hủy; sau cập nhật laser đứng yên bằng request_nomotion_update, AMCL hội tụ và lần đi tiếp E→C đạt. Giữ nguyên clip/log thất bại; bản nộp có cắt dựng và ghi nhãn đoạn nối sau AMCL. Không teleport robot hoặc bỏ kiểm tra định vị."
    )
    text(
        "Đã kiểm tra giải mã toàn bộ video, độ phân giải, audio AAC và đầy đủ A/B/D/E/F cùng sảnh C. Receipt: render_manifest.json, coverage.json; clips gốc1x và WAV giữ cùng thư mục. Đồng bộ audio dựa vào wall time sự kiện RECORDING; có sai số khởi động thiết bị/capture dưới mức giây, không khẳng định đồng bộ từng frame."
    )
    story.append(PageBreak())
    text("ẢNH CHỤP TỪ PHIÊN QUAY", "TitleVI")
    for name, caption in [
        ("environment_overview", "Toàn cảnh PAIRS Lab, năm khu và sảnh"),
        ("environment_go2", "Khu robot bốn chân Unitree Go2"),
    ]:
        file = film_dir / "stills" / f"{name}.png"
        with __import__("PIL.Image", fromlist=["Image"]).open(file) as im:
            w, h = im.size
        story.append(Image(str(file), width=420, height=420 * h / w))
        text(caption)


def foot(canvas, doc):
    canvas.setFont("VI", 8)
    canvas.setFillColor(colors.HexColor("#536b80"))
    canvas.drawString(55, 25, "PAIRS Lab / Bài7 / 09.11.2026 / Screenshot và dữ liệu thực thi")
    canvas.drawRightString(540, 25, str(doc.page))


SimpleDocTemplate(
    str(root / "docs/pairslab_scene_report.pdf"),
    pagesize=(595, 842),
    leftMargin=55,
    rightMargin=55,
    topMargin=40,
    bottomMargin=45,
    title="PAIRS Robotics Research Lab - Scene update",
    author="HRI Lab",
).build(story, onFirstPage=foot, onLaterPages=foot)
print(root / "docs/pairslab_scene_report.pdf")
