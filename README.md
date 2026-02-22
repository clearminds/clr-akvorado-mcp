# clr-akvorado-mcp

Network flow analysis via the Akvorado Console API

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
  "api_url": "https://akvorado.example.com",
  "api_user": "admin",
  "api_password": "your-password"
}
```

**Alternative:** Environment variables are also supported:

| Variable | Description | Example |
|----------|-------------|---------|
| `AKVORADO_API_URL` | Akvorado Console API URL | `https://akvorado.example.com` |
| `AKVORADO_API_USER` | API username | `admin` |
| `AKVORADO_API_PASSWORD` | API password | — |

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
