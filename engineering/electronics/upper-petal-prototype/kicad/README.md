# ULP-01 原生 ECAD 历史记录

**此目录不是当前候选板。**当前完成布线的独立样片是 [ULP-02](../ulp02/kicad/README.md)，其扫描映射和 280 mA 峰值预算必须成套使用。

这里保留初始 ULP-01 的原理图、未布线 PCB、本地符号/封装、生成脚本和当时实际检查报告：原理图 ERC 通过、317 针 XML 对照相符；PCB 留有未连接项，未通过完整 DRC。`checks/verification.json` 是历史状态，不能替代 ULP-02 报告。

`routing-trials.json` 记录未收敛的后续路由试验。其中出现过小于 0.15 mm 的自动缩颈线路，因违反规则未采用，也没有放宽或豁免规则。试验 DSN、SES、中间 PCB、临时 `.kicad_prl` 和原始日志已移至库外工作归档，不作为可生产输出提交。旧版 ULP-01 的 113 点原始映射保留在父目录，ULP-02 同时保留了新旧映射对照。

许可证 CC-BY-NC-4.0；Auromix contributors。
