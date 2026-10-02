<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# B05 底座：本轮外壳深化

当前形态以用户最新的 [B 收腰盾形参考](../../docs/concepts/selected/base-shield-current-reference.png)为目标。俯视宽肩、收腰、前鼻收窄；侧面外沿低矮，肩部向锥形中央环台抬升；前鼻保留简约琥珀灯窗。保留平滑大曲面与受控折线，分缝服务于试印和拆装，不堆加装饰。

本轮交付 **B05-EXTERIOR-SHAPE-04 外观与尺寸试印版**，尚未得到用户对新三维造型的确认。后续内部结构需匹配本轮轮廓；旧 B04/B05 矩形承载板前角会越出收腰外壳，不可直接作为适配后的总装发布。外观环台中心已从旧参考的 (0,135) 改为 (0,75) mm；环台外径 144 mm、内孔 104 mm，下一版内骨架须重新设计法兰，目标包络半径不超过 70 mm。旧 OD160 法兰不能直接套用。

- [可旋转三维预览](build/exterior/index.html)：内嵌真实零件网格，可离线打开。
- [原生 Blender 模型](build/exterior/ODR-BASE-B05-EXTERIOR.blend)：保留外形构造面与独立零件。
- [正面](build/exterior/front-three-quarter.png)、[俯视](build/exterior/top.png)、[后侧](build/exterior/rear.png)：由实际模型渲染。
- [外壳 STL 试印包](build/exterior/B05-exterior-fit-prototype.zip)：仅 8 个非承力外观件、说明与检查报告。
- [检查报告](build/exterior/print-checks.json)：8 件均闭合、单连通体，单位 mm，适配预设 220×220×250 mm 打印床和 5 mm XY 余量；最大平面件为 188.6×82.2 mm 前鼻、144×144 mm 环台。

外壳合拢外包络约 290×251 mm，最高 Z74 mm。试印 STL 已平移到正坐标，没有替用户决定摆放、支撑和切片参数。PETG/ASA 外壳、半透明灯窗只供无动力外形验证。不能把网格检查当成实物可装配、载荷或量产验证。

## 下一模块的必要接口

内骨架需随盾形收腰裁剪，并重新校核载荷与桌夹反力。外罩的定位舌、安装支座、螺钉、灯板固定及线缆应力释放尚未完成。后盖具有下出线开口，但未集成可替换接口板的安装结构。RJ45、两路 GMSL 同轴和独立 48V 电源须保留插拔、弯折及封盖空间。

[嘉立创原生接口 PCB](../electronics/base-io-b05/README.md)已完成导入、网络恢复与 J2/J6 移位；布线与覆铜重做待完成，当前 DRC 98 项未通过。当前接口板不能下单制造。

本轮最新模型独立存放于 `build/exterior/`，旧外观检查点移至 `history/`；已选概念参考保留在 `docs/concepts/selected/`。未确认的新模型不混入已选概念图稿。

构造与导出入口为 `blender_exterior.py`，本轮在 Blender GUI 控制台执行；`review_render.py` 只渲染已打开场景。后续只在本模块基础上深化。
