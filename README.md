# clr-akvorado-mcp

Network flow analysis via Akvorado/ClickHouse

## Install

```bash
pip install clr-akvorado-mcp
# or
uvx clr-akvorado-mcp
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
clr-akvorado-mcp --help
```

## Development

```bash
git clone https://github.com/clearminds/clr-akvorado-mcp.git
cd clr-akvorado-mcp
uv sync
uv run clr-akvorado-mcp
```

## License

MIT
