/**
 * MCP Proxy Server — Air Liquide BW6 Demo
 *
 * Spawns the BW6 MCP server as a child process (stdio transport),
 * then exposes a plain HTTP+CORS API the browser can call.
 *
 * Configure the server command in mcp-config.json before starting.
 * Run: npm start
 * Listens on http://localhost:3001
 */

import express from 'express';
import cors from 'cors';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const require = createRequire(import.meta.url);
const __dir  = path.dirname(fileURLToPath(import.meta.url));

// ── Load config ───────────────────────────────────────────────────────
const cfgPath = path.join(__dir, 'mcp-config.json');
let cfg;
try {
  cfg = require(cfgPath);
} catch (e) {
  console.error('[proxy] Cannot read mcp-config.json:', e.message);
  process.exit(1);
}

const { command, args = [], env: extraEnv = {} } = cfg;
if (!command) {
  console.error('[proxy] mcp-config.json must have a "command" field.');
  process.exit(1);
}
const PORT = parseInt(process.env.PORT || '3001', 10);

// ── Express ───────────────────────────────────────────────────────────
const app = express();
app.use(cors({ origin: '*' }));
app.use(express.json());

// ── MCP client (lazy, auto-restart) ──────────────────────────────────
let mcpClient = null;

async function getClient() {
  if (mcpClient) return mcpClient;

  console.log(`[proxy] Spawning MCP server: ${command} ${args.join(' ')}`);

  const transport = new StdioClientTransport({
    command,
    args,
    env: { ...process.env, ...extraEnv },
  });

  const client = new Client(
    { name: 'air-liquide-browser-proxy', version: '1.0.0' },
    { capabilities: {} }
  );

  transport.onclose = () => {
    console.warn('[proxy] MCP server process closed — will respawn on next request');
    mcpClient = null;
  };
  transport.onerror = (err) => {
    console.error('[proxy] Transport error:', err.message);
    mcpClient = null;
  };

  await client.connect(transport);
  console.log('[proxy] Connected to BW6 MCP server via stdio');
  mcpClient = client;
  return client;
}

// ── Routes ────────────────────────────────────────────────────────────
app.get('/health', (_, res) =>
  res.json({ ok: true, command, args, connected: !!mcpClient })
);

app.get('/mcp/tools', async (_, res) => {
  try {
    const client = await getClient();
    const { tools } = await client.listTools();
    res.json({ ok: true, tools });
  } catch (err) {
    mcpClient = null;
    console.error('[proxy] listTools error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/mcp/call', async (req, res) => {
  const { name, arguments: toolArgs } = req.body;
  if (!name) return res.status(400).json({ ok: false, error: 'Missing tool name' });

  console.log(`[proxy] → callTool "${name}"`, JSON.stringify(toolArgs));
  try {
    const client = await getClient();
    const result = await client.callTool({ name, arguments: toolArgs || {} });
    console.log(`[proxy] ← "${name}" ok`);
    res.json({ ok: true, result });
  } catch (err) {
    mcpClient = null;
    console.error(`[proxy] callTool "${name}" error:`, err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ── Start ─────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\nMCP proxy → http://localhost:${PORT}`);
  console.log(`  BW6 command : ${command} ${args.join(' ')}`);
  console.log('  Routes      : GET /health · GET /mcp/tools · POST /mcp/call\n');
});
