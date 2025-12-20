# Tavily Search API Wrapper

A comprehensive command-line interface for the Tavily AI Search API, designed to be highly accessible for AI agents and human users alike. This wrapper provides all features of the Tavily Search API with customizable output formats and clear, machine-readable responses.

## Features

- **Complete API Coverage**: Supports all parameters and features of the Tavily Search API
- **Multiple Output Formats**: JSON, table, and tree formats for different use cases
- **Rich CLI Interface**: Colorful, interactive command-line interface using Typer and Rich
- **AI Agent Friendly**: Clear structure, comprehensive docstrings, and type annotations
- **Flexible Configuration**: API key via environment variable or command-line option
- **Fast and Efficient**: Built with modern Python async capabilities

## Installation

### Prerequisites

- Python 3.12+
- `uv` package manager (recommended)

### Install with uv

```bash
cd /path/to/tavilySearch
uv sync
```

### Install dependencies manually

```bash
pip install typer rich httpx pydantic
```

## Setup

1. Get your Tavily API key from [Tavily](https://tavily.com/)
2. Set the environment variable:

```bash
export TAVILY_API_KEY="your-api-key-here"
```

Or pass it via `--api-key` option for each command.

## Usage

### Basic Search

```bash
tavilySearch "who is Leo Messi"
```

### Advanced Search with Options

```bash
tavilySearch "latest AI developments" \
  --limit 10 \
  --topic news \
  --search-depth advanced \
  --include-answer true \
  --format table
```

### Search with Date Filters

```bash
tavilySearch "climate change news" \
  --time-range week \
  --include-answer advanced \
  --format json
```

### Custom Domain Filtering

```bash
tavilySearch "Python tutorials" \
  --include-domains "realpython.com,docs.python.org" \
  --exclude-domains "stackoverflow.com" \
  --format tree
```

## Command Line Options

### Required Arguments

- `query`: The search query string

### Optional Flags

- `--api-key`: Tavily API key (or use `TAVILY_API_KEY` env var)
- `--format`: Output format (`json`, `table`, `tree`) - default: `table`
- `--auto-parameters`: Auto-configure search parameters - default: `false`
- `--topic`: Search category (`general`, `news`, `finance`) - default: `general`
- `--search-depth`: Search depth (`basic`, `advanced`) - default: `basic`
- `--chunks-per-source`: Chunks per source for advanced search (1-3) - default: `3`
- `--limit`: Maximum results (0-20) - default: `5`
- `--time-range`: Time range filter (`day`, `week`, `month`, `year`)
- `--start-date`: Start date filter (YYYY-MM-DD)
- `--end-date`: End date filter (YYYY-MM-DD)
- `--include-answer`: Include LLM-generated answer (`true`, `false`, `basic`, `advanced`) - default: `false`
- `--include-raw-content`: Include raw content (`true`, `false`, `markdown`, `text`) - default: `false`
- `--include-images`: Include image search results - default: `false`
- `--include-image-descriptions`: Include image descriptions - default: `false`
- `--include-favicon`: Include favicon URLs - default: `false`
- `--include-domains`: Comma-separated list of domains to include
- `--exclude-domains`: Comma-separated list of domains to exclude
- `--country`: Boost results from specific country
- `--include-credits`: Include credit usage information - default: `false`

## Output Formats

### Table Format (Default)

Displays results in a rich table with columns for Title, URL, Score, and Content. Includes answer panel and credit usage.

### JSON Format

Returns the complete API response as formatted JSON, perfect for programmatic use and AI agents.

### Tree Format

Displays results in a hierarchical tree structure, useful for exploring result relationships.

## API Coverage

This wrapper implements the complete Tavily Search API (`POST /search`) with all parameters:

- Query execution with customizable depth
- Topic-based searching (general, news, finance)
- Date and time range filtering
- Domain inclusion/exclusion
- Geographic boosting
- Content inclusion options (answers, raw content, images)
- Credit usage tracking

## Examples for AI Agents

### JSON Output for Parsing

```bash
tavilySearch "machine learning trends 2024" --format json --include-answer advanced
```

Returns structured JSON that can be easily parsed by AI systems.

### Table Output for Human Review

```bash
tavilySearch "quantum computing breakthroughs" --limit 15 --format table
```

Provides readable table format for human analysis.

### Tree Output for Hierarchical View

```bash
tavilySearch "renewable energy technologies" --format tree --include-raw-content markdown
```

Shows results in tree structure for better organization.

## Error Handling

The CLI provides clear error messages for:
- Missing API key
- Invalid parameters
- Network issues
- API rate limits
- Authentication failures

## Development

### Project Structure

```
tavilySearch/
├── main.py          # Main CLI application
├── pyproject.toml   # Project configuration
└── README.md        # This documentation
```

### Dependencies

- `typer`: Command-line interface framework
- `rich`: Rich text and beautiful formatting
- `httpx`: Modern HTTP client
- `pydantic`: Data validation and serialization

### Building

```bash
uv build
```

### Testing

```bash
uv run python -m pytest  # (if tests are added)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commit messages
4. Add/update tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Support

For issues related to:
- Tavily API: Visit [Tavily Documentation](https://docs.tavily.com/)
- This wrapper: Open an issue on GitHub

## Changelog

### v0.1.0
- Initial release with complete Tavily Search API coverage
- Support for JSON, table, and tree output formats
- Comprehensive CLI with all API parameters
- Rich interface for better user experience
- AI agent friendly design with type annotations and docstrings