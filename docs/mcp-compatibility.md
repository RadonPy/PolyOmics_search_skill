# MCP compatibility

The production endpoint is `https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/`. It accepts anonymous Streamable HTTP. The CLI verified eight tools and recorded the protocol, schema hashes, and advertised annotations. [Live MCP receipt](live-mcp-web-compatibility.json)

| MD tool | Input shape |
|---|---|
| `get_dataset_info` | No arguments |
| `list_search_fields` | Optional category: `property`, `class`, `all` |
| `search_polymers` | `request` with published property, class, structure, text and quality filters, fields, sort, limit, cursor and count options |
| `get_polymer` | `uuid` with optional `fields` and `config` |
| `aggregate_polymers` | `request` with shared search filters, properties and optional statistics, grouping and quantiles |

Responses use an `ok` JSON envelope. The live check covers snapshot consistency, a bounded class/property search, ranking, detail, aggregation and invalid input. SMARTS matches the finite graph in `search_smiles`. Read units and field names from the live schema and field catalog. The [2026-11-19 baseline](live-mcp.json) describes the five MD tools before Evidence was released.

The [Evidence 1.5.0 contract](evidence-contract-v1.5.md) covers `get_sim2real_catalog`, `search_sim2real_evidence`, and `get_sim2real_evidence`. Distinguish missing tools, an empty released catalog, an incompatible contract, and an outage. The [v1.4.0 live receipt](live-mcp-v1.5.json) remains historical. Source MD, evidence storage, and release revisions are distinct.

The operations read a bounded public dataset. MCP tool annotations come from the server. The live report records missing flags as null. [Public submission requirements](public-submission.md)
