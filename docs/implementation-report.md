# 実装と検証結果

## v1.4.0 — 2026-11-26 JST

- `skills/polyomics-search/` の指示、参照文書、`check_evidence.py` を更新しました。Direct/Indirectの公開回帰を軸・手法・尺度・件数で検証し、fitted R²、未補正parity R²、Source MD評価を区別します。member診断と独立評価のリンク・数値可用性も別々に判定します。
- `scripts/check_live_mcp.py` とCIにstrict検証を追加しました。`python scripts/check_live_mcp.py --smarts --evidence require --output docs/live-mcp-v1.5.json` は15:20 JSTに成功。匿名で8ツールを20回呼び出し、MD 5ツールの入力スキーマは旧基準と一致しました。公開release `public:sim2real-v1.5:a42a5f0eccfbea1e8f0d3f7b` ではmember診断を確認し、独立評価は未提供でした。独立評価がある場合と欠損回帰の分岐は合成テストで確認しました。
- `python -m pytest -q tests` は122件成功、失敗・skipなし。`python scripts/package_releases.py` を2回実行してSHA-256の一致を確認し、`python scripts/validate_package.py --schema-dir .cache/agent-plugins` とSkill validatorも通過しました。
- `dist/skill.zip`: `f3abbc1cfe2b417c99fe51192ce9ac83094b55d76e70ea1a1e847c5e9296bee0`。`dist/polyomics-search-plugin.zip`: `691d5242dbdc71aac581c7a4cec0ef0018d9fafea712d70cbe645af7d32813a2`。既存のアイコンと接続先に変更はありません。
- ChatGPTへのインストールと回答の検証、GitHub Actionsのリモート実行は未実施です。MCP、Dataset、Explorerは変更していません。

実測フィールドは[契約対応表](evidence-contract-v1.5.md)、検査ごとの結果は[実行ログ](live-mcp-v1.5.json)を参照してください。

## v1.3.1実装時の記録（2026-11-19）

v1.3.1はソースMD検証のリンクと数値性能の判定、Catalog指標の検出、プラグイン画像を更新するローカルパッチです。MCPの検索契約とSim2Real v1.2の科学的定義は維持しています。合成データ・ZIPのオフラインテスト、公式Agent Plugins 1.0.0スキーマ、Skill検証を実施しました。以下の公開MCPおよびChatGPTの記録はv1.2.0時点のもので、v1.3.1でのインストールやライブEvidence検証は実施していません。

## v1.2.0実装時の記録

Skill / Plugin `polyomics-search` 1.2.0。既存のRadonPy BSD 3-Clauseライセンスを保持し、Skill、Agent Plugins 1.0.0マニフェスト、MCP設定、文書、CIワークフロー、再現可能な配布ZIPを追加しました。Sim2Realはクライアントの解釈を先行実装しました。

| 範囲 | 結果 |
|---|---|
| `python -m pytest -q` | PASS：29件。v1.2合成フィクスチャ、役割・版・構造の検査、旧Indirect Evidence拒否、再現可能なZIP |
| Skill validator / Agent Plugins 1.0.0公式JSON Schema / ZIP内容 | PASS |
| `python scripts/check_live_mcp.py --smarts` | PASS：匿名アクセス、5ツール、UUID詳細と集計の照合、入力エラー。ポリイミド＋密度条件に1,265件、SMARTS追加時に1,195件 |
| Sim2Real本番E2E | NOT RUN：現行MCPにEvidence 3ツールが未提供 |
| ChatGPT上のプラグイン検証 | BLOCKED：非公開登録の試行はHTTP 403。ワークスペースでMCP付きプラグインの利用権限が必要 |
| GitHub Actions | NOT RUN：ローカル検証とリモートCIは別 |

GitHub `main` は公開アクセスで `30871c2eba6ca21165d165f0fa539aed1d9087ab`（ライセンスのみ）を取得済みです。実装はローカルの `codex/polyomics-search-v1-2` にコミットしました。書き込み資格情報を取得できず、pushとPR作成は未完了です。対象リポジトリへの書き込み権限があるアカウントで `git credential-manager github login` を実行してから、`git push -u origin codex/polyomics-search-v1-2` でブランチを公開し、`main` に向けたPRを作成してください。

実行記録は [live-mcp.json](live-mcp.json)、再現手順は[開発とテスト](developer-testing.md)。実物のPoLyInfoレコード、個別予測、モデル重み、秘密情報、個人固有のプラグイン登録情報は配布対象に含みません。
