# Spike 1 — MCP-client against n8n

**Goal:** verify Hermes-Agent can act as an MCP client, discover tools from an n8n MCP server, and successfully round-trip a call.

**Effort target:** 3-4 hours.

**Depends on:** n8n echo workflow exists and self-tests pass (see `../n8n-echo-workflow-SPEC.md`).

## Setup

1. Save the n8n MCP endpoint URL to `n8n-endpoint.txt` in this directory.
2. Save the transport type (SSE / HTTP / stdio) to `n8n-transport.txt`.
3. Configure Hermes-Agent to register n8n as an MCP server. Actual config command TBD — discover via `hermes config --help` or the project docs. Likely a YAML/JSON entry under an `mcp:` or `mcp_servers:` key.

## Test sequence

### 1.1 — Direct reachability (n8n side only)

```bash
./test-mcp-direct
```

Hits the n8n MCP endpoint with curl. Verifies the workflow itself before Hermes-Agent enters the picture.

**Pass:** n8n returns content containing `pong:`.
**Fail:** debug the n8n workflow first, not Hermes-Agent.

### 1.2 — Tool discovery

Start Hermes-Agent (`hermes` or `hermes-spike`). Run `/tools` (or whatever lists tools — check `/help`).

**Pass:** `echo` appears in the tool list with description from the workflow.
**Fail:** MCP server isn't being discovered. Check config path, server URL, transport type, n8n auth.

Capture into `spike-report.md` Section 1.2: the output of `/tools`.

### 1.3 — Tool invocation

Prompt the agent:

```
Use the echo tool with message "hello from spike 1"
```

**Pass:** agent calls the tool; response contains `pong: hello from spike 1`; n8n execution log shows the workflow ran.
**Fail:** agent doesn't call the tool, calls it but result is malformed, or output doesn't reach the agent.

Capture: agent's full response + n8n execution log entry.

### 1.4 — Latency

Repeat the invocation 5 times. Time each call:

- Wall-clock: `time` the prompt-response cycle if hermes is scriptable
- Agent-side: inspect the trajectory log timestamps

**Pass:** mean round-trip under 5s.
**Soft fail:** 5-10s (note as concern).
**Fail:** >10s.

### 1.5 — Error surfacing

Deactivate the n8n workflow. Prompt the agent to call echo again.

**Pass:** agent surfaces a clear error in its response.
**Fail:** agent hangs, returns garbage, or silently swallows the failure.

## What to record in `spike-report.md`

- Result per sub-test (1.1 - 1.5): Pass / Soft Fail / Fail
- Configuration friction notes — was MCP setup obvious or fight-the-system?
- Latency numbers (5 calls + mean)
- Subjective DX rating (1-5) for the MCP integration
- Anything surprising
