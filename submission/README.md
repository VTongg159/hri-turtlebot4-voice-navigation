# Bộ bàn giao Bài thực hành 07

Source public: [VTongg159/hri-turtlebot4-voice-navigation](https://github.com/VTongg159/hri-turtlebot4-voice-navigation).

| Sản phẩm | File |
|---|---|
| LaTeX hoàn chỉnh, chưa biên dịch, hình là placeholder | [bao_cao_bai7.tex](../docs/bao_cao_bai7.tex) |
| Occupancy gốc | [PGM](maps/pairs_lab.pgm), [YAML](maps/pairs_lab.yaml), [ảnh PNG](maps/pairs_lab_original.png) |
| Hình occupancy có chú giải và START (Hình 4) | [pairs_lab_occupancy_annotated.png](maps/pairs_lab_occupancy_annotated.png) |
| Hình 6: quy ước pixel và map | [PNG](figures/pairs_lab_pixel_map_coordinates.png), [SVG](figures/pairs_lab_pixel_map_coordinates.svg) |
| Hình 7: chụp trực tiếp lượt chạy ngày10/11/2026 | [Terminal sau khi đến đích](figures/figure7_terminal_live.png), [ASR/parser](figures/figure7_ASR_parser_live.png), [video terminal](figure7_terminal_live.mp4), [log gốc](evidence/figure7_terminal_live.log) |
| Hình 13: RViz sau khi đến phòng UAV | [Ảnh RViz trực tiếp](figures/figure13_rviz_UAV_succeeded.png), [đối chiếu ROS](evidence/figure13_rviz_verification.json) |
| Hình 14: khung video voice tại02:19 | [Ảnh PNG](figures/figure14_voice_video_UAV_succeeded.png), [nguồn và mốc video](evidence/figure14_video_frame.json) |
| Hình 15: B/D/F/E và kết thúc ở sảnh | [Ảnh ghép PNG](figures/figure15_room_arrivals.png), [nguồn ảnh](evidence/figure15_sources.json) |
| Measured trajectory: A→B→D→C→E→F | [trajectory_pairs.png](figures/trajectory_pairs.png), [TF/AMCL và results](evidence/trajectory_pairs/), [matplotlib script](../scripts/render_pairs_trajectory.py) |
| RViz multi-waypoint A→C→D | [rviz_multiwaypoint_plan.png](figures/rviz_multiwaypoint_plan.png), [log và plan](evidence/rviz_multiwaypoint/) |
| Voice từ chối khu vực Z, robot IDLE | [Terminal + RViz](figures/unknown_region_voice_idle_rviz.png), [terminal lúc chạy](figures/unknown_region_voice_idle.png), [log ASR/parser/TF](evidence/unknown_region_voice/) |
| T07: microphone F→A→B | [Clip bổ sung 1:50](source_destination_voice_demo.mp4), [log và số liệu](evidence/source_destination_voice/), [LaTeX đã điền](../docs/source_destination_results.tex) |
| Ảnh phân vùng A–F | [pairslab_segmentation.png](maps/pairslab_segmentation.png) |
| Polygon, tên, aliases và goal | [pairs_regions.yaml](config/pairs_regions.yaml) |
| Kiểm tra sáu goal | [goals_validation.json](evidence/goals_validation.json) |
| Video Full HD, khoảng 6:16 | [PAIRS_Lab_Demo_1080p.mp4](PAIRS_Lab_Demo_1080p.mp4) |
| Mốc thời gian video | [CHAPTERS.md](CHAPTERS.md) |
| 14 ảnh thật để chèn báo cáo | [figures/](figures/) |
| Kịch bản và lời dẫn | [KICH_BAN_QUAY_PAIRSLAB.md](../docs/KICH_BAN_QUAY_PAIRSLAB.md) |
| Build, 90 test, lint và formatter | [source_validation.json](evidence/source_validation.json) |
| Hash và danh mục sản phẩm | [manifest.json](manifest.json) |

## Video có đúng luồng yêu cầu không?

**Có, từ khoảng 01:07:** người dùng nói “Đi đến phòng UAV” vào microphone → Whisper ASR → parser xác định A → Nav2 → TurtleBot4 di chuyển và báo SUCCEEDED. Audio thuộc cùng lượt quay. Lượt đầu NO_SPEECH, lượt sau đạt; bản dựng giữ lượt đạt. Đây là cảnh voice mới, khác phiên nghiệm thu ba câu trước.

**Tour năm phòng dùng lệnh văn bản**, đi tới UAV, tay máy, HRI/Unitree G1, TurtleBot, Go2 rồi về sảnh. Video ghi rõ nguồn lệnh và tour tăng tốc2x. Không gọi các phần văn bản là kiểm thử giọng nói.

Lần F→E đầu mất định vị; sau cập nhật laser cho AMCL khi robot đứng yên, E→C đạt. Đoạn nối sau AMCL được ghi nhãn. Video có cắt dựng, không tuyên bố một lượt liên tục không lỗi. Raw clips/audio và log đầy đủ giữ local, không đưa WAV cá nhân lên source public.

Video hiện chưa quay riêng đủ mọi dạng trong sáu demo của đề (gọi ID, source→destination, câu Z sai, multi-waypoint voice); xem trạng thái cụ thể trong kịch bản và báo cáo. Phiên ba câu trước có audio/log và receipt T15 cho A, E, A→C→D, nhưng không có video cùng lượt.

## Phương pháp và phạm vi thực nghiệm

- Occupancy được sinh từ collision geometry của world, **không phải map SLAM**.
- Phân vùng chính là polygon có giám sát; tên phòng được gán theo thiết kế. Watershed chỉ xuất gợi ý, chưa có đánh giá IoU.
- Sáu goal được kiểm tra free/polygon/clearance≥0.38m và liên thông; runtime còn phải qua Nav2 planner/costmap.
- G1/Go2/X500/UR và các TB4 trưng bày là model tĩnh; TurtleBot4 Nav2 riêng là robot di chuyển.
- `evidence/historical_campus/` là kết quả integration scene cũ, không xác nhận đã chạy lại trên PAIRS.
- Receipt có đường dẫn raw local để truy vết; các file raw đó cố ý không nằm trong bản public. `manifest.json` liệt kê những file thực sự bàn giao.

Giữ cấu trúc `config/` và `maps/` khi tải metadata để đường dẫn `../maps/pairs_lab.yaml` tiếp tục hợp lệ. Source package chứa bản map và metadata tương ứng để chạy ROS.

Hình7 mới là ảnh chụp trực tiếp cửa sổ terminal khi người dùng nói qua microphone thật ngày10/11/2026. Bộ ghi hình được bật trước lần thu âm; ảnh/video giữ nguyên bytes, có JSON parser và action terminal Nav2 cùng command_id. Phiên ghi hình có2 lượt: ASR nhận UAB→UNKNOWN_REGION (không gửi goal), sau đó nhận đúng UAV→A→SUCCEEDED. Các ảnh biên soạn lại đã được rút khỏi bộ bàn giao. Xem evidence/figure7_live_acceptance.json để đối chiếu thời điểm, WAV hash, event và hash ảnh/video.

Hình13 chụp RViz đang chạy sau nhiệm vụ thật trong Hình7. Đường xanh là /voice/planned_path (đường lập kế hoạch được giữ lại), không phải quỹ đạo đã đo. Robot TF hiện tại nằm trong A. Nhãn SUCCEEDED và command_id được node marker cập nhật từ /voice/navigation_status; không chèn chữ lên ảnh sau khi chụp. Cấu hình tái mở: src/tb4_voice_navigation/rviz/pairs_lab_report.rviz.

Hình14 lấy khung02:19 của video demo09/11/2026, trong phần voice bắt đầu01:07. Bản dành cho báo cáo giữ nguyên pixel và tông màu của cửa sổ Gazebo, bố trí lại bảng phụ sang trắng–đen và chuyển bản đồ phụ sang grayscale; transcript/pose/trạng thái giữ đúng khung gốc. [Khung gốc để đối chiếu](figures/figure14_voice_video_original.png). Không phải ảnh terminal. Có thể tạo lại bằng `python scripts/style_figure14.py`.

Video demo đã cập nhật bảng phụ trắng–đen, nhãn kỹ thuật tiếng Anh và chapter titles. Transcript tiếng Việt giữ nguyên ASR thực tế; audio AAC giữ nguyên từng packet. Xem [video_style.json](evidence/video_style.json) để đối chiếu bản gốc và cách ánh xạ ROS events vào timeline.

Trajectory dùng lượt Nav2 riêng mới, ghi map→base_link TF 5 Hz và AMCL, đúng A→B→D→C→E→F. Sáu goal đều SUCCEEDED và pose cuối nằm trong vùng tương ứng. Đây là lượt đo riêng, khác thứ tự tour trong video. Tạo lại hình bằng `python scripts/render_pairs_trajectory.py` từ dữ liệu public.

T07 đã thực hiện riêng bằng microphone: từ F, nói “Đi từ khu vực A đến khu vực B”, parser [A,B], Nav2 lần lượt A rồi B đều SUCCEEDED. Thời gian hai chặng: 57,049 s và 41,801 s. Clip terminal thật được nối từ khoảng04:26, tốc độ1×; video hiện dài khoảng6:16. Ảnh RViz sau nhiệm vụ: [source_destination_rviz_succeeded.png](figures/source_destination_rviz_succeeded.png). Xem attempts.json để phân biệt6lượt thu của toàn phiên với2lượt dùng cấu hình ASR cuối.
