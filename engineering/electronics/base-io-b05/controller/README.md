# B06 底座灯控 · CONTROL-01 候选

这是同一底座接口 PCB 的增量版本，独立于机械臂。48V → 原有 F1/D1/U1 → 就地5V；新增 U3 提供3.3V，U2 STM32G030F6P6 通过 TIM3 驱动 J7.2 的 PWM。EtherCAT 保持被动直通，不承担灯控命令。

当前保存、重开后的 PCB 严格 DRC 为0。`native-readback.json`记录32个器件（含6个安装孔）、121个焊盘、401条线路、39个过孔；两层CHASSIS铺铜由客户端重新生成，规则未放宽。当前制造导出位于 `manufacturing/b06-io-control01/`；旧 `b06-io-local5v/` 不含控制器，仅用于追溯。文件通过数字审计也不等于实板或整套底座生产放行。

新器件及原理图/PCB 引脚契约以 [specification.json](specification.json) 为准。C5/C6 为有极性的钽电容，1脚正；U2 的 SWCLK 为封装19脚，20脚不用。模型中的最大包络采用 [package-envelopes.json](../local5v/package-envelopes.json)，不替代厂商插头模型。

原理图保存重开后的检查为0错误、0警告，见 `schematic-review.json`；全部32个器件的引脚网络与PCB逐项一致，见 `check_schematic.py`。这些数字检查不能替代实物电气测试。EDA元件总装STEP约16.7MB，MCP返回超限且系统下载保存按钮不可用；本包只包含真正单次导出的 `BoardOnly.step` 板体，完整电子元件包络在Blender中独立检查，不声称是厂商元件精确STEP总装。

| 接口 | 端子定义 | 连接方式 |
|---|---|---|
| J7 GH3 | 1=5V，2=PWM，3=RETURN48 | 底座内部接前灯板 J1，不增加桌下5V供电线 |
| J8 GH3 | 1=RETURN48，2=底座TX，3=底座RX | 3.3V UART，TX/RX交叉到控制器；线束经隐藏接线仓向下 |
| J9 GH5 | 1=RETURN48，2=3V3参考，3=SWDIO，4=SWCLK，5=NRST | 检修烧录；3V3只用于电平参考，不能由调试器倒灌供电 |

GH3/GH5 的额外焊脚为固定焊脚，均接 RETURN48。端子编号必须按厂家接插件图确认，不能根据视角认定左右顺序。UART 不兼容 RS232 或5V TTL；5V/3V3均非隔离，与48V返回共地，PC调试器/示波器接地需在台架方案中确认。

## 固件和命令

运行 `firmware/build.py` 重新编译；依赖 C 编译器、CAD Python 中的 ziglang 和固件目录内带许可证的 CMSIS 头文件。`firmware/build-report.json` 记录输入/输出 SHA256、目标 ELF/向量表检查、主机 UB/bounds 检查结果。当前产物1936字节 FLASH，12字节静态RAM，预留1024字节栈。没有实板烧录、硬件时钟或栈峰值测量。

115200、8N1、3.3V UART，每条 ASCII 命令以 LF 结束；先等待 `OK\n`，再发下一条。错误命令返回 `ERR\n` 并保留灯效。过长/非法字符帧丢弃到 LF；半帧250ms超时复位。发送间隔和 ACK 超时由主机约束，繁忙时可能丢弃 ACK，超时后不能据此断言命令没执行。

| 命令 | 参数 |
|---|---|
| `OFF` | 关闭 |
| `SET 250` | 0–1000，占空比千分数 |
| `BREATH 2000` | 200–10000ms，三角亮度包络；光学观感需实测 |
| `FLASH 100 200` | 亮/灭各20–10000ms |

复位默认灭灯，名义PWM 1kHz；没有持久化设置。断开UART后当前灯效继续运行。独立看门狗名义约2秒，实际LSI误差、复位和引脚瞬态须示波器验证。

Ubuntu PC 可用3.3V USB-UART适配器做独立台架调试（只接GND/TX/RX，不接适配器电源）。`python3 lamp_cli.py /dev/ttyUSB0 BREATH 2000` 发送单条并等待 ACK；工具不供电、不烧录、不自动重试。`python3 test_lamp_cli.py` 用PTY模拟器验证传输，**不是硬件测试**。外置盒最终UART设备及隔离方式未冻结，不与EtherCAT网口混用。

## 原生板修复和验证顺序

1. 用嘉立创专业版打开同一 `.eprj3`；核对控制器线路、差分对及规则仍存在。增量编辑脚本不可无条件重放。
2. 重建全部铺铜，保存。保存关闭重开后严格DRC为0；继续核对原理图与PCB网络匹配，不能删除CHASSIS铜层或放宽间距来消除错误。
3. 从客户端重新导出Gerber、BOM、贴片坐标、IPC356和STEP，核对U1的Ø1.1孔、混合Ø0.3/Ø0.6过孔及26个实际元件。重新导出哈希必须对应本版原生源。
4. 完成插头/线束、焊接、间距和装配审核后才形成PCB打样包。整板工作电流、保护与温升仍需首件确认。

## 不接机械臂的实板验证

先做无电目检、极性及短路检查；独立限流48V源只接底座支路，不接臂或其他负载。按已有台架计划检查就地5V启动、低负载及输出不超过100mA的测试预算，确认5V为4.75–5.25V、3V3在芯片工作范围后再接调试器。用J9烧录 `firmware/controller.hex`，从0x08000000写入并读回比对，不改安全/读保护选项。

示波器和电流测量记录须覆盖：上电/复位灭灯、0/25/50/75/100%占空比、1kHz波形、UART命令/错误/断线行为、看门狗复位、闭盖8小时呼吸/闪烁和温升。记录最低/最高输入、固件哈希、板号、仪器校准、测量原始文件和复核人，填写底座 [独立验证计划](../../../base_b06/validation-plan.json)。所有项目可用底座、台架电源、灯板、调试器和测试设备完成，机械臂不是前置条件。

元件原始资料：[ST STM32G030](https://www.st.com/resource/en/datasheet/stm32g030f6.pdf)、[Diodes AP2112](https://www.diodes.com/datasheet/download/AP2112.pdf)、[KEMET T491](https://search.kemet.com/download/specsheet/T491A106K016AT)。第三方 CMSIS 授权独立保留在 `firmware/vendor/`。
