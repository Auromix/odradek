# BASE-IO-B05 嘉立创 EDA 迁移工作包

CC-BY-NC-4.0；Required Notice: Odradek — Auromix contributors.

已经在激活后的专业版 4.1.60 客户端完成原生导入、恢复原理图网络、移动 J2/J6，并保存实际可编辑的 [原生工程](base-io-b05/base-io-b05.eprj3)。原 BRI01 保留不变。通过本项目的 MCP→官方 CLI 适配器操作；原理图导入变更弹窗由 GUI 确认。适配器不是厂商原生 MCP。

`migration-input/kicad/` 保留源格式副本。`reports/migration-status.json` 和 `reports/native-relocation-readback.json` 记录当前状态与实际 API 读回；原 KiCad ERC/DRC 结果不能继承到嘉立创 EDA。

PCB 原生坐标以 mil 为 API 单位、Y 向负方向。J2 已移动到 (58,0) mm，J6 到 (42,20) mm；实际 48 个焊盘中 38 个电气焊盘有网络，10 个机械焊盘无网络。板框仍为 116×56 mm。

**尚未制造放行。** 导入没有保留线路；移动后原覆铜也需重新生成。当前原生 DRC 共 98 项：56 间距、14 过孔孔径规则、28 连通性。不能仅调整规则以掩盖这些问题。EtherCAT 差分对、叠层与阻抗、48V 载流和温升均待设计验证。

EtherCAT 为无磁被动直通，GMSL 走独立同轴馈通，不经过普通 FR4 线路。MCAD 的整体刚性旋转与 PCB 实际改版分别记录；外壳缩腰后，内部骨架和接口面板还需重新对齐与试装。
