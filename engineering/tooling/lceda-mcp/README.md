# 嘉立创 EDA 桌面 CLI → MCP 本地适配器

本目录是 Odradek 项目维护的薄适配层，**不是嘉立创官方 MCP 服务端**。它使用官方 MCP TypeScript SDK，将工具调用转发给已安装的嘉立创 EDA 专业版桌面客户端 CLI；不修改厂家应用，不安装第三方 EDA 扩展，不绕过激活或编辑器权限。

## 为什么有这一层

2026-10-02 实测官方 macOS arm64 客户端 `4.1.60.198f38ab`：

- `--help` 列出了 `--mcp stdio|http`，但实际执行返回 `MCP_NOT_SUPPORTED`。
- `doctor`、`session list`、`doc api` 等 CLI 命令能正常返回 JSON。
- 因此采用 MCP → 官方 CLI → 官方本地编辑器桥接。不要把官方 README 的功能描述替代本机实测。

参考：[嘉立创官方客户端 CLI](https://github.com/easyeda/easyeda-client-cli)、[官方 CLI 使用说明](https://prodocs.lceda.cn/cn/api/guide/cli.html)、[MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk/tree/v1.x)、[Codex MCP 配置](https://developers.openai.com/codex/mcp)。

## 本地安装

需要 Node.js、pnpm、已经激活的嘉立创 EDA 专业版桌面客户端。将本目录复制到稳定的本机目录，例如 `~/.local/share/lceda-pro-mcp`，然后：

```sh
pnpm install --frozen-lockfile --ignore-scripts
node verify.mjs
codex mcp add lceda-pro -- /absolute/path/to/node /absolute/path/to/server.mjs
```

GUI 启动的 Codex 可能没有终端 PATH，因此注册时使用 Node 和脚本的绝对路径。默认应用路径是 `/Applications/嘉立创EDA(专业版).app/Contents/MacOS/LCEDA-Pro`；其他安装路径使用 `LCEDA_CLI` 环境变量配置。

建议只给这个服务设置 `startup_timeout_sec = 20`、`tool_timeout_sec = 190`。保留其他服务、既有权限设置和用户配置；修改前做本地备份。适配器仅使用 stdio，不监听网络端口。

## 工具

| 工具 | 用途 |
| --- | --- |
| `lceda_doctor` | 官方桥接健康与版本检查 |
| `lceda_list_sessions` | 列出编辑器会话与工程 |
| `lceda_api_reference` | 获取官方扩展 API 参数与返回值定义 |
| `lceda_format_reference` | 获取原生工程格式定义 |
| `lceda_open_project` | 按绝对路径打开指定工程 |
| `lceda_close_session` | 关闭由 CLI 创建的会话 |
| `lceda_invoke` | 在指定会话中调用官方扩展 API，可编辑及导出工程 |

调用使用 `execFile` 参数数组，不经过 shell 拼接。编辑工具如实标记为可变更设计；它具有官方扩展 API 的能力，应仅在用户授权的项目范围内调用。

## 验证边界

`verify.mjs` 验证 MCP 握手、工具发现、官方 API 文档查询、会话枚举及非法参数拒绝；`doctor.ok=true` 只说明探测命令成功，**必须另外检查 `connected`**。指定 `LCEDA_TEST_SESSION` 后，验证器还通过 MCP 调用编辑器，回读版本与客户端状态。

这不替代原生工程导入后的网表比对、封装与孔位检查、ERC/DRC、PCB 导出复核，也不构成机械装配或制造验收。
