# BASE-IO-B05 嘉立创 EDA 迁移工作包

CC-BY-NC-4.0；Required Notice: Odradek — Auromix contributors.

已经在激活后的专业版 4.1.60 客户端完成原生导入、恢复原理图网络、移动 J2/J6，并保存实际可编辑的 [原生工程](base-io-b05/base-io-b05.eprj3)。原 BRI01 保留不变。通过本项目的 MCP→官方 CLI 适配器操作；原理图导入变更弹窗由 GUI 确认。适配器不是厂商原生 MCP。

`migration-input/kicad/` 保留源格式副本。`reports/migration-status.json` 和 `reports/native-relocation-readback.json` 记录当前状态与实际 API 读回；原 KiCad ERC/DRC 结果不能继承到嘉立创 EDA。

PCB 原生坐标以 mil 为 API 单位、Y 向负方向。J2 已移动到 (58,0) mm，J6 到 (42,20) mm；实际 48 个焊盘中 38 个电气焊盘有网络，10 个机械焊盘无网络。板框仍为 116×56 mm。

**尚未制造放行。** 导入没有保留线路。2026-10-09在嘉立创原生工程重新铺铜，消除56项旧覆铜间距错误；确认铜层导线为0、14个遗留过孔均无网络后删除这些孤立过孔，保留删除前读回。未放宽DRC规则。目前原生DRC为 **28项连通性错误**，需要重新设计实际线路；差分对、叠层与阻抗、48V载流和温升仍未验证。见[本轮清理读回](reports/b06-native-cleanup.json)。

此板为无磁RJ45被动直通布局，不能据此视作EtherCAT控制器。丝印已将“ETHERCAT”改为“DATA 8P PASSIVE”，增加“B06 IO FIT / UNROUTED”，移动CHASSIS标识避开已移动的J6。GMSL走独立同轴馈通，不经过普通FR4线路。

本轮机械对照使用B06同源外罩与底架。板框116×56 mm、厚1.6 mm，PCB坐标(u,v)映射总装(X,Y,Z)=(58-u,40-v,20)，API读回先把mil转换为mm并翻转Y。H1..H4分别对应(52,34)、(-52,34)、(-52,-10)、(52,-10)，与底架四个安装孔一致；[原生读回](reports/b06-native-fit-readback.json)保存器件和焊盘坐标。后盖开窗是检修/插拔空间，不能当作接插件承力板；真实插头、锁扣和线束仍须试装。
