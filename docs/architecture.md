# Architecture

One remotely hosted PolyOmics MCP serves all live operations. The Skill discovers the tools provided by its host and interprets public results. It does not store scientific records or run a model locally.

The standalone and portable profiles preserve the remote MCP dependency in the Skill metadata. The portable plugin ships Agent Plugins 1.0.0 `plugin.json` and `mcp.json`. The workspace profile uses the same Skill text and icons, keeps the Skill's presentation metadata, and binds to one existing cloud app through `.app.json`. Workspace app access is managed separately.

MD searches and evidence interpretation are separate workflows. The evidence workflow checks catalog definitions, provenance, and release before requesting bounded results. The Web chat follows the Skill's instructions. Developers can also run the Python helper for local validation.

Packaging uses explicit allowlists. Synthetic fixtures, developer tooling, raw data, and caches are not included. Workspace-specific bindings and ZIPs are generated locally and are not public repository assets.
