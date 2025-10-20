# Bug Warnings

Cuando se Claude Desktop usa el MCP, funciona, pero aparecen mensajes de warning que no interrumpen el funcionamiento, pero generan alertas inncesarias.

Confirmado: El problema ESTÁ PRESENTE en tu contenedor actual.
Los warnings son mensajes de progreso [INIT], [FETCH], [SCRAPE], [COMPLETE] que Crawl4AI está enviando a STDOUT, mezclándose con el protocolo MCP JSON.
Diagnóstico - Verifica la librería Crawl4AI:

```bash
docker exec crawl4ai-mcp python -c "import crawl4ai; print(crawl4ai.__version__)"
```

Solución:
Los mensajes vienen de Crawl4AI. Necesitamos deshabilitar su output. Revisa si hay variables de entorno:

El problema está en Crawl4AI - está enviando mensajes de progreso a STDOUT.
Solución:  Modificar `crawler_agent\mcp_server.py` para silenciar Crawl4AI:

```python
# En mcp_server.py, después de los imports, agregar:
import sys
import io

# Redirigir stdout de crawl4ai a devnull
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self
    
    def __exit__(self, *args):
        sys.stdout = self._original_stdout

# Modificar _run_scrape para usar el context manager:
async def _run_scrape(args: ScrapeArgs) -> ScrapeResult:
    require_public_http_url(str(args.url))
    with SuppressOutput():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=str(args.url),
                script=args.script,
            )
    # resto del código...
```

necesitas modificar ese archivo. El problema es que Crawl4AI emite mensajes de progreso ([INIT], [FETCH], etc.) a STDOUT, pero MCP stdio requiere SOLO JSON válido en STDOUT.
Solución - Agregar al inicio del archivo (después de imports):

```python
import io
from contextlib import redirect_stdout

# Supresor de output de Crawl4AI
class SuppressCrawl4AIOutput:
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self
    
    def __exit__(self, *args):
        sys.stdout = self._stdout
```

Luego envolver todas las llamadas a crawler.arun() así:
```python
async def _run_scrape(args: ScrapeArgs) -> ScrapeResult:
    require_public_http_url(str(args.url))
    async with AsyncWebCrawler() as crawler:
        with SuppressCrawl4AIOutput():  # <-- AGREGAR ESTO
            result = await crawler.arun(
                url=str(args.url),
                script=args.script,
            )
    # resto del código...
```

