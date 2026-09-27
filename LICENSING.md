# Licensing / 许可说明

Policy updated: 2026-09-27. This note describes scope and licensing history; it does not modify the standard [CC BY-NC 4.0 legal text](LICENSE).

## 当前政策

现有原创概念图、设计文档、生成提示词和静态文档页面，现按 **Creative Commons Attribution-NonCommercial 4.0 International（CC BY-NC 4.0，署名—非商业性使用 4.0 国际）** 提供。适用范围限于权利人有权许可的版权及类似权利；下述既有 Apache-2.0 授权继续有效。

- 允许非商业的研究、教学、个人学习和爱好者用途，包括复制、修改与分享。
- 分享时保留作者署名、许可链接和所提供的声明，并注明修改。建议署名：`Odradek — Auromix contributors`，附[项目链接](https://github.com/Auromix/odradek)。
- 本许可不授予商业使用权。对需要依赖本许可的商业用途，须先联系项目作者并取得另行书面授权；提出申请本身不构成授权。
- 商业与否按具体用途判断，不能仅凭“研究”“大学”“非营利”或“公司”标签决定。以商业利益或金钱报酬为主要目的的使用不在 NC 许可范围内；法定例外和已有授权不受本说明削减。

这里选择 BY-NC，而非 BY-NC-SA：当前要求是署名与非商业使用，没有另行增加“改作必须采用相同许可”的义务。

## 商业授权联系

通过仓库的 [Commercial license request / 商业授权申请](https://github.com/Auromix/odradek/issues/new?template=commercial-license.yml) 联系作者，由 Auromix 维护者对接。说明使用的版本、素材以及计划用途即可；不要在公开 Issue 中提交保密信息。作者将依据相关内容的权利归属协调授权，具体范围以双方另行达成的书面协议为准。

出售或付费分发受保护图稿、将其用于商业营销等，属于需要评估商业授权的典型场景。实体机械臂的制造、销售及功能利用涉及的权利须另行判断，不能仅凭这份图文许可认定允许或禁止。

## 已发布版本与生效边界

此前提交 `2416784`、`6999b19`，直至 **[2d7d00f3639f2f80bc4b6c621e13300fea09f88d](https://github.com/Auromix/odradek/tree/2d7d00f3639f2f80bc4b6c621e13300fea09f88d)**，已经按 Apache-2.0 发布。其[原许可文本](LICENSES/Apache-2.0.txt)在仓库内保留作历史授权记录，并非对未来新增内容的统一 Apache 授权。

**本次变更不撤销、不缩减此前 Apache-2.0 已经授出的权利。** 使用者仍可在遵守该许可条件的前提下使用和商用此前发布的内容；同一内容在新版本中再次出现，也不会使其失去原授权。新 NC 政策主要适用于本次变更及其后新增或修改内容中尚未按其他条款授出的权利，不能把旧内容仅因移动、重新打包或改写许可声明就变成“禁止商用”。

## 软件、硬件及第三方内容

R4 开始增加工程计算、参数化建模脚本与机械模型，按目录明确区分：

| 范围 | 新增原创内容的许可 |
| --- | --- |
| 文档、图稿、参数数据、原创 STEP／STL／DXF／PDF／Blend 模型 | CC BY-NC 4.0，限许可方拥有的版权及类似权利 |
| `engineering/` 中原创 Python 计算／CAD／Blender 生成脚本及对应测试 | [PolyForm Noncommercial 1.0.0](LICENSES/PolyForm-Noncommercial-1.0.0.md)，以文件标识为准 |
| 第三方 SDK、驱动、元件 CAD、软件包 | 各自原许可；不自动纳入上述许可，不擅自重新分发 |

软件采用完整、未改写的标准 PolyForm Noncommercial 许可。其允许用途以原文为准，包括规定的个人非商业用途及非商业机构用途，不能笼统改写为“任何研究都允许”或“任何营利机构都禁止”。需要许可但不在其允许范围内的商业软件使用，仍须联系作者取得单独授权。

模型文件的版权许可不等于已经解决实体制造、功能使用、专利和商标的全部权利问题。不得将文件上标注 NC 理解为对所有功能性硬件制造自动产生禁止权。尚未提供经过验证的控制软件、固件或制造发布版 CAD。

CC BY-NC 不授予专利或商标权，也不会为不受版权保护的功能、思想或材料创造新权利。AI 辅助图像的许可仅覆盖权利人实际拥有且能够授出的权利。第三方参考图、商标与组件不因在文档中被引用而进入本项目许可。实体产品的制造／销售及正式商业授权合同应由具备相应经验的法律专业人士审核。

## 贡献者

贡献者保留其权利。提交到当前文档／图稿范围内的原创贡献按 CC BY-NC 4.0 接收，除非明确另有约定。维护者不会仅凭这项非商业许可就假定能将他人的贡献转授为商业许可；需要包含这些贡献的商业授权时，应先取得相应权利人的单独书面许可。

## English summary

Current original concept artwork, design documentation, prompts, and static documentation pages are offered under **CC BY-NC 4.0**, to the extent the licensors hold the relevant rights. Noncommercial research, education, personal study, and hobby use may include copying, adapting, and sharing under its terms. Sharing requires attribution, license information, and indication of changes. Commercial use requiring permission under this license needs a separate written authorization from the relevant rights holders; contact the authors through the repository's commercial-license issue form.

Previously published material through commit **2d7d00f** remains available under its already-granted Apache-2.0 rights, including commercial use under those terms. Changing the current license does not withdraw that grant, including for unchanged material carried forward. The new policy governs only rights in new material or changes not already granted under other terms.

R4 introduces engineering calculation and model-generation software under the unmodified PolyForm Noncommercial 1.0.0 license, with file-level notices. Original design files, models, drawings, and parameter data use CC BY-NC 4.0 to the extent of applicable copyright and similar rights. Third-party components retain their own terms. No validated control firmware or manufacturing-release CAD is asserted. These notices do not by themselves establish control over functional hardware manufacture; contributor commercial permissions, third-party rights, and statutory exceptions remain distinct.

## Official references

- [CC BY-NC 4.0 legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en): noncommercial grant, attribution, separate terms, and rights excluded.
- [Creative Commons FAQ](https://creativecommons.org/faq/): noncommercial purpose is distinct from the user's legal status; software and hardware need different consideration.
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0): existing copyright grant is perpetual and irrevocable, subject to its terms.
- [Open Source Definition, section 6](https://opensource.org/osd): a noncommercial restriction does not meet the OSI definition of open source.
- [PolyForm Noncommercial 1.0.0 official text](https://polyformproject.org/licenses/noncommercial/1.0.0): permitted software purposes and notices; the repository copy is unmodified.

Therefore the project is described as **a publicly shared design for noncommercial use**, not an OSI open-source project.
