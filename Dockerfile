# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY . .

RUN uv pip install --system --no-cache-dir .

# --- Runtime stage ---
FROM python:3.13-slim

RUN useradd -r -m -d /home/mcp mcp

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/clr-akvorado-mcp /usr/local/bin/clr-akvorado-mcp

USER mcp
EXPOSE 8000

ENTRYPOINT ["clr-akvorado-mcp"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
