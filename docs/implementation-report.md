# 実装と検証結果（2026-11-19）

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
