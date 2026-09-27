# CAM-CABLE02 — 动态同轴候选与资料冲突

2026-09-27重新读取厂商资料。目标是缩小内部侧腔；本次没有批准线束、改变限位或订购元件。

| 候选 | 本次一手资料 | 判断 |
|---|---|---|
| Rosenberger Similar RG316-d / CG:03 | 直接下载的9页目录，第7页：OD3.1mm，动态R75mm/3M弯曲，±180°/m/5M扭转；单次R15mm | 继续用于较保守空间研究。弯曲和扭转是分别给出的条件，不组合成同一复合寿命；还缺完整FAKRA总成号和通道验收。 |
| Basler 2200002798，3m FAKRA-Z F/F | 技术文档v134列最大OD3.45mm、动态R34.5mm/5M和robot适用；**同料号官方商店却列运动特性static** | 动态用途blocked，等待同料号受控规格消除冲突。可计算R34.5条件空间，不作为已确认线材。 |
| OKI FKR(CX)，K可动系列 | 官方产品页列OD3mm、R37mm、超过10M滑动弯曲参考值，可动最长5m；未给扭转 | 完整端型/长度待定。新闻说明约5Gbps，不能直接视为ZED链路6Gbps合格；也不能把U形滑动试验用于滚转扭转。 |

依据：[Rosenberger目录](https://www.rosenberger.com/fileadmin/content/headquarter/Downloads/_Other/HySpeedVision_Flyer.pdf)、[Basler技术文档](https://docs.baslerweb.com/basler-cable-gmsl-fakra-z-1x-f-f)、[Basler同料号商店](https://www.baslerweb.com/en/shop/cable-gmsl-fakra-z-1x-f-f-3m/)、[OKI产品](https://www.okidensen.co.jp/en/prod/cable/movable/index_fakra.html)、[OKI新闻](https://www.oki.com/global/press/2025/z25054e.html)。OKI产品页还将PZPZ文字写为两端Plug，而配置图标题称Jack-to-Jack；最终料号不能由这些文字直接拼接。

Rosenberger相同URL的搜索提取仍返回旧CG:02/2M内容，直接下载PDF则为CG:03及上表条件。以本次下载哈希`8ee280b7cbf131ab88ae178ce2651643849476610639e6aa04c67d1cc5f3ebc4`和逐页目视为依据，旧[线束研究](harness-and-connectors.md)保留为历史，不静默把旧型号改成新型号。动态半径仍75mm，原空间反例没有因此解除。

纯几何对照：单根线的180°半圆回环最小跨距为`2R+OD`。上述三种半径分别给153.1mm、72.45mm、77mm；不包括第二根线、隔板、护套、端部直段及装配间隙。这只是指定半圆方案，不是所有三维路径的最小外形证明。J4到J5的紧凑转向不能仅凭有通孔就宣称布线完成。

后续须核定相机实际3/6Gbps配置、PoC电流/压降、FAKRA接头配合与锁扣、全通道损耗/回波损耗、动态温区、夹点/曲率及弯扭工况。Stereolabs列GMSL2前向3或6Gbps，取决于设备与配置；不是以像素带宽直接猜测线速。[Stereolabs链路说明](https://docs.stereolabs.com/docs/products/embedded/zed-link-capture-card/gmsl2)

[来源记录与计算输入](sources/camera-cable-refresh.json)固定原始资料哈希。当前选择仍是“需要动态验证的候选”，没有实测链路或寿命结论。

原创分析：CC BY-NC 4.0。Odradek — Auromix contributors (https://github.com/Auromix/odradek)。
