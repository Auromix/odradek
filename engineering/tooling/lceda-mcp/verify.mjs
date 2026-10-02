import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const client = new Client({name:'odradek-install-verifier',version:'1.0'});
const transport = new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('./server.mjs',import.meta.url))]});
const record={time:new Date().toISOString()};
try {
  await client.connect(transport);
  record.server=client.getServerVersion();
  const listing=await client.listTools();
  record.tools=listing.tools.map(t=>({name:t.name,annotations:t.annotations}));
  record.doctor=await client.callTool({name:'lceda_doctor',arguments:{}});
  record.api=await client.callTool({name:'lceda_api_reference',arguments:{class_name:'SYS_Environment',method_name:'getEditorCurrentVersion'}});
  record.sessions=await client.callTool({name:'lceda_list_sessions',arguments:{}});
  record.invalid_args=await client.callTool({name:'lceda_api_reference',arguments:{method_name:'getEditorCurrentVersion'}});
  for(const key of ['doctor','api','sessions']) {
    if(record[key].isError || record[key].structuredContent?.ok!==true) throw new Error(`${key} failed`);
  }
  if(record.invalid_args.isError!==true) throw new Error('Argument validation did not reject invalid input');
  if(process.env.LCEDA_TEST_SESSION) {
    record.editor=await client.callTool({name:'lceda_invoke',arguments:{session:process.env.LCEDA_TEST_SESSION,code:'return {version:eda.sys_Environment.getEditorCurrentVersion(), client:eda.sys_Environment.isClient()};',timeout_ms:20000}},undefined,{timeout:30000});
    if(record.editor.isError || record.editor.structuredContent?.ok!==true) throw new Error('Editor read failed');
  }
  record.passed=true;
  console.log(JSON.stringify({passed:true,server:record.server,tools:record.tools.length,doctor:record.doctor.structuredContent,sessions:record.sessions.structuredContent,editor:record.editor?.structuredContent}));
} finally {
  await writeFile(fileURLToPath(new URL('./verification.json',import.meta.url)),JSON.stringify(record,null,2));
  await client.close();
}
