<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# A05 七轴实尺寸包络查看器

最新版本用RS03／RS04／RS06／RS00的尺寸包络替代A03理想腕环，供本体装配、姿态与走线空间讨论。对应 [装配修订说明](../../arm-body-assembly-a05.md)；具体型号仍是装配候选，非采购/制造冻结。底部圆盘仅表示固定安装基准，不修改底座分支外观。

## 操作与读图

- 七个滑条控制J1～J7，J2上臂竖直为0°；选中轴和型号高亮。
- Z字收拢、抬起互动、参考伸展使用同一套尺寸；“收拢→互动”演示共同路径，显示时长不代表实机速度。
- 拖动画面旋转，滚轮/双指缩放；可以看侧面、正面和腕部近景。
- 头部、支架、轴线和线束占位可以分别显示。关闭头部不取消其碰撞检查，避免仅因隐藏部件就误判安全。
- 粗包络提示检查电机互相、电机/主杆、头部/电机、头部/主杆、跨刚体支架相关对及桌面；同刚体支架接合与指定相邻连接对除外。不等于全部制造零件检查。详细范围见修订说明及结果JSON。
- 彩色分段曲线是预留通道，半透明体是活动线腔占位；并非已经连续、恒长并通过弯曲半径检查的真实线束。
- 四瓣头保持展开，包含上下外倾相机；不在本轮增加夹爪开合。

世界Z向上，+X向桌内；轴序为Z,Y,X,Y,Y,Z,X。J2几何旋转为显示角度−90°。J5/J6已沿局部X错开55 mm，不再是共点腕。上臂250、前臂180、后续轴向尺寸55+65+60+90 mm，轴向和700 mm；另有肘部90 mm侧向错层。

关节滑条范围是布局探索目标，不是所有组合都可用的实机限位。例：低位J6=−60°会出现下相机/肘电机冲突；参考伸展J7=45°时大灯瓣可能进入桌面，即使TCP位置不变。J7±90°的真实线束能力尚未验证，不支持无限roll。

## 来源与复现

统一尺寸在 `engineering/parameters/arm-a05-layout.json`。`engineering/arm_a05/model.js`提供FK、部件和碰撞包络，`viewer.js`提供显示交互，`a05.template.html`提供视图布局。运行：

```sh
node engineering/arm_a05/check.js
python3 engineering/arm_a05/build_viewer.py
```

生成 `arm-body-viewer.html`。它是小于1 MB的对话HTML片段，使用宿主主题和控件样式，内嵌three.js r160，无模型网络依赖。原始项目代码按CC-BY-NC-4.0提供；three.js保留独立 [MIT许可证](THREE-LICENSE.txt)，原始来源 `https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js`。

本地预览用visualize技能的 `scripts/render.py` 包裹为临时页面，再以只绑定127.0.0.1的HTTP服务打开。临时文件放在忽略目录 `work/`，检查后停止服务；不用 `file://` 做验证。

可编辑Blender文件在 `engineering/models/arm-a05-packaging.blend`；生成方式见 `engineering/arm_a05/export_blender.py`。它与查看器共用几何数据，是装配研究模型，不是带完整孔、轴承公差和紧固件的制造CAD。

A02查看器在提交`540f158`；A03查看器在`5e68bc0`，其旧腕环问题见 [A03复核](../../arm-body-structural-review-a03.md)。这些历史尺寸不与A05混用。
