# Trạng thái scene PAIRS Lab — 09/11/2026

Bản scene mới thay campus đơn giản làm mặc định. Giữ nguyên asset/log cũ để truy vết lịch sử; các kết quả dưới đây dựa vào evidence/pairslab_redesign/.

- World pairs_lab.sdf: 28×20m, năm khu UAV/tay máy/HRI humanoid/Go2/TurtleBot và một sảnh. 564 visual kiến trúc gộp trong một static body, 105 footprint collision ở chiều cao robot. Logo PAIRS và ĐHQGHN là PNG gốc, kiểm tra file hashes trong asset_manifest.json.
- Robot nhập thật: Unitree G1 29DoF, hai Unitree Go2, UR5e, UR3e, hai X500, hai TB4 exhibit. Chỉ visuals và joint pose kinematics được dùng cho exhibit; không có controller chuyển động hoặc plugin sensor/TF trùng. Robot Nav2 là TB4 riêng.
- Map580×420, resolution0.05, origin[-14.5,-10.5,0]. Sinh từ cùng collision geometry, không phải SLAM. Metadata pairs_regions.yaml có 6 vùng A–F, aliases chuyên biệt, goal/yaw có clearance≥0.38m và connectivity. Tên chung “phòng thí nghiệm” được từ chối thay vì đoán một trong năm phòng.
- 87 unit tests PASS (71 test cũ + 16 test scene/alias/resource mới). unit_tests.log, unit_test_result.log và pytest.xml. Lượt test đầu bắt một legacy Gazebo material script của X500; conversion đã đổi sang RGBA/PBR portable, giữ nguyên source và license gốc; lượt cuối tất cả PASS.
- gz sdf -k xác nhận world Valid (sdf_validation.log).
- **Native Nav2 thật:** A → B → D → C → E → F đều SUCCEEDED, không recovery trong lượt đo; navigation.json và navigation.log. Chưa suy thành độ tin cậy nhiều lượt.
- **Scan alignment:** 10 scan/3600 endpoints, median0m, p95≈0.101m tới occupied cell tại pose đo (scan_alignment.json). Một số điểm outlier; không coi đây là sai số localization trên toàn scene.
- **Pipeline mới:** parser/controller input bàn phím “Đi đến phòng TurtleBot” → F; pipeline.json và pipeline_events.json ghi result thật. Không dùng microphone trong test này.
- Khởi động lại sau đóng gói được kiểm tra riêng. AMCL tự seed pose(-11,0,0) trong pairs_nav2_params.yaml ngay khi mở scene mới để Nav2 không timeout trong lúc chờ người dùng đặt pose. Không teleport. Các log final_launch.log/final_localization.log là lượt phát triển từng gặp timeout khi seed thủ công muộn; lượt verified_launch.log/pipeline.json là căn cứ cuối.
- **Cập nhật nghiệm thu giọng nói thật:** người dùng đã thử microphone ngày09/11/2026; T15 PASS với A, E và A→C→D. Có6 lượt ghi:3 thành công,2 transcript bị UNKNOWN_REGION và1 NO_SPEECH. Câu1 đạt lượt1, câu2 đạt lượt3, câu3 đạt lượt2. Audio16kHz mono và terminal action status4/error0 đã đối chiếu theo command_id; xem voice_acceptance.json và VOICE_TEST_RESULTS.md.
- Model cache bị thiếu khi bắt đầu buổi thử đã được khôi phục; dịch vụ ASR đã được nạp lại. Terminal hướng dẫn dùng Terminator không phụ thuộc D-Bus và chỉ thu khi người dùng nhấn Enter. Không sửa transcript hoặc aliases để ép các lượt sai thành PASS.
- Đã bổ sung video 4:26, đủ5phòng+sảnh: một câu microphone mới→A; tour văn bản ghi nhãn2x. Có lần mất định vị ở F→E, cập nhật AMCL đứng yên rồi E→C đạt; bản dựng ghi rõ đoạn nối. Xem VIDEO_DEMO_RESULTS.md. Phiên ba câu trước vẫn có audio/log riêng và retries; không suy thành độ chính xác ASR tổng quát.

Ảnh docs/pairslab_*.png là screenshot Gazebo thật hoặc ảnh map tính từ dữ liệu, không phải ảnh dựng nghiệm thu. Báo cáo addendum pairslab_scene_report.pdf, hướng dẫn README.md, demo mới DEMO_PAIRSLAB.md. Source và sản phẩm public: https://github.com/VTongg159/hri-turtlebot4-voice-navigation; xem submission/README.md. Raw WAV giữ local.
