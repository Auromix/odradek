// Local Odradek adapter. Not a vendor-provided MCP server.
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const exec = promisify(execFile);
const binary = process.env.LCEDA_CLI || '/Applications/嘉立创EDA(专业版).app/Contents/MacOS/LCEDA-Pro';
const cliEnvironment = {...process.env};
// MCP hosts may omit TMPDIR. The vendor's macOS bridge socket lives in the
// per-user temp directory, so using /tmp would silently address another bridge.
if (process.platform === 'darwin' && !cliEnvironment.TMPDIR) {
  const {stdout} = await exec('/usr/bin/getconf', ['DARWIN_USER_TEMP_DIR']);
  cliEnvironment.TMPDIR = stdout.trim();
}
const server = new McpServer({name: 'odradek-lceda-cli-adapter', version: '0.1.0'}, {
  instructions: 'Local project-maintained adapter for the official JLCEDA desktop CLI. Not the vendor MCP server. Call doctor, list sessions, then query API documentation before editing. Require an activated client. Use explicit session IDs and verify returned ok and exported files. A connected bridge does not prove a project is editable or a PCB is manufacturable. Do not bypass activation or editor permissions.'
});
const readOnly = {readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false};
const changing = {readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false};
const str = z.string().min(1);

export function parseEnvelope(stdout) {
  for (const line of stdout.trim().split('\n').reverse()) {
    try {
      const result = JSON.parse(line);
      if (typeof result.ok === 'boolean') return result;
    } catch {}
  }
  throw new Error('Official CLI did not return a JSON response envelope');
}

async function run(args, timeout=65000) {
  let output;
  try { output = await exec(binary, args, {env:cliEnvironment, timeout, maxBuffer: 16*1024*1024, windowsHide: true}); }
  catch (error) {
    if (error.stdout) {
      try { return result(parseEnvelope(error.stdout)); } catch {}
    }
    return result({ok:false, error:{code:'CLI_EXECUTION_FAILED', message:String(error.message)}});
  }
  try { return result(parseEnvelope(output.stdout)); }
  catch (error) { return result({ok:false, error:{code:'CLI_PROTOCOL_ERROR', message:error.message}}); }
}
function result(value) {
  return {content:[{type:'text', text:JSON.stringify(value)}], structuredContent:value, isError:!value.ok};
}
function tool(name, description, inputSchema, annotations, handler) {
  server.registerTool(name, {description, inputSchema, annotations}, handler);
}

tool('lceda_doctor', 'Probe the official local editor bridge and version. connected is not proof of activation or an editable project.', {}, readOnly,
  () => run(['doctor']));
tool('lceda_list_sessions', 'List editor sessions and project paths via the official CLI.', {}, readOnly,
  () => run(['session','list']));
tool('lceda_api_reference', 'Read official extension API classes, method signatures, or enum documentation.', {
  class_name:str.optional(), method_name:str.optional()
}, readOnly, ({class_name,method_name}) => {
  if (method_name && !class_name) return result({ok:false,error:{code:'INVALID_ARGS',message:'method_name requires class_name'}});
  const args=['doc','api'];
  if(class_name) args.push('--class-name',class_name);
  if(method_name) args.push('--method-name',method_name);
  return run(args);
});
tool('lceda_format_reference', 'Read official native project file-format documentation.', {
  class_name:str.optional()
}, readOnly, ({class_name}) => run(['doc','format',...(class_name?['--class-name',class_name]:[])]));
tool('lceda_open_project', 'Open an explicitly selected local EDA project. Use an absolute path; opens a visible editor by default. The current Mac CLI requires a path.', {
  path: str.refine(s=>s.startsWith('/'), 'Absolute local path required'), headless:z.boolean().default(false)
}, changing, ({path,headless}) => run(['open','--path',path,'--headless',String(headless)],125000));
tool('lceda_close_session', 'Close a session created through the CLI when its work is finished. Does not force-kill the application.', {
  session:str, destroy:z.boolean().default(false)
}, changing, ({session,destroy}) => run(['session','close','--session',session,...(destroy?['--destroy']:[])]));
tool('lceda_invoke', 'Run an async JavaScript body through the official editor extension API in an explicit session. This tool can modify design files; query API documentation first. Do not use it for unrelated system actions. Values in args are accessible via __CLI__.args.', {
  session:str, code:str.max(250000), args:z.record(z.string(),z.unknown()).optional(), timeout_ms:z.number().int().min(1000).max(180000).default(60000)
}, {...changing,destructiveHint:true,openWorldHint:true}, ({session,code,args,timeout_ms}) => {
  const cli=['invoke','--session',session,'--ext-uuid','eda','--code',code,'--timeout',String(timeout_ms)];
  if(args!==undefined) cli.push('--args',JSON.stringify(args));
  return run(cli, timeout_ms+5000);
});

await server.connect(new StdioServerTransport());
