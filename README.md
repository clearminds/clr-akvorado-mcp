# akvorado-mcp-server

Network flow analysis via Akvorado/ClickHouse

## Install

```bash
pip install akvorado-mcp-server
# or
uvx akvorado-mcp-server
```

## Configuration

**Preferred:** Configuration file at `~/.config/akvorado/credentials.json` (chmod 600):

```json
{
  "url": "https://akvorado.example.com"
}
```

**Note:** Akvorado typically doesn't require authentication.

**Alternative:** Environment variables are also supported:

| Variable | Description | Example |
|----------|-------------|---------|
| `AKVORADO_URL` | Akvorado URL | `https://akvorado.example.com` |

See `--help` for additional options:

```bash
akvorado-mcp-server --help
```

## Development

```bash
git clone https://github.com/clearminds/akvorado-mcp-server.git
cd akvorado-mcp-server
uv sync
uv run akvorado-mcp-server
```

## License

MIT
