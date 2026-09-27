# 可复现计算与建模

本目录原创 Python 源码按 [PolyForm Noncommercial 1.0.0](../LICENSES/PolyForm-Noncommercial-1.0.0.md) 提供。参数数据和生成的原创工程文档／模型按根目录 CC BY-NC 4.0，详细范围见 [LICENSING.md](../LICENSING.md)。依赖库保留各自许可，不打包重新许可。

`kinematics.py` 使用空间轴乘积形式计算位姿、Jacobian、重力、质量矩阵及数值 Christoffel 项；`gripper.py` 定义四片各自的径向转动与接触力映射。所有计算使用米、千克、秒和弧度；外部配置中的角度字段名称明确带 `_deg`。

代码不连接硬件、不发送运动指令。数值 IK 不包含碰撞或线束约束，质量和惯量假设必须在使用结果前核对。摩擦抓持下界不能作为力闭合证明。复现步骤与固定依赖将在对应模型发布时记录。
