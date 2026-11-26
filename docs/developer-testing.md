# Development and testing

Run from the repository root with Python 3.12:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/package_releases.py
python scripts/validate_package.py
python scripts/check_english_text.py
python scripts/check_live_mcp.py --smarts --evidence require --output .cache/live-mcp.json
```

Create the output directory before writing a live report. Strict mode requires usable Direct, Indirect, and member examples and checks the five MD input schemas against the baseline. `--evidence auto` can verify MD alone if the evidence tools are absent. A partial Evidence deployment fails. `--evidence off` runs MD checks only. Live reports keep schema hashes, tool annotation flags, release metadata, counts, and public Evidence IDs.

Download the two official schemas to `.cache/schemas/`. Run `python scripts/validate_package.py --schema-dir .cache/schemas` to validate the package. CI checks that the tracked ZIPs reproduce and tests a workspace binding with a synthetic ID in a temporary directory. The workflow's manual live run uses strict mode. [Plugin schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json) · [MCP schema](https://agent-plugins.org/schemas/1.0.0/mcp.schema.json)

The English checker scans repository-authored UTF-8 text, decoded JSON/YAML strings, archive text, and relative Markdown file links. It detects Japanese-script characters and permits scientific symbols such as R², µm, and °C. Review English prose manually as well. To check a generated private ZIP, add `--archive .local/dist/polyomics-search-web-plugin.zip`.

Synthetic fixtures cover Evidence v1.2 and v1.5. Use the separate browser checklist for Web acceptance. [Web acceptance](web-compatibility.md#web-acceptance) · [Evaluation cases](evaluation-cases.md)
