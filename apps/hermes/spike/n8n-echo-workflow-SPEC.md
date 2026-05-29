# n8n Echo Workflow Spec — Spike 1

Used by Spike 1 (MCP-client). You implement; this spec describes what it must do.

## Workflow shape

- **Trigger node:** MCP Server Trigger
- **Tool name:** `echo`
- **Tool description:** "Echo a string back with a 'pong: ' prefix. For testing MCP round-trip."
- **Logic:** `output = "pong: " + input.message`
- **Side effects:** none — no wiki writes, no API calls, no Telegram sends

## Input / output schema

Input:

```json
{ "message": "string, required" }
```

Output:

```json
{ "output": "string" }
```

## Self-test (independent of Hermes-Agent)

Once the workflow exists, verify it directly. The endpoint shape depends on how the MCP Server Trigger node exposes it — likely `/mcp/<workflow-id>/sse` or `/webhook/mcp/<id>`. Confirm in the node's UI.

```bash
# Adjust to actual endpoint shape
curl -sS -i -X POST "$N8N_MCP_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"tool": "echo", "input": {"message": "hello world"}}'
```

Expected: response containing `pong: hello world`.

## Sharing with Spike 1

Once the workflow exists and self-test passes:

1. Drop the endpoint URL at `spike-1-mcp/n8n-endpoint.txt` (gitignored).
2. Note the transport type (SSE / HTTP / stdio) — record at `spike-1-mcp/n8n-transport.txt`.

Then proceed to `spike-1-mcp/README.md`.

## Why an echo and not the real Mnemosyne ingest

The spike verifies the *integration mechanism* — does Hermes-Agent's MCP-client see and call n8n MCP tools at all? Mnemosyne ingest has side effects (wiki writes), conflates "did MCP work" with "did the wiki write correctly," and is hard to repeat in a tight loop. Echo is the smallest test that proves the wire.
