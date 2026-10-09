<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# 底座唯一来源与本体协作规则

2026-10-08，用户确认：底座以本底座模块的内容为准，本体与底座在同一Auromix/odradek仓库修改，不维护两套当前底座。当前同源候选为 **B06-COMPACT-03**：保留已确认COMPACT-02主罩母面，优化后部接口窗、背向检修固定及PCB底架。当前本地修订尚未成功推送，协作时不能把远端旧版本当作最新版本。

## 唯一可编辑底座源

- 源目录：[engineering/base_b06](../../engineering/base_b06/README.md)。
- 原生生成器：[blender_compact.py](../../engineering/base_b06/blender_compact.py)与[geometry.py](../../engineering/base_b06/geometry.py)。
- 当前原生模型：[ODR-BASE-B06-COMPACT.blend](../../engineering/base_b06/build/exterior/ODR-BASE-B06-COMPACT.blend)。
- 参数、实体目录：[manifest.json](../../engineering/base_b06/build/exterior/manifest.json)；来源与验证指纹：[provenance.json](../../engineering/base_b06/build/exterior/provenance.json)。

主罩前鼻、双翼及颈台一体，约239×224×71 mm；共五件打印结构，面向256³打印空间，主视觉面无新增固定孔。颈口Ø136、轴心XY(0,75)、顶部Z74；预留Ø160法兰及PCD120八M6。以模型和manifest为具体尺寸依据，不用示意图或旧B05接口覆盖它。

B04、B05、SHAPE07/08及其旧总装继续保存作历史研究；不删除历史文件，不继续把它们作为当前底座修改或制造入口。旧检查不能转移给B06。

## 本体怎样引用

本体与底座可以位于不同工作目录或Git分支，但都属于Auromix/odradek。工作目录不同不产生第二份底座权威源。本体侧直接读取上述同源文件；如果并行生成需要冻结输入，可保存记录源路径、版本及SHA256的只读快照/缓存，不能把缓存变成可编辑的底座分叉。

更新底座必须回到`engineering/base_b06/`，同时重生成模型、STL、manifest、预览与适当检查。涉及臂根配合时协调本体接口；本体侧随后显式刷新快照，记录新哈希并重做受影响的联检。禁止只替换底座显示模型后沿用旧适配报告。

A12本体模块已采用B06来源和记录哈希的只读缓存。COMPACT-03更新后，旧COMPACT-02缓存需要由本体模块显式刷新；主罩/臂根接口未改变也不能把旧整包哈希称为最新。该事实只确认同源引用，不表示整个新臂身与底座已经联合验证。底座外罩/PCB安装架不承担机械臂载荷；承载底板、隐藏桌夹、内收盒架和PCB制造验证继续分别推进。
