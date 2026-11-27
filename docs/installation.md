# Installation

## ChatGPT Web in a workspace

Use the [workspace Web setup](web-compatibility.md): register or verify the remote cloud app, obtain its actual app ID, build the separate workspace ZIP, and install and test the full plugin in a fresh Web Work chat. An app reference does not confer access. If the listing says **Desktop only**, it cannot run on Web. Consult [OpenAI workspace import guidance](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github).

To test the MCP tools directly, open **Plugins → + → Add custom MCP server** and connect `https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/` with **No authentication**. The full PolyOmics Search workflows require the Skill in the workspace package. See the [official connection flow](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

## Portable plugin

Import [polyomics-search-plugin.zip](../dist/polyomics-search-plugin.zip) into a compatible desktop or portable host. It contains the shared Skill and a single anonymous HTTPS Streamable HTTP connection. For external distribution, use this ZIP as the [public submission candidate](public-submission.md) in the **With MCP** route.

To update an existing installation, open **PolyOmics Search** in the host's plugin manager and use its **Upload new version** or source update flow for the existing entry. For a local source, replace the package in its existing directory and refresh the host. Verify version `1.6.0`, subtitle **Polymer property database (MD)** and the full description in the details page before running a representative fresh-chat evaluation. [Package manifest](../plugin.json) · [Evaluation cases](evaluation-cases.md)

## Standalone Skill in Codex

1. Extract [skill.zip](../dist/skill.zip) and place its `polyomics-search` folder under the project's `.agents/skills/`.
2. Reuse an existing PolyOmics connection or run `codex mcp add polyomics --url https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/` in an authorized Codex environment.
3. Select `$polyomics-search` in a fresh session and run a query from the [evaluation cases](evaluation-cases.md).
