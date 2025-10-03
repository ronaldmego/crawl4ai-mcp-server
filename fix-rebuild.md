despues de cambios hacer:


```bash
cd /mnt/c/Users/ronal/APPs/crawl4ai-mcp-server

# 1. Detener y borrar contenedor actual
docker stop crawl4ai-mcp && docker rm crawl4ai-mcp

# 2. Rebuild imagen
docker build --platform linux/amd64 -t crawl4ai-mcp:local .

# 3. Lanzar nuevo contenedor
docker run -d --name crawl4ai-mcp -p 8002:8002 crawl4ai-mcp:local

# 4. Verificar que está running
docker ps | grep crawl4ai
```