# EU5 Strategy MCP — Windows / Steam (v0.1)

Read-only MCP bridge for EU5 autosaves. The game continues running normally; the bridge only sees **completed saves**, not the game's live memory.

## Setup (PowerShell)

### Quick start on Windows

Download or clone this repository, open PowerShell in its folder, and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-windows.ps1
.\start-windows.ps1
```

Read these scripts before running. Python 3.11+ must already be installed. The installer creates a local virtual environment, installs dependencies, downloads Rakaly from the official GitHub release, verifies the release's SHA-256 checksum, and stores the executable in `.tools`. No administrator privileges are needed. Start a local EU5 game and enable autosaves; leave the PowerShell window running.

### Manual setup

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

### Connect securely to ChatGPT web

1. In [OpenAI Platform](https://platform.openai.com/), open tunnel settings for your organization and create a tunnel linked to your ChatGPT workspace. Tunnel permissions are required.
2. Download the Windows [tunnel-client](https://github.com/openai/tunnel-client/releases/latest) and run `tunnel-client help quickstart` for current syntax.
3. Configure a profile forwarding to `http://127.0.0.1:8765/mcp`. Enter any required runtime API key locally; never paste secrets into chat, GitHub or screenshots.
4. Validate with `tunnel-client doctor --profile <your-profile> --explain`, then keep `tunnel-client run --profile <your-profile>` running.
5. In ChatGPT **Plugins → Add custom MCP server → Tunnel**, select the same tunnel and create a private plugin. Test `get_game_state`.

Both the EU5 MCP and tunnel-client processes must stay running while playing. The tunnel uses outbound HTTPS and does not require router port forwarding. See the [official Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## Available tools

- `get_game_state`: latest ingested save and freshness.
- `list_save_fields`: discover real parsed schema.
- `get_save_data`: read an explicitly chosen subtree (25k character cap).
- `compare_snapshots`: compare a scalar across the last two snapshots.
- `get_player_economy`: verified typed economy extraction for the currently played nation (EU5 1.4.x).

Economy parsing was validated against an actual EU5 1.4.5 Ottoman autosave, which is **not included in this public repository**. Other game patches may differ. Diplomacy and military schemas still require validation. Before each strategic answer the AI should check save date and freshness, and never present old data as live.

## Browser ChatGPT limitation

ChatGPT web cannot directly connect to this local stdio server. That requires a separate authenticated, HTTPS remote MCP gateway/plugin, **not yet included**. Do not expose the local save database to the public internet. Windows ChatGPT desktop/Codex hosts may use local stdio MCP directly.

## Privacy and bounds

- No write access to game data, no game injection, no cheats.
- Full converted save JSON is stored locally in SQLite; game saves can be large, so monitor disk usage.
- Rakaly is a third-party binary; verify release provenance.
- A failed or incomplete save is retried on the next watcher pass; errors go to stderr, preserving the MCP stdio protocol.
