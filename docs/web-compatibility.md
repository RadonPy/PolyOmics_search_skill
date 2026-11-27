# ChatGPT Web workspace setup

The workspace ZIP bundles the PolyOmics Search Skill and a required reference to a registered PolyOmics cloud app. The existing remote MCP server supplies all live results. A workspace owner or authorized developer can build the package on a development machine. Once the full plugin is installed, its Web workflows use the cloud app without Python, a local server, or filesystem access.

## Register or find the cloud app

1. Open ChatGPT in a browser and select the intended workspace. Open **Plugins** and look for the separately registered **PolyOmics MCP** connection. An existing **PolyOmics Search** entry installed from a ZIP identifies the plugin. The app identifier belongs to the separate MCP connection.
2. If the connection is missing and you are authorized to register it, choose **Plugins → + → Add custom MCP server**. Enter **PolyOmics MCP**, the description **Search PolyOmics, a large-scale computational polymer property database with published aggregate Sim2Real evidence**, and the server URL `https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/`. Choose **No authentication**. Verify the disclosed permissions and confirm that the server exposes the eight tools described in the [MCP contract](mcp-compatibility.md). Refresh its tools if the workspace has a stale snapshot.
3. Select **Create as a plugin** to register a new connection, or open the details page for an existing one. Look in the browser address bar for `plugin_asdk_app_…`. The workspace binding takes its `asdk_app_…` portion. If the connection or its details are hidden, the workspace owner or an authorized developer can verify its registration and availability. The workspace route targets eligible Business, Enterprise, and Edu accounts.
4. In a fresh Web chat with just the registered app, ask for the PolyOmics dataset revision. Check the tool call and confirm that the app is available to the intended role. This isolates the connection before testing the full Skill. Changes to access or publication require the workspace owner's approval.

See the [custom MCP connection flow](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt), [browser URL instructions](https://developers.openai.com/plugins/build/plugins#create-and-test-a-plugin-locally-with-an-mcp-server), and [registered app guidance](https://learn.chatgpt.com/docs/enterprise/plugin-management#reference-an-existing-app-with-appjson).

## Build, upload, and install the workspace ZIP

Set the actual app ID in the local environment as `POLYOMICS_WORKSPACE_APP_ID`, or supply it with `--workspace-app-id`. The generator checks the shape of the ID and rejects placeholders. The workspace administrator verifies ownership and access separately. Keep the ID and generated archive private. Use the repository's [development prerequisites](developer-testing.md).

```sh
python scripts/package_releases.py --profile workspace
python scripts/validate_package.py --profile workspace
python scripts/check_english_text.py --archive .local/dist/polyomics-search-web-plugin.zip
```

The output is `.local/dist/polyomics-search-web-plugin.zip`. Its portable root manifest refers to `./.app.json`. That file has one required binding, `apps.polyomics`. The workspace profile omits the bundled MCP declaration and the Skill's direct-connection metadata. It uses the same scientific instructions and icon as the portable profile.

In the target workspace's **Admin console → Plugins**, use **Add → Upload plugin**, or **Upload new version** for an existing manually uploaded listing when the workspace permits it. For a GitHub-managed listing, update the owning marketplace source to a private workspace profile and sync it. Importing the public repository root would select the portable plugin. Preserve the existing listing and sharing where supported. If the importer cannot convert the listing, coordinate a private replacement with the owner before retiring it. An installed plugin and its required app each need to be available to the intended user. [Workspace plugin management](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) · [GitHub import and sync](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github)

After uploading v1.6.0, open the existing **PolyOmics Search** listing in **Plugins**. Verify version `1.6.0`, the 30-character subtitle **Polymer property database (MD)**, and the full description, which begins “Search PolyOmics, a large-scale computational polymer property database.” Record the visible metadata with the host and mode. If the host still displays stale copy after refreshing, verify its installed version and update source or use the supported listing edit with owner approval. The **PolyOmics MCP** cloud app has its own listing. A GitHub merge updates the source repository. An installed or published release still needs its supported update flow. [Manifest](../plugin.json)

For a connection diagnostic or tools-only access, use **Add custom MCP server** and attach the registered app directly. The full scientific workflow instructions are provided by the separate PolyOmics Search Skill.

## Web acceptance

Open a fresh **Work** chat on the web and select the full PolyOmics Search plugin. Repeat in ordinary **Chat** separately if the account and plugin offer it. Record the package version, mode, app access, observed calls, and whether each response used the shared Skill's interpretation rules. Redact workspace identifiers, user identifiers, and response payloads. If an eligible second workspace member is available, verify their install and tool access separately.

| Case | Action or prompt | Verify |
|---|---|---|
| W1 | Open the full plugin listing on Web and install it. | The required app is available and the listing has no Desktop only label. |
| W2 | Use PolyOmics Search to report the dataset revision and available property fields. | Visible live MCP schema or source calls with current provenance and no local execution. |
| W3 | Find three PolyOmics polyimides with density at least 1.3 g/cm3, sorted by simulated thermal conductivity. Include units and citations. | A bounded search uses live property names and units. Report an empty result explicitly if applicable. |
| W4 | What is the Direct Sim2Real Evidence for density? Explain the slope, intercept, sample count, and uncertainty. | Live catalog, search, and detail calls support coefficients, units, applicability, and any published uncertainty. A descriptive fit provides no independent calibration claim. |
| W5 | Find Indirect Evidence linking a simulated source property to an experimental target, and explain the source model's member and independent validation. | Show the correct axes and distinguish member diagnostics, independent validation, and missing links. |
| W6 | Ask a comparable question in Japanese. | The same cloud tools run and the reply is in Japanese. Record the outcome in English. |
| W7 | Ask for a missing Evidence record, an invalid alias, or private experimental rows. | Clearly report an error, absence, or data boundary. Use approved aggregate alternatives where relevant. |
| W8 | Use an approved isolated account without access to the registered app. | The full plugin explains missing live access. If a temporary access change was authorized, restore it afterwards. |
| W9 | Find polymers that could provide high experimental thermal conductivity for an insulating film. | Evidence is retrieved without naming PolyOmics. Verify public MD candidates, thermal and electrical constraints, applicable estimates or meaningful fallbacks. |
| W10 | Estimate experimental density for a public candidate with its published Direct fit. | Use current detail and candidate X. Compute and label an exploratory point estimate when eligible. Report any unknown definitions or conditions that block applicability. |
| W11 | Find candidates for low water uptake, then try using observed MD in place of an Indirect Source prediction. | Show a qualified signed proxy or hypothesis. An incompatible observed MD value yields no numerical experimental estimate. |
| W12 | Only report the highest simulated Tg. | Use the MD search and units, honor applicable reliability rules and keep the output narrow. |
| W13 | Screen for two experimental targets when evidence for one is absent. | Evaluate each target separately and surface the unresolved constraint. |
| D1 | Run W9–W12 on the updated portable package in Desktop or Codex. | The host uses the portable connection and the same scientific workflow. |

Current v1.6.0 status is `WEB_E2E_NOT_VERIFIED` and `PLUGIN_METADATA_UI_NOT_VERIFIED`. The private workspace ZIP was built and validated with the supplied app ID. The available browser was signed out and the workspace lookup could not confirm a corresponding active connection in this session. A v1.6.0 interactive portable test is also pending. [Implementation results](implementation-report.md)
