<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# 底座与臂：同源交接规则

2026-10-10 用户确认：**底座优先，臂侧优先适配**。只有臂侧调整适配件、根部支架、装入顺序和线束后仍有难以解决的拼接问题，才提交底座修改建议；不得静默缩放、改孔位或另建一套底座。

同一个 Auromix/odradek 仓库：`main` 管理当前底座，`design/arm-body` 管理臂身。两个 worktree 的 HEAD 可以不同，但当前臂的底座上下文必须绑定同一组底座文件指纹。分支名称或同样写着 B06 均不能代替同源检查。历史模型保留历史指纹，不要求改写历史成果。

## 唯一设计源

- [接口契约](interface-contract.json)是机械与电气边界。
- [底座模型清单](build/exterior/manifest.json)和 [Blender 总装](build/exterior/ODR-BASE-B06-COMPACT.blend)是当前外观及独立装配上下文。
- [承力件清单](build/load-frame/manifest.json)和 [法兰 STEP](build/load-frame/step/B06-104-LOAD-FLANGE.step)是精确结构来源。
- [交接指纹](arm-handoff.json)固定本次交接的上述文件 SHA256；它不重新定义几何，也不代表生产放行。修改源后必须显式更新交接、刷新当前臂上下文并重做受影响的拼接检查。

臂可直接读取底座 worktree，或从记录的 Git 提交导出只读缓存。缓存须字节一致；不能成为可编辑的第二套底座。臂预览、Blender 和检查报告都须记录来源指纹，禁止只更新 JSON 标签而沿用旧场景中的底座网格。

## 拼接职责

坐标单位 mm：桌面 Z=0、+Y 朝桌内，底座轴心 XY=(0,75)，安装面 Z=58。臂根局部原点应落在此安装面；若使用不同坐标系，明确记录刚体变换，不对底座做非均匀缩放。

底座提供 Ø160 法兰、Ø56 穿线孔、PCD120 的 8×M6x1-6H 通孔，首孔 22.5°、间隔45°；罩颈内径 Ø136、顶面 Z74。臂侧负责适配件、与臂电机相匹配的螺孔及支架、臂安装螺钉长度/垫圈/有效咬合和工具通路。Ø134 适配件可从上方装入；旧 Ø140 根部须在封罩前自下方装入。这些是名义几何规则，实际公差及装配尚需验证。

底座保留 48V 供电、专用 RJ45 EtherCAT 被动贯通、两路独立被动同轴和就地前灯供电控制。臂侧负责内部线束、插头/弯曲半径/应变释放、运动中的余量和固定。Ø56 是穿线空间，不是整束线缆与插头已可穿过的证明；底座不含 GMSL 解码器或 EtherCAT 主站。针脚、电气等级和控制接口只引用接口契约，不在臂侧另行定义。

臂须交付根部质量/重心/惯量与全姿态六轴载荷包络。本次契约中的 500N 轴向、100N 水平、150Nm 弯矩、40Nm 扭矩仍是未实测的候选值，不能作为机器人额定能力。源同步通过后，安装、运动干涉、线束和载荷分别验收。

## 同源检查与回执

仅检查底座自身文件一致性，不依赖臂：

```sh
python3 engineering/base_b06/check_arm_handoff.py
```

臂的**当前**上下文 JSON 使用 `base_revision`、`base_native_sha256`、`base_manifest_sha256`、`base_interface_contract_sha256` 字段；检测过时上下文：

```sh
python3 engineering/base_b06/check_arm_handoff.py --arm-context /path/to/current-base-context.json
```

协同回执格式见交接 JSON 的 `receipt_required`，完成源同步后运行：

```sh
python3 engineering/base_b06/check_arm_handoff.py --receipt /path/to/arm-thread-handoff-receipt.json
```

检查失败会以非零状态退出。回执须记录臂提交、当前模型路径、实际重新读取的底座指纹和各项验收状态；单纯回执声明不等于模型或装配证据。远端推送成功另外用 `git ls-remote origin refs/heads/main` 验证，并确认底座提交是远端祖先。不得强推、重置另一会话分支或用整分支覆盖底座文件。

## 2026-10-10 核对结论

交接前 main 为 `37627bd1d20da58b85a47bb48edaef40f10f0dce`。当前底座 COMPACT-07-DFM；臂 A12 wrist02 及 A14 模型链记录的上下文仍为 COMPACT-03，native `86812642…`、manifest `947b72eb…`，不能算作当前同源。A11 的 B05 是历史上下文。此次只新增交接与版本检查，不改底座外观、结构和 PCB。

前灯原生 PCB 已在此前工作中保存复开、DRC0；接口契约中的部分历史进度文字尚未刷新，实际资格以当前独立验证报告为准。物理验收仍未完成，本交接不改变生产资格。
