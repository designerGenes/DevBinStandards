# Kagi Search CLI

A command-line interface for the Kagi Search API.

## Features

- **Search**: Perform web searches using Kagi's index.
- **FastGPT**: Answer queries using Kagi's FastGPT.
- **Summarizer**: Summarize content from URLs or text.
- **Enrichment**: Get enriched content for web and news.

## Installation

```bash
uv pip install .
```

## Usage

Set your API key:
```bash
export KAGI_API_KEY="your_api_key"
```

Search:
```bash
kagi search "machine learning"
```

FastGPT:
```bash
kagi fastgpt "Explain quantum computing"
```

Summarize:
```bash
kagi summarize --url "https://example.com/article"
```
