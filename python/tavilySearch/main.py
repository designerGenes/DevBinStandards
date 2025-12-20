"""
Tavily Search API Wrapper CLI

A command-line interface for the Tavily AI Search API, providing easy access
to web search functionality with customizable output formats.
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Union

import httpx
import typer
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(help="Tavily AI Search API Wrapper")
console = Console()


class SearchRequest(BaseModel):
    """Request model for Tavily Search API."""

    query: str = Field(..., description="The search query to execute")
    auto_parameters: bool = Field(default=False, description="Auto-configure parameters")
    topic: str = Field(default="general", description="Search category: general, news, finance")
    search_depth: str = Field(default="basic", description="Search depth: basic or advanced")
    chunks_per_source: int = Field(default=3, ge=1, le=3, description="Chunks per source for advanced search")
    max_results: int = Field(default=5, ge=0, le=20, description="Maximum results to return")
    time_range: Optional[str] = Field(default=None, description="Time range: day, week, month, year")
    start_date: Optional[str] = Field(default=None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="End date YYYY-MM-DD")
    include_answer: Union[bool, str] = Field(default=False, description="Include LLM answer: false, true, basic, advanced")
    include_raw_content: Union[bool, str] = Field(default=False, description="Include raw content: false, true, markdown, text")
    include_images: bool = Field(default=False, description="Include image search results")
    include_image_descriptions: bool = Field(default=False, description="Include image descriptions")
    include_favicon: bool = Field(default=False, description="Include favicon URLs")
    include_domains: Optional[List[str]] = Field(default=None, description="Domains to include")
    exclude_domains: Optional[List[str]] = Field(default=None, description="Domains to exclude")
    country: Optional[str] = Field(default=None, description="Boost results from country")
    include_credits: bool = Field(default=False, description="Include credit usage info")


class SearchResult(BaseModel):
    """Model for individual search result."""

    title: str
    url: str
    content: str
    score: float
    raw_content: Optional[str] = None
    favicon: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model from Tavily Search API."""

    query: str
    answer: Optional[str] = None
    images: List[dict] = Field(default_factory=list)
    results: List[SearchResult]
    response_time: float
    auto_parameters: Optional[dict] = None
    usage: Optional[dict] = None
    request_id: Optional[str] = None


class TavilyClient:
    """Client for interacting with Tavily Search API."""

    BASE_URL = "https://api.tavily.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute search request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = request.model_dump(exclude_unset=True)

        response = self.client.post(f"{self.BASE_URL}/search", headers=headers, json=data)
        response.raise_for_status()

        return SearchResponse(**response.json())


def get_api_key(api_key: Optional[str] = None) -> str:
    """Get API key from parameter or environment."""
    if api_key:
        return api_key
    env_key = os.getenv("TAVILY_API_KEY")
    if not env_key:
        raise ValueError("API key must be provided via --api-key or TAVILY_API_KEY environment variable")
    return env_key


def display_json(response: SearchResponse):
    """Display response as JSON."""
    console.print_json(json.dumps(response.model_dump(), indent=2))


def display_table(response: SearchResponse):
    """Display response as a table."""
    table = Table(title=f"Search Results for: {response.query}")
    table.add_column("Title", style="bold cyan", no_wrap=True)
    table.add_column("URL", style="blue")
    table.add_column("Score", justify="right")
    table.add_column("Content", max_width=80)

    for result in response.results:
        table.add_row(result.title, result.url, f"{result.score:.4f}", result.content)

    console.print(table)

    if response.answer:
        console.print(Panel.fit(Text(response.answer, style="green"), title="Answer"))

    if response.usage:
        console.print(f"Credits used: {response.usage.get('credits', 'N/A')}")


def display_tree(response: SearchResponse):
    """Display response as a tree."""
    tree = Tree(f"[bold cyan]Search Results for: {response.query}[/bold cyan]")

    for i, result in enumerate(response.results, 1):
        branch = tree.add(f"[bold]{i}. {result.title}[/bold] (Score: {result.score:.4f})")
        branch.add(f"[blue]{result.url}[/blue]")
        branch.add(f"[green]{result.content}[/green]")

    console.print(tree)

    if response.answer:
        console.print(Panel.fit(Text(response.answer, style="yellow"), title="Answer"))


@app.command()
def search(
    query: str = typer.Argument(..., help="The search query"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Tavily API key"),
    format: str = typer.Option("table", "--format", help="Output format: json, table, tree"),
    auto_parameters: bool = typer.Option(False, "--auto-parameters", help="Auto-configure parameters"),
    topic: str = typer.Option("general", "--topic", help="Search topic: general, news, finance"),
    search_depth: str = typer.Option("basic", "--search-depth", help="Search depth: basic, advanced"),
    chunks_per_source: int = typer.Option(3, "--chunks-per-source", help="Chunks per source (1-3)"),
    max_results: int = typer.Option(5, "--limit", help="Maximum results (0-20)"),
    time_range: Optional[str] = typer.Option(None, "--time-range", help="Time range: day, week, month, year"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date YYYY-MM-DD"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date YYYY-MM-DD"),
    include_answer: Optional[str] = typer.Option(None, "--include-answer", help="Include answer: true, false, basic, advanced"),
    include_raw_content: Optional[str] = typer.Option(None, "--include-raw-content", help="Include raw content: true, false, markdown, text"),
    include_images: bool = typer.Option(False, "--include-images", help="Include images"),
    include_image_descriptions: bool = typer.Option(False, "--include-image-descriptions", help="Include image descriptions"),
    include_favicon: bool = typer.Option(False, "--include-favicon", help="Include favicons"),
    include_domains: Optional[List[str]] = typer.Option(None, "--include-domains", help="Domains to include"),
    exclude_domains: Optional[List[str]] = typer.Option(None, "--exclude-domains", help="Domains to exclude"),
    country: Optional[str] = typer.Option(None, "--country", help="Boost country results"),
    include_credits: bool = typer.Option(False, "--include-credits", help="Include credit usage"),
):
    """
    Search the web using Tavily AI Search API.

    Example: tavilySearch "who is Leo Messi" --limit 10 --format json
    """
    # Auto-load environment variables from project .env file if API key not set
    if not os.getenv("TAVILY_API_KEY"):
        # Get the project directory (where main.py is located)
        project_dir = Path(__file__).parent
        original_cwd = os.getcwd()
        
        try:
            # Change to project directory to load .env file
            os.chdir(project_dir)
            # Use zsh to source the autoload script and print the key
            import subprocess
            # We need to unset TAVILY_API_KEY first in the subshell to ensure loadenv actually loads it
            # and we redirect stderr to /dev/null to avoid capturing the "loaded ..." messages
            result = subprocess.run(
                ["zsh", "-c", "unset TAVILY_API_KEY; source $HOME/DEV/bin/autoload_environment.zsh; loadenv_verbose_masked .env >/dev/null 2>&1; echo $TAVILY_API_KEY"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                # The stdout might still contain some noise if not perfectly silenced, so we take the last line
                output_lines = result.stdout.strip().split('\n')
                os.environ["TAVILY_API_KEY"] = output_lines[-1].strip()
        finally:
            # Always change back to the original directory
            os.chdir(original_cwd)
    
    try:
        key = get_api_key(api_key)

        # Parse include_answer and include_raw_content
        inc_answer = include_answer.lower() if include_answer else False
        if inc_answer in ("true", "basic", "advanced"):
            inc_answer = inc_answer if inc_answer != "true" else True
        else:
            inc_answer = False

        inc_raw = include_raw_content.lower() if include_raw_content else False
        if inc_raw in ("true", "markdown", "text"):
            inc_raw = inc_raw if inc_raw != "true" else True
        else:
            inc_raw = False

        request = SearchRequest(
            query=query,
            auto_parameters=auto_parameters,
            topic=topic,
            search_depth=search_depth,
            chunks_per_source=chunks_per_source,
            max_results=max_results,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date,
            include_answer=inc_answer,
            include_raw_content=inc_raw,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            include_favicon=include_favicon,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            country=country,
            include_credits=include_credits,
        )

        client = TavilyClient(key)
        response = client.search(request)

        if format == "json":
            display_json(response)
        elif format == "table":
            display_table(response)
        elif format == "tree":
            display_tree(response)
        else:
            console.print(f"[red]Unknown format: {format}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
