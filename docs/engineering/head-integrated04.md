<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek) -->

# HEAD-INTEGRATED04：中央显示集成的历史 P16 工程快照

**HEAD04 已归档，不再作为主末端驱动路线。** 用户已确认灯片发光面本身参与夹持、参考造型关系，以及空载全闭→全开→全闭 **≤1 s**；后续研究转向一电机＋mimic 联动。HEAD04 保留四路 P16 的旧运动与支承，不能满足该周期要求。这里交付的是中央 CD-MOUNT01／CD-PCB01 与已有机械头的集成证据、可追溯质量账和原生几何模型，不是新的单驱动末端方案。

[开态 STEP](../../engineering/generated/head-integrated04/HEAD-INTEGRATED04-open.step) · [闭态 STEP](../../engineering/generated/head-integrated04/HEAD-INTEGRATED04-closed.step) · [开态 GLB](../../engineering/generated/head-integrated04/HEAD-INTEGRATED04-open.glb) · [原生 Blender](../../engineering/generated/head-integrated04/blender/odradek-head04.blend) · [质量输入](../../engineering/generated/head-integrated04/mass-properties.json) · [间隙记录](../../engineering/generated/head-integrated04/clearance.json) · [冻结清单](../../engineering/generated/head-integrated04/ready-manifest.json)

## 本轮实际集成了什么

从 HEAD03 的 697 个对象删除旧光学框和完整显示占位两项，保留 695 项，加入中央模块 **332 项**，总计 **1027 个命名对象**。新增项包含 14 个按候选材料积分的名义件，以及 **318 个质量未知的电子包络**：285 颗中央 LED、32 个背面器件和一套 GH 配对参考外形。中央模块与灯片合计 629 个 LED 实例。GH 只出现一次，没有将板级接头再重复添加。

中央模块新增的名义实体包括杯形座、压圈、PCB 板体、绝缘垫、窗口、光学框及连接件。电子器件使用已发布的最大本体盒或配对参考包络，不是供应商受控 BREP；背面器件的实体盒与 PCB 焊盘／装配余量包络分开记录。没有给电子矩形盒随意赋密度。

331 个新增对象被逐件证明包含于 CD-MOUNT01 已检验的中央显示障碍包络；替换光学框相对旧框只去料。所有灯片、指轴和 P16 机构的几何与运动未变，因此原中央模块对这些运动体的连续避让下界可以按原假设继承。历史角域上片 0…109°、下片 0…122°；最小继承下界约 **17.781620 mm**，它仅是中央模块与该旧机构的局部名义几何关系。

背面电子装配包络对中央名义结构共 462 组检查无正体积交叠，部分最小距离为零，表示存在名义贴合，**不能当成公差后正间隙保证**。额外的器件装配余量包络之间未发现正体积交叠。线缆、焊接偏差、绝缘、热桥、变形和实际安装服务空间未因此闭合。

## 坐标与使用方式

STEP 为头坐标系 **mm**，GLB 为头坐标系 **m**，前脸在局部 Z=0，+Z 指向工件；开态、闭态均已分别烘焙到文件注明的姿态。将闭态文件再施加一次闭合角会重复变换。

本版对应抬肩后整臂零位的前脸是世界 **[0,55,839] mm**。J7 轴心在头坐标 **[0,0,−164] mm**，换算世界 **[0,55,675] mm**。旧 HEAD03 的世界前脸 804 mm 不在几何中烘焙；可能误导下游的旧世界变换和世界 COM 已从公开 `source_metadata` 剔除。当前字段以头坐标和本版顶层放置契约为准。

这个世界放置约定不表示 HEAD04 已经替换主整臂。`parts-open.json`、`parts-closed.json` 给出每个对象的状态包围盒、源、材料／包络表示及文件哈希；质量表中的逐件 COM/I 是**开态 home** 定义，不能将其误认为随闭态文件自动更新的账。闭态聚合值在 `whole_head_nominal_proxy.closed`，并已与独立闭态实体积分比较。

## 质量账：可计量小计与未知件分开

| 项目 | 当前记录 |
|---|---:|
| 带名义／目录代理质量的对象 | **275 项** |
| 未称量电子、预留等对象 | **752 项**，质量为 null，物理质量不等于零 |
| 名义／代理质量小计 | **2.830643365 kg** |
| 已单列规划余量 | **0.185…0.450 kg** |
| 可计量小计＋上述已列余量 | **3.015643365…3.280643365 kg** |
| 完整头部规划质量范围 | **未知：`whole_head_planning_mass_kg_interval=null`** |

控制板、其元件、本地双路 buck、这些部件的支架和互连尚未纳入，`unallocated_items` 明确保留未知质量。因此 3.015643…3.280643 kg **只是部分项目的小计区间，不是完整头重或有保证上限**，不能拿区间上端代替新整机载荷。

新中央名义件增加 65.226974 g，移除旧光学框的 37.074934 g，净增 28.152040 g。原 25…60 g 中央模块预算已改写为当前仍未称量的电子、铜／焊料及后续热／绝缘部件的规划分配，旧完整模块预算不再重复计入；这个数值保留不是称量，也不是证明所有缺项可以装进该范围。

四路 P16 仍按目录每台 95 g 分配一次，固定体与滑动体的质量分配是旧包络代理，不是辨识出的内部参数。原生件的均匀材料假设、目录件惯量代理和电子未知项分别保留。13 个聚合刚体与逐件质量账可以二选一使用，**不能两组同时相加**。

开态已计量小计的头坐标 COM 为约 **[0.000003,1.529341,−36.761632] mm**；按前述抬肩世界放置约为 **[0.000003,56.529341,802.238368] mm**。这只是 2.830643 kg 子集的 COM，未知电子／控制／电源加入后会改变它。

## 原生模型与已完成核对

开态、闭态 STEP 与 GLB 均重新导入为 1027 个命名对象；网格全部闭合。STEP 往返最大体积差约 **1.40×10⁻⁸ mm³**、COM 差约 **9.93×10⁻¹² mm**。275 个有质量对象的闭态刚体变换与独立闭态 CAD 积分比较，最大 COM 差约 **1.36×10⁻¹³ m**、中央惯量差约 **7.09×10⁻¹⁷ kg·m²**。这是数值一致性，不是实物精度或负载验证。

Blender 有 **21 个持久表达式 driver**：1 个 J7、4 个指轴、4 个 P16 本体转角、12 个滑块位移分量。它是旧五个用户运动变量的机构表达，**不是 21 个物理轴，也不是新的一电机 mimic 配置**。P16 本体随真实连杆几何摆动，没有直接挂到指轴下冒充同转。

无渲染构建后，使用 `--disable-autoexec` 重新打开已保存 `.blend`，21 个 simple-expression driver 均有效，无注册 handler 依赖。1027 件闭态网格包围盒与独立 CAD 逐项比较，最大偏差 **0.002721 mm**。构建与重开报告分别见 [build-review](../../engineering/generated/head-integrated04/blender/build-review.json) 和 [reopen-review](../../engineering/generated/head-integrated04/blender/reopen-review.json)。本交付没有生成新的产品渲染，也没有硬件运行测试。

根线程另有只读独立审查，保存在本机 `work/head-integrated04-review/`：确认计数、重复质量、13 组惯量重构和每指 257 点的 P16 几何方程一致。原审查记录的旧世界元数据与不完整总重两项语义问题，随后由根线程仅更新注释／契约解决；没有重写旧数值来隐藏变化。冻结清单记录该审查快照及当前文件哈希，不把旧审查哈希冒充当前脚本版本。

## 可复用范围与复算

可以复用中央圆形显示的板形、灯点布局、可拆安装概念，以及逐件几何和质量证据组织方法。装到新参考造型和单驱动头部时，需重新检查机械接口、运动包络、接触面、电源和热路径；不能直接继承旧 P16 的整体适配结论。[HEAD-POWER01](hardware/head-power01.md) 也已在页首标明历史四路 P16 分支，不能直接视为新驱动的电源配置。

下列命令从仓库根执行。Python 需要既有工程依赖；本机 Blender 在 `work/r4-runtime/Blender.app`，其他环境可替换为对应 `blender` 可执行文件。临时网格 JSON 放在仓库外的工作目录，不纳入交付。脚本参数已经按当前源码核对，归档过程没有再次改写生成数值。

```bash
../../work/r4-runtime/venv/bin/python engineering/head_integrated04.py \
  --blender-mesh-output ../../work/head-integrated04/mesh.json

../../work/r4-runtime/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python engineering/head_integrated04_blender.py -- \
  --mesh-json ../../work/head-integrated04/mesh.json --no-render

../../work/r4-runtime/Blender.app/Contents/MacOS/Blender \
  --background --disable-autoexec \
  engineering/generated/head-integrated04/blender/odradek-head04.blend \
  --python engineering/head_integrated04_blender.py -- \
  --mesh-json ../../work/head-integrated04/mesh.json --review
```

重新生成会改变 STEP/Blender 文件哈希，须复核并刷新归档清单；不要把旧清单继续当作新产物的证据。本次归档仅新增本说明、冻结清单，并给 HEAD-POWER01 增加历史范围说明；两份生成脚本、CAD、数值、主整机和索引均未修改。未采购、未验证实体装配，也没有制造、绝缘、热或额定夹持放行。
