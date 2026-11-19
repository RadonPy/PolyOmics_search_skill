# 開発とテスト

Python 3.12で、リポジトリのルートから実行します。

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/package_releases.py
python scripts/validate_package.py
python scripts/check_live_mcp.py --smarts
```

ライブ試験の出力フォルダーは事前に作成します。サービスの待機やネットワークによっては実行に時間がかかります。結果にはスキーマのハッシュ、集計数とリビジョンのみを保存し、レコードは保存しません。CIでは手動実行時にのみライブ試験を選べます。

`plugin.schema.json` と `mcp.schema.json` を [Agent Plugins 1.0.0の公式配布元](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json)（[MCP用スキーマ](https://agent-plugins.org/schemas/1.0.0/mcp.schema.json)）から `.cache/schemas/` に保存し、`python scripts/validate_package.py --schema-dir .cache/schemas` で公式スキーマも検査してください。`.github/workflows/validate.yml` は同じ検査とアーカイブの差分検査を実行します。

`tests/fixtures/` は v1.2 引き継ぎの合成データとJSON Schemaです。対象は互換性ゲート、モデル役割と統計の取り違え、ZIPの同一性・構成です。ChatGPTの生成応答や、まだ公開されていないevidenceサーバーのE2Eを模した実測値ではありません。プロンプトの動作確認は[評価ケース](evaluation-cases.md)に従います。
