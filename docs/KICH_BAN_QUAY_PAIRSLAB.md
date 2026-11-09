# Kịch bản quay/chụp PAIRS Lab — bản nộp Bài 7

Ngày chuẩn bị: 09/11/2026. Mục tiêu: giới thiệu đẹp toàn bộ môi trường, chứng minh microphone thật→ASR→parser→Nav2, và chứng minh robot thực sự đến đủ 5 phòng nghiên cứu. Tuyến có bằng chứng riêng cho nguồn lệnh, không ghép tiếng buổi cũ lên hình chạy lại để coi là T15 mới.

## Tuyến tham quan bắt buộc

**A (UAV) → B (tay máy) → D (HRI/G1) → C (sảnh) → F (TurtleBot) → C (sảnh trung gian) → E (Go2) → C (sảnh kết thúc).**

A được thực hiện bằng câu nói thật trong lúc quay. Các điểm còn lại do chương trình tham quan gửi câu lệnh văn bản qua parser, ghi nhãn rõ trên video. Không set pose/teleport để chuyển phòng. Chỉ chuyển điểm khi waypoint trước có terminal SUCCEEDED; pose TF phải nằm trong polygon phòng khi nghiệm thu đến đích.

## Kịch bản dựng khoảng 4–6 phút

Thời gian dưới đây là kế hoạch; timeline chính xác của bản xuất được ghi trong CHAPTERS.md cùng thư mục video.

| Phần | Thời lượng dựng dự kiến | Hình ảnh phải có | Lời giới thiệu/caption đề xuất | Bằng chứng |
|---|---:|---|---|---|
| 1. Nhận diện | 8s | Logo PAIRS + ĐHQGHN trên biển sảnh | “PAIRS Robotics Research Lab — môi trường mô phỏng nghiên cứu robot.” | Screenshot Gazebo thật |
| 2. Tổng quan | 8s | Toàn cảnh 28×20m và bản đồ A–F | “Năm khu nghiên cứu nối bằng sảnh rộng4m; sáu mục tiêu ngữ nghĩa.” | Map thực, nhãn đúng |
| 3. UAV | 8s | Lồng thử, X500, H pads, mocap/workstation | “Khu UAV: không gian thử bay và kiểm tra nền tảng X500.” | Model là exhibit tĩnh |
| 4. Tay máy | 8s | UR5e, UR3e, bàn/bins | “Khu thao tác với hai tay máy Universal Robots.” | Mesh/URDF nguồn thật |
| 5. HRI | 8s | Unitree G1, sân tương tác | “Khu HRI và humanoid sử dụng model Unitree G1.” | Giữ đúng hình học/pose |
| 6. Chó robot | 8s | Hai Go2, bậc, bàn bảo trì | “Khu robot bốn chân với model Go2 và địa hình thử.” | Model đứng tĩnh, không giả controller đi bộ |
| 7. TurtleBot | 8s | Robot trưng bày, dock, test lanes | “Khu robot di động và thử nghiệm SLAM/Nav2.” | Robot navigation là TB4 riêng |
| 8. Giọng nói thật | 45–100s | Trạng thái ghi âm, transcript thật, routeA, robot đi đếnA | Người dùng nói **“Đi đến phòng UAV.”** | Audio cùng lượt, command_id, Nav2 status4/error0 |
| 9. Đi hết các phòng | 100–160s | B→D→C→F→C→E→C, bản đồ TF và cập nhật SUCCEEDED | “Tham quan tự động bằng lệnh văn bản; các đoạn này tăng tốc2x.” | Không thay tên nguồn lệnh thành voice |
| 10. Kết thúc | 5–10s | Robot ở sảnh/logo; checklist đủ5phòng | “Đã hoàn thành tuyến tham quan và xác nhận bằng Nav2/TF.” | Coverage receipt đầy đủ |

Giữ clip gốc tốc độ1x. Bản nộp chỉ tăng tốc phần tour văn bản và phải có nhãn2x; phần người nói/ASR giữ tốc độ thực. Không lồng nhạc vào câu nói để bảo toàn bằng chứng; các phần không có âm thanh nguồn để im lặng hoặc dùng lời thuyết minh riêng nếu quay bổ sung sau.

## Bố cục hình

- Khung trái: cửa sổ Gazebo thật, không quay toàn bộ desktop/ứng dụng cá nhân.
- Khung phải: bản đồ occupancy/semantic, pose và vệt TF thật, trạng thái Nav2 và transcript ASR khi ở phần voice.
- Phần voice ghi “MICROPHONE THẬT→ASR→NAV2”. Phần tour ghi “LỆNH VĂN BẢN THAM QUAN→NAV2”.
- G1/Go2/X500/UR và các TB4 trưng bày đứng tĩnh; robot điều hướng TB4 mới là đối tượng di chuyển.

## Danh sách ảnh cho báo cáo

| Tên ảnh | Nội dung | Đưa vào mục |
|---|---|---|
| environment_branding.png | Logo và sảnh | Giới thiệu/nhận diện |
| environment_overview.png | Toàn cảnh | Thiết kế môi trường |
| environment_uav.png | X500 + lồng thử | Khu UAV |
| environment_manipulation.png | UR5e/UR3e | Khu tay máy |
| environment_hri.png | Unitree G1 | HRI |
| environment_go2.png | Unitree Go2 + bậc | Chó robot |
| environment_turtlebot.png | Dock/test lanes | Robot di động |
| voice_UAV_arrival.png | KhuA sau lệnh voice thành công | T15 |
| arrival_B/D/F/E/C.png | Từng khu sau SUCCEEDED | Kết quả navigation |
| tour_complete.png | Kết thúc và tổng quan | Tổng kết |

Ảnh arrival chụp khi robot đã nhận SUCCEEDED; receipt lưu pose TF và kiểm tra polygon. Các góc cận cảnh chủ yếu giới thiệu thiết bị, còn vệt robot/pose trong video xác nhận đường đi. Không ghi một ảnh model trưng bày tĩnh là ảnh robot navigation đang di chuyển.

## Cách quay lại

Trong một phiên mô phỏng + pipeline đã định vị, ASR đã MODEL_READY. Source ROS/.venv/install, ROS_DOMAIN_ID=19. Không chạy đồng thời nhiều director vì chúng cùng điều khiển camera GUI.

```bash
python scripts/film_pairslab_demo.py broll --session deliverables/pairslab_demo_TAKE
python scripts/film_pairslab_demo.py voice --session deliverables/pairslab_demo_TAKE
# Khi voice director đã ghi hình: mở live_voice_trial với plan một câu và output cùng thư mục.
python scripts/live_voice_trial.py --plan docs/FILMING_VOICE_PLAN.json --output deliverables/pairslab_demo_TAKE/voice
# Sau khi voice director đã lưu filmed_acceptance.json:
python scripts/film_pairslab_demo.py tour --session deliverables/pairslab_demo_TAKE
```

Chuẩn bị recordings_dir/audit_file của voice_recognition_node vào voice/audio và voice/asr.jsonl trong cùng session trước khi nói. Trong lần quay, câu nói chỉ bắt đầu sau Enter của người dùng; chương trình không publish transcript kỳ vọng để thay ASR. Nếu nghe sai, giữ log và thử lại; bản raw giữ đủ các lượt, bản dựng cần ghi là lượt đạt nếu đã bỏ phần retry.

## Kiểm tra trước khi bàn giao

Video phải decode được, đúng1920×1080, có âm thanh microphone ở đoạn voice, các đoạn tăng tốc có nhãn, đủ5phòng và sảnh có receipt SUCCEEDED/inside_region. Giữ audio và raw video gốc; không push/public khi chưa được cho phép. Report cập nhật dựa vào file kết quả thực thi của session quay, không chỉ dựa vào kịch bản.

## Ghi nhận phiên quay 09/11/2026

Tuyến thực tế: A bằng microphone → B → D → C → F → thử E bị LOCALIZATION_LOST → cập nhật laser đứng yên cho AMCL → E đạt → C đạt. Bản dựng bỏ phần thử E thất bại, giữ đầy đủ clip/log gốc và ghi nhãn đoạn nối sau AMCL. Đây là video có cắt dựng, không tuyên bố một lượt liên tục không lỗi. Với lần quay mới, dùng C làm điểm trung gian giữa F và E như tuyến đề xuất trên.

## Đối chiếu các cảnh trong đề gốc

Bản video hiện tại ưu tiên môi trường đủ5phòng và T15 với một lệnh semantic UAV. Để trình bày đủ sáu demo liệt kê trong đề, có thể dùng thêm các cảnh sau; các cảnh chưa quay không được coi là đã có trong MP4 hiện tại.

| Demo trong đề | Kịch bản cảnh ngắn | Trạng thái video hiện tại |
|---|---|---|
| 1. Map segmentation | Hiển thị occupancy gốc cạnh semantic map A–F; trỏ các cửa và goal hợp lệ | HUD hiện semantic map; hình đối chiếu có trong tài liệu, chưa quay thao tác editor |
| 2. Single destination | Nói “Đi đến khu vực A”; chờ ASR, parser A và SUCCEEDED | Chưa quay riêng câu dạng ID; video dùng semantic UAV→A |
| 3. Semantic destination | Nói “Đi đến phòng UAV” để khớp phòng chuyên biệt của scene mới | Đã quay, gồm audio thật, parser và robot đến A |
| 4. Source→destination | Nói “Đi từ khu vực A đến khu vực B”; nếu chưa ở A, phải đến A trước rồi B | Chưa có clip voice riêng dạng này |
| 5. Invalid command | Nói “Đi đến khu vực Z”; ghi rõ UNKNOWN_REGION và không phát goal | Chưa có clip microphone riêng; không đổi text test thành voice test |
| 6. Multi-waypoint | Nói “Đi từ phòng UAV qua sảnh đến phòng robot hình người”; chờ A→C→D | Đã có audio/log phiên ba câu trước, chưa có video cùng lượt |

Các câu trong đề dùng “phòng thí nghiệm” có thể mơ hồ với năm lab; trong lời dẫn giải thích việc dùng tên cụ thể “phòng UAV” của scene mới. Nếu giảng viên yêu cầu nguyên văn, cần cấu hình alias mục tiêu rõ ràng rồi kiểm tra; không tự nhận hiện tại parser đã hiểu alias chưa xác minh.
