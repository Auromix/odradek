# A10 长版：打印与螺栓装配验证

**2026-10-08外观状态：用户保留长版，但拒绝A10本体造型；本版继续作为机械输入与历史试装文件。当前外观候选在[A11风格探索](../../docs/concepts/exploration/arm-body-a11-style-study/README.md)，参照另一个会话的同源魔鬼鱼底座，等待用户选择。**

范围是裸臂，不安装四瓣头。长版轴向参考距离690.7 mm，七轴构型Z/Y/X/Y/Y/Z/X，J2竖直向上为显示0°。保持低位回折与抬起互动的桌面宠物定位。载荷目标仍为裸法兰中心总外负载3 kg。

版本采用20×40×2金属直管＋打印一体端座＋可拆护罩。电机接口来自锁定版本的RobStride STEP和尺寸图；完整原厂几何在本机Blender中导入，公共模型保留自主绘制包络，供应商资产不套用项目许可证。来源、比例和定位变换见`build/motor-import-audit.json`。

验证原型交付不代表额定承载成立。J2长臂水平伸展约37 N·m静态需求，厂家35/40 N·m数据带不同大面积散热工装条件；紧凑外壳中热能力、关节输出轴承及打印连接强度待测。当前电机组合可进行接口和无动力装配验证，尚不能批准3 kg无辅助支撑运行。完整线束与插头位置需实物电机复核。

- `build/odradek-a10-long-validation.blend`：公共原生模型，七轴可调。
- `../../work/arm-a10/odradek-a10-long-actual-motors.blend`：本机完整原厂电机模型，忽略上传。
- `build/print-ready/`：平移到平台、单位mm的打印STL；不是采购件的打印替代品。
- `build/drawings/`：打印件三视图、两根管材DXF；三视图为核对页，STEP/STL定义打印尺寸。
- `build/assembly-guide.md`、`build/hardware-BOM.csv`：装配顺序和采购规格。
- `build/print-audit.json`、`build/collision-*.json`、`build/motion-context-audit.json`：数字检查范围和结果。

[完整验证结论](../../docs/engineering/arm-body-a10-validation.md) · [仅当前长版的收敛外观目录](../../docs/concepts/converged/arm-body-a10/README.md) · [独立打印与装配包](build/odradek-a10-long-print-validation.zip) · [离线七轴查看器](../../docs/viewers/arm-body-a10/index.html)。压缩包中的`VALIDATION.md`是仓库报告的副本，报告内仓库相对链接请在仓库中打开；包内文件本身可独立使用。

## 重建

需CadQuery、numpy、trimesh、ezdxf以及Blender4.5；使用项目既有Python环境。顺序执行`build.py`、`vendor.py`、`collision.py quick`、`collision.py full`、`collision.py supplier`、`bounds.py`、`motion.py`、`tools.py`、`review.py`、`manufacture.py`、`blender.py`及`audit_blender.py`。原厂文件按`docs/engineering/sources/arm-a05-mechanical-sources.json`的URL下载到忽略目录`work/arm-a05/vendor/`，核对SHA256；导入器拒绝哈希不符文件。`blender.py -- --actual`输出本机原厂CAD版；`--no-render`可只保存模型。

`build.py`中的`refine.py`补实际紧固件空间；没有通过隐藏冲突件使碰撞检查通过。碰撞报告对插入螺纹及热熔嵌件的例外局限在具体几何区域。任意滑条组合不属于已验证工作空间。
