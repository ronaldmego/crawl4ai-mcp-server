# Quick Setup Guide

Configuración rápida del Crawl4AI MCP Server en una nueva laptop.

## Opción 1: Setup Local (Recomendado para desarrollo)

### 1. Prerrequisitos
```bash
# Verificar que tienes Docker instalado
docker --version

# Verificar que tienes Git
git --version
```

### 2. Clonar y construir
```bash
# Clonar tu fork
git clone https://github.com/ronaldmego/crawl4ai-mcp-server.git
cd crawl4ai-mcp-server

# Construir imagen local
docker build -t crawl4ai-mcp:local .
# O usar el script helper
./docker-run.sh build
```

### 3. Probar que funciona
```bash
# Test básico
./docker-run.sh test

# Test manual
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | docker run --rm -i crawl4ai-mcp:local
```

### 4. Configurar Claude Desktop
Copiar el contenido de `claude-desktop-config.local.json` a tu configuración de Claude Desktop:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "crawl4ai-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--volume",
        "/tmp/crawl4ai-crawls:/app/crawls",
        "crawl4ai-mcp:local"
      ],
      "env": {
        "CRAWL4AI_MCP_LOG": "INFO"
      }
    }
  }
}
```

### 5. Reiniciar Claude Desktop
- Cerrar completamente Claude Desktop
- Abrir de nuevo
- Verificar que aparezcan las herramientas MCP

---

## Opción 2: Setup con Imagen Publicada (Más rápido)

### 1. Sin clonar nada, solo configurar Claude Desktop
Usar el contenido de `claude-desktop-config.example.json`:

```json
{
  "mcpServers": {
    "crawl4ai-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--volume",
        "/tmp/crawl4ai-crawls:/app/crawls",
        "uysalsadi/crawl4ai-mcp-server:latest"
      ],
      "env": {
        "CRAWL4AI_MCP_LOG": "INFO"
      }
    }
  }
}
```

### 2. Probar que funciona
```bash
# Docker descargará automáticamente la imagen
docker pull uysalsadi/crawl4ai-mcp-server:latest

# Test
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | docker run --rm -i uysalsadi/crawl4ai-mcp-server:latest
```

---

## Verificación Final

### En Claude Desktop deberías ver:
- 4 herramientas MCP disponibles:
  - `mcp_crawl4ai_scrape`
  - `mcp_crawl4ai_crawl` 
  - `mcp_crawl4ai_crawl_site`
  - `mcp_crawl4ai_crawl_sitemap`

### Test rápido en Claude Desktop:
```
Usa la herramienta scrape para obtener el contenido de https://example.com
```

### Troubleshooting

**Si no aparecen las herramientas:**
1. Verificar que Docker esté corriendo
2. Verificar sintaxis JSON de la configuración
3. Reiniciar Claude Desktop completamente
4. Revisar logs de Claude Desktop

**Si hay errores de permisos en Windows:**
- Cambiar `/tmp/crawl4ai-crawls` por `C:\temp\crawl4ai-crawls`
- Crear la carpeta manualmente si no existe

**Si hay errores de volumen:**
- Usar ruta absoluta en lugar de `./crawls`
- Ejemplo: `C:\Users\tu-usuario\crawls:/app/crawls`

---

## Comandos Útiles

```bash
# Ver imágenes Docker
docker images | grep crawl4ai

# Ver contenedores corriendo
docker ps

# Limpiar contenedores parados
docker container prune

# Reconstruir imagen local
docker build -t crawl4ai-mcp:local . --no-cache

# Ver logs detallados
docker run --rm -i -e CRAWL4AI_MCP_LOG=DEBUG crawl4ai-mcp:local
```

## Tiempo estimado
- **Opción 1 (Local):** 10-15 minutos
- **Opción 2 (Publicada):** 3-5 minutos