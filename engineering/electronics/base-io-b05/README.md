# BASE-IO-B05 嘉立创 EDA 迁移工作包

CC-BY-NC-4.0；Required Notice: Odradek — Auromix contributors.

已经在激活后的专业版 4.1.60 客户端完成原生导入、恢复原理图网络、移动 J2/J6，并保存实际可编辑的 [原生工程](base-io-b05/base-io-b05.eprj3)。原 BRI01 保留不变。通过本项目的 MCP→官方 CLI 适配器操作；原理图导入变更弹窗由 GUI 确认。适配器不是厂商原生 MCP。

`migration-input/kicad/` 保留源格式副本。`reports/migration-status.json` 和 `reports/native-relocation-readback.json` 记录当前状态与实际 API 读回；原 KiCad ERC/DRC 结果不能继承到嘉立创 EDA。

PCB 原生坐标以 mil 为 API 单位、Y 向负方向。J2 已移动到 (58,0) mm，J6 到 (42,20) mm；实际 48 个焊盘中 38 个电气焊盘有网络，10 个机械焊盘无网络。板框仍为 116×56 mm。

**尚未制造放行。** 导入没有保留线路。2026-10-09先重新铺铜、消除56项旧覆铜间距错误，确认14个遗留过孔无网络且铜层导线为0后清理，DRC98→28，见[清理读回](reports/b06-native-cleanup.json)。随后本阶段完成48V正极与回流的原生实际走线：上下外层各2.4 mm宽，连接J3各3个焊脚和J4/J5各4个焊脚，共14个电气焊盘。编辑器在焊盘处自动拆分后为34段；保存、关闭并重开已确认。DRC规则和所有焊盘完全未改，当前原生DRC为 **16项连通性错误，全部属于未布线的8条RJ45数据网络**；没有新增间距错误。见[重开读回](reports/b06-power-reopened.json)、[独立审计](reports/b06-power-audit.json)及[走线审阅图](reports/b06-power-review.png)。

此板为无磁RJ45被动直通布局，不能据此视作EtherCAT控制器。丝印“DATA 8P PASSIVE”保留；状态文字已由“B06 IO FIT / UNROUTED”改为“B06 IO / POWER ROUTED”，CHASSIS标识避开J6。机壳屏蔽和RETURN48仍是分离网络。GMSL走独立同轴馈通，不经过普通FR4线路。

本轮机械对照使用B06同源外罩与底架。板框116×56 mm、厚1.6 mm，PCB坐标(u,v)映射总装(X,Y,Z)=(58-u,40-v,20)，API读回先把mil转换为mm并翻转Y。H1..H4分别对应(52,34)、(-52,34)、(-52,-10)、(52,-10)，与底架四个安装孔一致；[原生读回](reports/b06-native-fit-readback.json)保存器件和焊盘坐标。后盖开窗是检修/插拔空间，不能当作接插件承力板；真实插头、锁扣和线束仍须试装。

独立铜箔几何检查：上下供电路径一致，每极每层7个焊盘处于一个连通铜区，两极外层铜最小间距约4.585 mm。假设外层铜35 µm、两层平均分流，中心线模型估算供电回路电阻约4.80 mΩ，10 A约48 mV/0.48 W；20 A约96 mV/1.92 W。**这不是载流额定值**：未包含接插件、过孔桶壁、焊盘扩散、接线和温升。原生API未返回可用物理叠层，不能把历史KiCad叠层当作当前嘉立创已确认叠层；差分阻抗、载流和温升仍待验证。

本阶段不改B06几何和打印件。真实电源插头宽高已按官方资料复核，但深藏接头的闭盖锁扣可达性仍未闭合，见[插头复核记录](reports/b06-plug-review.md)。下一阶段先验证局部插合基准，再决定是否修改后盖或接口安装位置。

源码：[原生走线脚本](route-power-native.js)只能在激活客户端、指定PCB、零铜线的首次阶段执行，重复执行会拒绝；[独立检查](check_power.py)检查保存重开读回与当前PCB哈希；[审阅图生成器](plot_power.py)仅用于可视化，不是Gerber或制造图。
