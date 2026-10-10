# A16 收敛臂身：完整外罩固定试配资料

此目录只收录当前装配需要的件，不混入废弃候选。共41件塑料打印件、6件采购金属管/隔套和完整名义紧固件。普通法兰、矩形管、分体鞍座、固定耳、螺钉和标准热熔螺母；未添加凸轮、齿轮联动或差动机构。

**只能有支撑、断电、空载试装。尚不是3kg额定或量产放行。** 电机原厂STEP没有公开再分发；本地Blender使用对应未缩放原厂实体和B06同一份底座。source_sha256和replacement_chain追溯每一件，移除旧件后再装新件。

- print-bed/：41件毫米贴床STL，查看print-list.csv后切片；内部支撑、孔径收缩和预紧需小样与首件验证。
- step/：当前自有打印/普通采购包络的原装配坐标实体，含实际固定孔和服务窗口，不含原厂电机几何。
- A16-body-own-parts.blend：完整当前自有臂身和同源B06底座；公开版移除原厂电机实体。本地完整原厂实体装配见work/arm-a16/actual-motors-modules.blend。
- drawings/：41页当前打印件名义尺寸工作图；完整几何以STEP为准，不是金属GD&T放行图。
- drawings/3-stock-cut-drill-fit-drawings.pdf：6件管材/隔套的3页下料钻孔工作图，stock-drill-table.csv列出端面到孔的尺寸；无需打印这些管材。
- assembly-BOM.csv、purchased-hardware-summary.csv、stock-cut-list.csv：只包含当前装配件，旧支架/旧罩不重复。
- assembly07.md：实际逐段装配与可拆顺序；harness-boundary07.md：供电、CAN、GMSL和法兰的保留接口与未解决事项。
- release-gates07.md：3kg肩部、金属骨架、线束、热与实物验收缺口，不能以网格闭合或三个姿态通过替代。
- first-sample07.md：当前装配的孔/螺母/轴承/接缝小样和实测记录要求；actuator-candidate-list.csv是与几何匹配的关节候选，不代表3kg链选型已经合格。
- joint-axis-table.csv、kinematics07.md：当前七轴零位/偏移、正运动学、雅可比和重力关系；cover-mount-table.csv列出当前外罩固定轴线。

原型打印前，先核实到货电机版本，尤其RS00固定面盲孔深度；按各模块小样校准热熔螺母与6807配合。不要直接将本塑料骨架改材质标签后当成金属量产件。
