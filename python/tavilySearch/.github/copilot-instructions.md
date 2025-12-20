## Project Description

This project will create a local wrapper around the entire Tavily AI Search API.
The documentation for the Taily AI Search API can be found here: https://tavily.com/docs/api-reference/search/introduction and https://docs.tavily.com/welcome.

We will use "uv" for managing dependencies and building the project.
The project will be written entirely in Python
We will use Typer and Rich for the CLI interface.

Our goal is to make this application entirely accessible to AI agents, so we will focus on clear and simple code structure, comprehensive docstrings, and type annotations throughout the codebase.

we will load

basic calls to this app from the Terminal CLI will look like:

tavilySearch "search phrase/term" 

or 

tavilySearch "search phrase/term" --limit 15 --filters '{"key":"value"}'

We should be able to intensely customize the output format, including options for JSON, table, and tree formats.  Once again, the goal is machine-readability and accessibility for AI agents.

I will know this script is complete when it has colorful, detailed documentation and the user can implement all the features of the Tavily AI Search API through this local wrapper.