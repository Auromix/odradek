# A09 — 直管、平面板与紧凑关节的本体重设计

状态：**未确认提案；加工架构与配合检查阶段，不是制造发布或完整打印装配套件。** A08保留为历史版本。裸臂法兰总外负载目标3 kg，名义载荷质心在法兰中心，不安装四瓣头。

阅读[设计说明](../../docs/arm-body-redesign-a09.md)，查看[离线七轴查看器](../../docs/viewers/arm-body-a09/index.html)。参数源为[arm-a09-layout.json](../parameters/arm-a09-layout.json)。

## 文件与作用

| 文件 | 作用 |
|---|---|
| `build.py` | CadQuery原始解析实体，直管/板件/端座；导出STEP/STL/表面网格/质量惯量 |
| `blender.py` | 从相同网格创建七轴原生Blender驱动模型与渲染 |
| `review.py` | 递归/直接力矩核对、虚功核对、三姿态相交检查、512静态采样 |
| `vendor_clearance.py` | 本地读取固定版本原厂CAD检查肩/腕接口；不分发原厂网格 |
| `local_sweep.py` | 参考姿态中逐轴10°离散检查，完整保留相交结果 |
| `audit_blender.py` | 重新打开保存的blend，独立FK与源哈希核对 |
| `drawings.py` | 四片4 mm侧板DXF/平面图及轮廓、孔位、面积核对 |
| `package.py` | 32件原始几何STL配合检查包、清单、CRC核对 |
| `build_viewer.py` | 两种比例、原始CAD表面、底座背景及MIT three.js的离线HTML |

`build/slim/`轴向参考长度610.7 mm，`build/long/`为690.7 mm。该长度不是最大工作空间半径；前臂另有62 mm侧偏。长版用于外观比例比较。两个目录各有41件原始几何、STEP、报告、原生blend和渲染。两版blend均名为`odradek-slim-arm-a09.blend`，以父目录区分。

## 重建顺序

Python环境需要CadQuery、numpy、shapely、trimesh、ezdxf；Blender使用4.5 LTS。本项目不自动安装运行环境。仓库根目录下执行：

```sh
python engineering/arm_a09/build.py slim
python engineering/arm_a09/review.py slim
python engineering/arm_a09/local_sweep.py slim
python engineering/arm_a09/drawings.py slim
python engineering/arm_a09/package.py slim
blender --background --python engineering/arm_a09/blender.py -- slim
blender --background engineering/arm_a09/build/slim/odradek-slim-arm-a09.blend --python engineering/arm_a09/audit_blender.py -- slim
```

长版将`slim`替换为`long`；两版报告生成后执行`python engineering/arm_a09/build_viewer.py`。Blender/查看器另读相邻原底座工作树`../odradek/engineering/base_b04/build/`作为只读背景；独立克隆须恢复该上下文。原厂检查须另外提供源清单中固定SHA的本地CAD，缺失时不能宣称检查通过。

## 当前核对结果

- 两版41件STEP均为有效单实体；三个代表姿态未检出大于0.05 mm³的相交。
- 每版150个单轴离散样本中，**2个有干涉**：参考姿态其他轴保持不变时，J2 = −70°碰肩部顶板；J4 = −155°使腕部回折到肩部电机。150个点不覆盖连续运动及多轴组合。
- 短版原厂CAD肩/腕20项局部核对未检出相交；不含连接器、螺栓头、加工误差及工具空间。
- 保存的blend重新打开：7轴驱动、41件，三姿态独立FK误差低于0.001 mm。
- 四片侧板DXF的mm单位、闭合轮廓、两个Ø4.5孔位和面积与STEP核对通过。图中未包含完整GD&T、配合、表面处理和紧固件规范。
- 32 STL检查包不含7个电机与2个采购轴承；其中金属设计件是塑料配合副本，不能用于3 kg受力验证。

原始设计遵循仓库非商用许可证；内嵌three.js遵循其MIT许可证。原厂资料权利不由本仓库许可证覆盖。
