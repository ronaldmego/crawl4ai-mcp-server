# Crawl4AI MCP Server - Setup Guide

Alternativa self-hosted a Firecrawl para scraping web sin límites de créditos.

Memoria:
```bash
group_id: crawl4ai
```

## Quick Steps

```bash
# 1. Clonar repo
cd /path/to/workspace
git clone https://github.com/sadiuysal/crawl4ai-mcp-server.git
cd crawl4ai-mcp-server

# 2. Aplicar fix de Dockerfile (ver sección Fix)

# 3. Build optimizado
docker build --platform linux/amd64 -t crawl4ai-mcp:local .

# 4. Test
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | docker run --rm -i crawl4ai-mcp:local

# 5. Configurar Claude Desktop (ver sección Config)

# 6. Reiniciar Claude Desktop
```

## Problema Original

El repo `sadiuysal/crawl4ai-mcp-server` tiene un bug en el Dockerfile:
- Instala Playwright browsers como `root` en `/root/.cache/`
- Luego cambia a usuario `appuser`
- `appuser` no tiene acceso a los browsers instalados
- **Resultado**: Error "Executable doesn't exist"

## Fix del Dockerfile

Reemplazar Stage 4 (desde línea ~50) con:

```dockerfile
# Stage 4: Final runtime image
FROM browsers as runtime

# Copy application code
COPY . .

# Create directories for outputs
RUN mkdir -p /app/crawls /app/test_crawls

# Create non-root user AFTER installing browsers
RUN adduser --disabled-password --gecos '' --uid 1000 appuser

# Install Playwright browsers for appuser
USER appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
RUN python -m playwright install chromium

# Set permissions
USER root
RUN chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app \
    CRAWL4AI_MCP_LOG=INFO

# Expose volume mount points
VOLUME ["/app/crawls", "/app/test_crawls"]

# Default command runs the MCP server
CMD ["python", "-m", "crawler_agent.mcp_server"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import crawler_agent.mcp_server; print('OK')" || exit 1

# Labels for metadata
LABEL maintainer="crawler_agent" \
      description="Crawl4AI MCP Server - Web scraping and crawling tools for AI agents" \
      version="1.0.0"
```

**Key changes**:
1. Instala browsers como `appuser` (no root)
2. Define `PLAYWRIGHT_BROWSERS_PATH` para appuser
3. Ejecuta `playwright install` después de cambiar a appuser

## Configuración Claude Desktop

Editar: `C:\Users\[user]\AppData\Roaming\Claude\claude_desktop_config.json` (Windows)  
o `~/.config/claude/claude_desktop_config.json` (Linux)

```json
{
  "mcpServers": {
    "crawl4ai": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "crawl4ai-mcp:local"
      ]
    }
  }
}
```

**Reiniciar Claude Desktop completamente** después del cambio.

## Tools Disponibles

1. **scrape** - Single page scraping
2. **crawl** - Multi-page crawl con depth control
3. **crawl_site** - Site completo con persistencia
4. **crawl_sitemap** - Crawl vía sitemap.xml

## Setup en VPS (Producción)

### Diferencias vs Local

```bash
# En VPS, agregar resource limits
docker build --platform linux/amd64 -t crawl4ai-mcp:vps .

# Run con límites
docker run -d \
  --name crawl4ai-mcp \
  --restart unless-stopped \
  --cpus="2" \
  --memory="1g" \
  -p 127.0.0.1:8051:8051 \
  -e TRANSPORT=sse \
  -e HOST=127.0.0.1 \
  -e PORT=8051 \
  crawl4ai-mcp:vps
```

### Config para VPS (SSE Transport)

```json
{
  "mcpServers": {
    "crawl4ai": {
      "transport": "sse",
      "url": "http://vps-ip:8051/sse"
    }
  }
}
```

### Firewall (UFW)

```bash
# Solo localhost puede acceder al puerto
ufw allow from 127.0.0.1 to any port 8051
ufw deny 8051
```

## Comparación con Alternativas

| Repo | Stars | Pros | Contras |
|------|-------|------|---------|
| **sadiuysal/crawl4ai-mcp-server** | 5 | Docker ready, 4 tools scraping, docs EN | Bug Playwright (fixed) |
| weidwonder/crawl4ai-mcp-server | 118 | Más features, search engines | Sin Docker image, docs CN |
| coleam00/mcp-crawl4ai-rag | 1,728 | RAG completo, Knowledge Graph | Requiere Supabase + Neo4j |

**Elegimos sadiuysal porque**:
- Enfoque en scraping (reemplazo directo de Firecrawl)
- Docker image disponible
- Setup más simple (sin deps externas)

## Troubleshooting

### Error: "Executable doesn't exist"
- **Causa**: Dockerfile sin fix
- **Solución**: Aplicar fix de Stage 4

### Warning: "platform (linux/arm64) vs (linux/amd64)"
- **Causa**: Imagen compilada para ARM
- **Solución**: Build local con `--platform linux/amd64`

### Tools no aparecen en Claude
- **Solución**: Reiniciar Claude Desktop completamente
- Verificar config JSON válido
- Check Docker container con `docker ps`

## Limpieza

```bash
# Remover imagen vieja
docker rmi uysalsadi/crawl4ai-mcp-server:latest

# Limpiar builds fallidos
docker image prune -f

# Ver imágenes actuales
docker images | grep crawl4ai
```

## Seguridad

**Protecciones incluidas** (safety.py):
- Bloquea localhost/127.0.0.1/::1
- Bloquea IPs privadas (RFC 1918)
- Bloquea file:// schemes
- Bloquea dominios .local/.internal/.lan

**CVE Conocido**: Crawl4AI ≤0.4.247 tiene SSRF (CVE-2025-28197)
- Verificar versión en requirements.txt post-fix

## Notas

- `--rm` en args: Container se auto-destruye después de cada uso (stateless)
- Build time: ~10-15 mins (descarga Chromium)
- Performance: Nativo AMD64 sin emulación
- Cost: $0 (vs Firecrawl $20/mes)