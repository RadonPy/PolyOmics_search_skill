# 開発とテスト

Python 3.12で、リポジトリのルートから実行します。

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/package_releases.py
python scripts/validate_package.py
python scripts/check_live_mcp.py --smarts --evidence require --output docs/live-mcp-v1.5.json
```

`--evidence auto` は既定で、Evidenceツールがない場合はMDのみ、全種類が空ならAPI呼び出しだけの確認が可能です。部分公開は失敗です。`require` はDirect、Indirect、memberの実例まで検査し、未公開・空・契約不一致・通信失敗は非zeroで終了します。`off` はMD専用です。結果にはスキーマハッシュ、件数、リビジョン、検査結果、公開Evidence IDだけを保存し、元レコードは保存しません。CIでは手動 `live_mcp` のときだけstrict検証を実行します。

`plugin.schema.json` と `mcp.schema.json` を [Agent Plugins 1.0.0の公式配布元](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json)（[MCP用スキーマ](https://agent-plugins.org/schemas/1.0.0/mcp.schema.json)）から `.cache/schemas/` に保存し、`python scripts/validate_package.py --schema-dir .cache/schemas` で公式スキーマも検査してください。`.github/workflows/validate.yml` は同じ検査とアーカイブの差分検査を実行します。

`tests/fixtures/` は旧v1.2とv1.5の合成データです。オフライン試験は回帰、member/独立評価、ライブチェッカーの失敗分岐、ZIP再現性を検査します。ChatGPTでの生成応答は別途[評価ケース](evaluation-cases.md)に従います。
