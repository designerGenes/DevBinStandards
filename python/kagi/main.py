"""
Kagi Search API Wrapper CLI

A command-line interface for the Kagi Search API, providing access to
Search, FastGPT, Universal Summarizer, and Enrichment APIs.
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Literal

import httpx
import typer
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

app = typer.Typer(help="Kagi Search API Wrapper")
console = Console()

# --- Models ---

class SearchRequest(BaseModel):
    q: str
    limit: int = 10

class SearchResult(BaseModel):
    t: int # Rank
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    published: Optional[str] = None

class SearchResponse(BaseModel):
    meta: dict
    data: Optional[List[SearchResult]] = None
    error: Optional[List[dict]] = None

class FastGPTResponse(BaseModel):
    meta: dict
    data: Optional[dict] = None
    error: Optional[List[dict]] = None

class SummarizeResponse(BaseModel):
    meta: dict
    data: Optional[dict] = None
    error: Optional[List[dict]] = None

class EnrichResponse(BaseModel):
    meta: dict
    data: Optional[List[dict]] = None
    error: Optional[List[dict]] = None



# --- Client ---

class KagiClient:
    BASE_URL = "https://kagi.com/api/v0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=60.0)

    def _get_headers(self):
        return {
            "Authorization": f"Bot {self.api_key}",
        }

    def search(self, query: str, limit: int = 10) -> SearchResponse:
        params = {"q": query, "limit": limit}
        response = self.client.get(
            f"{self.BASE_URL}/search", headers=self._get_headers(), params=params
        )
        return SearchResponse(**response.json())

    def fastgpt(self, query: str, cache: bool = True) -> FastGPTResponse:
        data = {"query": query}
        if cache:
            data["cache"] = "true"
        else:
            data["cache"] = "false"
            
        response = self.client.post(
            f"{self.BASE_URL}/fastgpt", headers=self._get_headers(), json=data
        )
        return FastGPTResponse(**response.json())

    def summarize(
        self,
        url: Optional[str] = None,
        text: Optional[str] = None,
        engine: str = "muriel",
        summary_type: str = "summary",
        target_language: Optional[str] = None,
        cache: bool = True,
    ) -> SummarizeResponse:
        params = {
            "engine": engine,
            "summary_type": summary_type,
            "cache": "true" if cache else "false",
        }
        if url:
            params["url"] = url
        elif text:
            params["text"] = text
            
        if target_language:
            params["target_language"] = target_language
        
        # The official client uses GET for summarize
        response = self.client.get(
            f"{self.BASE_URL}/summarize", headers=self._get_headers(), params=params
        )
        return SummarizeResponse(**response.json())

    def enrich_web(self, query: str) -> EnrichResponse:
        params = {"q": query}
        response = self.client.get(
            f"{self.BASE_URL}/enrich/web", headers=self._get_headers(), params=params
        )
        return EnrichResponse(**response.json())
    
    def enrich_news(self, query: str) -> EnrichResponse:
        params = {"q": query}
        response = self.client.get(
            f"{self.BASE_URL}/enrich/news", headers=self._get_headers(), params=params
        )
        return EnrichResponse(**response.json())


# --- Helpers ---

def get_api_key(api_key: Optional[str] = None) -> str:
    if api_key:
        return api_key
    
    # Try getting from env
    env_key = os.getenv("KAGI_API_KEY")
    if env_key:
        return env_key

    # Try loading from .env similarly to tavilySearch
    project_dir = Path(__file__).parent
    try:
        import subprocess
        result = subprocess.run(
            ["zsh", "-c", "unset KAGI_API_KEY; source $HOME/DEV/bin/autoload_environment.zsh; loadenv_verbose_masked .env >/dev/null 2>&1; echo $KAGI_API_KEY"],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[-1].strip()
    except Exception:
        pass

    raise ValueError("API key must be provided via --api-key or KAGI_API_KEY environment variable")


# --- Commands ---

@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="The search query"),
    limit: int = typer.Option(10, "--limit", help="Number of results"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Kagi API key"),
    format: str = typer.Option("table", "--format", help="Output format: json, table, tree"),
    use_env: bool = typer.Option(False, "--use-env", help="Use SEARCH_QUERY environment variable as query"),
):
    """
    Perform a general web search.
    """
    try:
        if use_env:
            env_query = os.getenv("SEARCH_QUERY")
            if env_query:
                query = env_query
            else:
                console.print("[red]--use-env specified but SEARCH_QUERY environment variable not found.[/red]")
                raise typer.Exit(1)
        if not query:
            console.print("[red]Query not provided.[/red]")
            raise typer.Exit(1)

        key = get_api_key(api_key)
        client = KagiClient(key)
        response = client.search(query, limit)

        if response.error:
            for err in response.error:
                console.print(f"[red]API Error ({err.get('code')}): {err.get('msg')}[/red]")
            return

        if format == "json":
            console.print_json(json.dumps(response.model_dump(), indent=2))
        elif format == "table":
            if response.data:
                for i, result in enumerate(response.data, 1):
                    console.print(f"\n[bold]{i}. {result.title or 'No Title'}[/bold]")
                    console.print(f"   [blue]{result.url or 'No URL'}[/blue]")
                    if result.snippet:
                        console.print(f"   [dim]{result.snippet}[/dim]")
            if not response.data and not response.error:
                 console.print("[yellow]No results found.[/yellow]")

        elif format == "tree":
            tree = Tree(f"[bold cyan]Search Results for: {query}[/bold cyan]")
            if response.data:
                for result in response.data:
                    branch = tree.add(f"[bold]{result.title or 'No Title'}[/bold]")
                    branch.add(f"[blue]{result.url or 'No URL'}[/blue]")
                    if result.snippet:
                        branch.add(f"[green]{result.snippet}[/green]")
            console.print(tree)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def fastgpt(
    query: Optional[str] = typer.Argument(None, help="The query to answer"),
    cache: bool = typer.Option(True, "--cache/--no-cache", help="Use cache"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Kagi API key"),
    format: str = typer.Option("panel", "--format", help="Output format: json, panel"),
    use_env: bool = typer.Option(False, "--use-env", help="Use SEARCH_QUERY environment variable as query"),
):
    """
    Answer a query using FastGPT.
    """
    try:
        if use_env:
            env_query = os.getenv("SEARCH_QUERY")
            if env_query:
                query = env_query
            else:
                console.print("[red]--use-env specified but SEARCH_QUERY environment variable not found.[/red]")
                raise typer.Exit(1)
        if not query:
            console.print("[red]Query not provided.[/red]")
            raise typer.Exit(1)

        key = get_api_key(api_key)
        client = KagiClient(key)
        response = client.fastgpt(query, cache)

        if response.error:
            for err in response.error:
                console.print(f"[red]API Error ({err.get('code')}): {err.get('msg')}[/red]")
            return

        if format == "json":
            console.print_json(json.dumps(response.model_dump(), indent=2))
        else:
            if response.data:
                output = response.data.get("output", "")
                console.print(Panel.fit(Text(output), title=f"FastGPT Answer: {query}"))
                
                refs = response.data.get("references", [])
                if refs:
                    console.print("\n[bold]References:[/bold]")
                    for ref in refs:
                        console.print(f"- {ref.get('title', 'Unknown')} ({ref.get('url', 'No URL')})")
            elif not response.error:
                console.print("[yellow]No answer returned.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def summarize(
    url: Optional[str] = typer.Option(None, "--url", help="URL to summarize"),
    text: Optional[str] = typer.Option(None, "--text", help="Text to summarize"),
    engine: str = typer.Option("muriel", "--engine", help="Summarization engine (muriel, agnes, daphne)"),
    summary_type: str = typer.Option("summary", "--type", help="Type: summary or takeaway"),
    target_language: Optional[str] = typer.Option(None, "--lang", help="Target language code"),
    cache: bool = typer.Option(True, "--cache/--no-cache", help="Use cache"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Kagi API key"),
    format: str = typer.Option("panel", "--format", help="Output format: json, panel"),
):
    """
    Summarize content from a URL or text.
    """
    if not url and not text:
        console.print("[red]Error: Must provide either --url or --text[/red]")
        raise typer.Exit(1)

    try:
        key = get_api_key(api_key)
        client = KagiClient(key)
        response = client.summarize(
            url=url,
            text=text,
            engine=engine,
            summary_type=summary_type,
            target_language=target_language,
            cache=cache
        )

        if response.error:
            for err in response.error:
                console.print(f"[red]API Error ({err.get('code')}): {err.get('msg')}[/red]")
            return

        if format == "json":
            console.print_json(json.dumps(response.model_dump(), indent=2))
        else:
            if response.data:
                output = response.data.get("output", "")
                console.print(Panel.fit(Text(output), title="Summary"))
            elif not response.error:
                console.print("[yellow]No summary returned.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def enrich(
    query: Optional[str] = typer.Argument(None, help="The query to enrich"),
    kind: str = typer.Option("web", "--kind", help="Type of enrichment: web or news"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Kagi API key"),
    format: str = typer.Option("table", "--format", help="Output format: json, table"),
    use_env: bool = typer.Option(False, "--use-env", help="Use SEARCH_QUERY environment variable as query"),
):
    """
    Get enriched content results (Teclis/TinyGem).
    """
    try:
        if use_env:
            env_query = os.getenv("SEARCH_QUERY")
            if env_query:
                query = env_query
            else:
                console.print("[red]--use-env specified but SEARCH_QUERY environment variable not found.[/red]")
                raise typer.Exit(1)
        if not query:
            console.print("[red]Query not provided.[/red]")
            raise typer.Exit(1)

        key = get_api_key(api_key)
        client = KagiClient(key)
        
        if kind == "web":
            response = client.enrich_web(query)
        elif kind == "news":
            response = client.enrich_news(query)
        else:
            console.print(f"[red]Unknown enrichment kind: {kind}[/red]")
            raise typer.Exit(1)

        if response.error:
            for err in response.error:
                console.print(f"[red]API Error ({err.get('code')}): {err.get('msg')}[/red]")
            return

        if format == "json":
            console.print_json(json.dumps(response.model_dump(), indent=2))
        else:
            table = Table(title=f"Enrichment Results ({kind}): {query}")
            table.add_column("Type", style="dim", width=4)
            table.add_column("Title", style="bold cyan")
            table.add_column("URL", style="blue")
            
            if response.data:
                for item in response.data:
                    # Structure might vary slightly, adapting generally
                    rank = item.get("t", "?")
                    title = item.get("title", "No Title")
                    url = item.get("url", "No URL")
                    table.add_row(str(rank), title, url)
            
            console.print(table)
            if not response.data and not response.error:
                 console.print("[yellow]No results found.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
