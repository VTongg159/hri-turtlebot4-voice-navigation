# Bộ bàn giao Bài thực hành 07

Source public: [VTongg159/hri-turtlebot4-voice-navigation](https://github.com/VTongg159/hri-turtlebot4-voice-navigation).

| Sản phẩm | File |
|---|---|
| LaTeX hoàn chỉnh, chưa biên dịch, hình là placeholder | [bao_cao_bai7.tex](../docs/bao_cao_bai7.tex) |
| Occupancy gốc | [PGM](maps/pairs_lab.pgm), [YAML](maps/pairs_lab.yaml), [ảnh PNG](maps/pairs_lab_original.png) |
| Hình occupancy có chú giải và START (Hình 4) | [pairs_lab_occupancy_annotated.png](maps/pairs_lab_occupancy_annotated.png) |
| Ảnh phân vùng A–F | [pairslab_segmentation.png](maps/pairslab_segmentation.png) |
| Polygon, tên, aliases và goal | [pairs_regions.yaml](config/pairs_regions.yaml) |
| Kiểm tra sáu goal | [goals_validation.json](evidence/goals_validation.json) |
| Video Full HD, khoảng 4:26 | [PAIRS_Lab_Demo_1080p.mp4](PAIRS_Lab_Demo_1080p.mp4) |
| Mốc thời gian video | [CHAPTERS.md](CHAPTERS.md) |
| 14 ảnh thật để chèn báo cáo | [figures/](figures/) |
| Kịch bản và lời dẫn | [KICH_BAN_QUAY_PAIRSLAB.md](../docs/KICH_BAN_QUAY_PAIRSLAB.md) |
| Build, 87 test, lint và formatter | [source_validation.json](evidence/source_validation.json) |
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
