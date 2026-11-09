# Nguồn model và quyền sử dụng

Scene PAIRS Robotics Research Lab, cập nhật 09/11/2026. Danh sách file/hash máy đọc được: src/tb4_voice_navigation/models/asset_manifest.json.

- **Unitree G1 (29DoF)**: https://github.com/unitreerobotics/unitree_ros/tree/725b59b6de39a26c425632120c89f23c49a36f1e/robots/g1_description . URDF g1_29dof.urdf và các STL gốc; pose bằng forward kinematics, không scale sai kích thước robot. BSD-3-Clause; giữ license gốc tại models/unitree_g1/LICENSE.
- **Unitree Go2**: https://github.com/unitreerobotics/unitree_ros/tree/725b59b6de39a26c425632120c89f23c49a36f1e/robots/go2_description . URDF go2_description.urdf và DAE gốc; stance joints thigh0.78/calf−1.56rad. BSD-3-Clause; models/unitree_go2/LICENSE.
- **UR5e/UR3e**: Universal Robots ROS2 Description https://github.com/UniversalRobots/Universal_Robots_ROS2_Description . Đọc từ bản Jazzy3.5.1 đã có, copy mesh visual tương ứng và giữ COPYRIGHT trong mỗi folder. Không dùng mesh UR20/UR30 có điều khoản đồ họa riêng.
- **X500**: PX4 x500_base, assets từ package PX4 sẵn có; nguồn upstream https://github.com/PX4/PX4-gazebo-models/tree/main/models/x500_base . License BSD-3-Clause của Rudis Laboratories được giữ tại models/x500_base/LICENSE. Chỉ copy visual; bỏ motor/sensor plugins và đổi legacy Gazebo material script sang RGBA/PBR tương đương để portable trên Harmonic. File nguồn gốc giữ nguyên trong model folder, bản scene là conversion có ghi rõ.
- **TurtleBot4 trưng bày**: nav2_minimal_tb4_description https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation . Visual URDF từ package Jazzy; COPYRIGHT tại models/turtlebot4_display/COPYRIGHT. Robot navigation dùng package simulator gốc riêng.
- **Logo PAIRS Lab + ĐHQGHN**: ảnh gốc do người dùng cung cấp, đối chiếu với brand assets sẵn có trên máy; copy PNG nguyên vẹn, không vẽ lại hoặc thay chữ. Logo phục vụ nhận diện scene theo yêu cầu người dùng; không tuyên bố logo thuộc license phần mềm của repository.
- **Kiến trúc/biển tên/lồng UAV/nội thất/địa hình**: code generator của bài thực hành. Biển chữ là texture code-generated; logo chính là PNG gốc riêng. Không dùng ảnh sinh để thay screenshot nghiệm thu.

Các robot nhập là **exhibit tĩnh**, không có walking/flying/manipulation controller hoặc sensor/TF trùng với robot Nav2. Bục/bàn/vách/cửa có collision; mesh trình diễn được đặt đúng kinematics lên các vùng đó. Không tuyên bố G1/Go2/X500 đang tự hành hoặc đã được kiểm thử điều khiển trong scene này.
