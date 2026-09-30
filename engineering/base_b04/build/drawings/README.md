<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# B04 P1 辅助图册检查点

本目录的 PDF、CSV 与 SVG 保留为较早机械骨架研究记录，**不是当前模型加工包**。最新工作以三维模型为主；外罩造型、底座灯、PCB 接口与外壳开孔正在协同修订，暂停图册重生成。

| 文件 | 对应范围 |
|---|---|
| `base-b04-manufacturing-review.pdf` | 6 页 STEP 实体边线投影、材料与特征坐标；26 个自制件 |
| `feature-coordinates.csv` | 同一旧版清单的完整特征字段 |
| `assembly-isometric.svg` | 同一旧版 STEP 的轴测边线投影 |
| `drawing-evidence.json` | 以上输入及输出的散列；6 页渲染与逐页版面检查已完成 |
| `assembly-dfm-check.json` | 独立、较新的局部刚体检查；源版本与范围见文件内容，不能代替图册更新 |

图册清单 SHA-256：`ad065c979d159c1636a3b4f45636eb2d2e782b9553024c0c5ffa4498b730d9ef`。图册早于保持罩转向、盒架避让和 PCB 装配细化，不能把这些文件与当前 STEP 混用。图册页数及版面检查不代表制造或承载放行。

重新生成前须冻结同版 CAD、装配清单与电子接口合同；按 [装配审查文档](../../../../docs/engineering/base-b04-assembly.md) 的命令生成，再渲染并检查全部 PDF 页。曲线采样只用于显示，实际尺寸应来自同版 STEP 与特征表，不按打印图量尺寸。
