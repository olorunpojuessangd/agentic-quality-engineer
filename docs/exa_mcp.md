# Connecting Exa MCP to AI Agents

Exa provides a hosted Model Context Protocol (MCP) server at:
```
https://mcp.exa.ai/mcp
```
This enables LLMs and agents (in Claude Code, Cursor, VS Code, or Antigravity) to call Exa search and contents tools natively over Server-Sent Events (SSE).

---

## 1. Exa MCP Tools

When connected, Exa provides agents with the following tools:
* **`search` / `web_search_exa`**: Semantic web search designed for AI queries. Supports neural search, date filters, domain inclusion/exclusion, and category filtering (`research paper`, `company`, `news`, `pdf`).
* **`get_contents` / `get_contents_exa`**: Clean markdown or text extraction from search URLs, including highlights and summaries.

---

## 2. Configuration Across Agent Frameworks

### A. Claude Code / Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "env": {
        "EXA_API_KEY": "YOUR_EXA_API_KEY"
      }
    }
  }
}
```
Or using Exa's hosted HTTP SSE endpoint in compatible clients:
```json
{
  "mcpServers": {
    "exa-hosted": {
      "url": "https://mcp.exa.ai/mcp?apiKey=YOUR_EXA_API_KEY"
    }
  }
}
```

### B. Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "exa": {
      "url": "https://mcp.exa.ai/mcp?apiKey=YOUR_EXA_API_KEY"
    }
  }
}
```

---

## 3. How Exa MCP Enhances the Agentic Quality Engineer

In our custom pipeline:
* **Current Direct RAG**: [`pipeline/exa_retriever.py`](file:///Users/d.essang/Desktop/MVP%20Projects/agentic-quality-engineer/pipeline/exa_retriever.py) calls Exa's Python SDK / REST endpoints directly to fetch domain standards (`ISO 3685`, `ISO 230-3`, `ASME Y14.5`).
* **MCP Agent Mode**: When using tool-calling agents, the Analyst agent is equipped with Exa's MCP tools to dynamically discover new technical bulletins, manufacturer cutting data (e.g. Sandvik Coromant, Kennametal), and machine tool service alerts without hardcoded retrieval paths.
