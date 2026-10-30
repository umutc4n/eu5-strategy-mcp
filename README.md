# EU5 Strategy MCP — Windows / Steam (v0.1)

Read-only MCP bridge for EU5 autosaves. The game continues running normally; the bridge only sees **completed saves**, not the game's live memory.

## Setup (PowerShell)

1. Install Python 3.11+.
2. Download the current **Windows Rakaly CLI** from https://github.com/rakaly/cli/releases and put `rakaly.exe` on PATH. Use a release supporting your EU5 patch; Rakaly v0.8.21 supports EU5 1.4.
3. From this folder run `py -m pip install -e .`.
4. Start EU5, configure autosaves (monthly if the game permits), and make a manual save to test.
5. Start a local MCP host with command `py` and arguments `-m`, `eu5_mcp` (working directory this folder). Alternatively, install and run `eu5-mcp`.

By default this reads `%USERPROFILE%\Documents\Paradox Interactive\Europa Universalis V\save games`. Set `EU5_SAVE_DIR` if saves are elsewhere (including OneDrive). Set `EU5_RAKALY` to the full executable path if needed. `EU5_MCP_DB` controls the SQLite history path.

The host's MCP server configuration should point at Python and this project's `eu5_mcp` module. It uses **stdio**. To check the parser independently: `rakaly json "C:\path\to\save.eu5"`.

### Local Streamable HTTP mode (for a secure tunnel)

PowerShell:

```powershell
$env:EU5_MCP_TRANSPORT = "streamable-http"
$env:EU5_MCP_PORT = "8765"
py -m eu5_mcp
```

The local MCP endpoint is `http://127.0.0.1:8765/mcp`. It binds to loopback only, intentionally has **no public listener**, and should never be exposed by raw port-forwarding. To use it in ChatGPT web, use an authenticated **Secure MCP Tunnel** and then install/connect a ChatGPT plugin. Follow the official [connect-and-test guide](https://developers.openai.com/plugins/deploy/connect-chatgpt). The tunnel and ChatGPT plugin are separate setup steps, not provided by this repository. Until those are configured, ChatGPT web cannot access your PC.

## Available tools

- `get_game_state`: latest ingested save and freshness.
- `list_save_fields`: discover real parsed schema.
- `get_save_data`: read an explicitly chosen subtree (25k character cap).
- `compare_snapshots`: compare a scalar across the last two snapshots.

We intentionally **do not pretend** economy, diplomacy or military fields have a stable schema across patches. Validate with a real EU5 save first, then implement typed domain tools. Before each strategic answer the AI should check save date and freshness, and never present old data as live.

## Browser ChatGPT limitation

ChatGPT web cannot directly connect to this local stdio server. That requires a separate authenticated, HTTPS remote MCP gateway/plugin, **not yet included**. Do not expose the local save database to the public internet. Windows ChatGPT desktop/Codex hosts may use local stdio MCP directly.

## Privacy and bounds

- No write access to game data, no game injection, no cheats.
- Full converted save JSON is stored locally in SQLite; game saves can be large, so monitor disk usage.
- Rakaly is a third-party binary; verify release provenance.
- A failed or incomplete save is retried on the next watcher pass; errors go to stderr, preserving the MCP stdio protocol.
