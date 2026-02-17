# akvorado-mcp-server

Network flow analysis via Akvorado/ClickHouse

## Install

```bash
pip install akvorado-mcp-server
# or
uvx akvorado-mcp-server
```

## Configuration

Configuration via environment variables. See `--help` for all options:

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
