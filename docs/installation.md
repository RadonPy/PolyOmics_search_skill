# インストール

## 統合プラグイン

`dist/polyomics-search-plugin.zip` を、Agent Plugins形式に対応するホストに取り込んでください。ChatGPT/Codexでは管理者がMCP付きプラグインの作成を許可している環境で非公開登録し、登録したプラグインを開いてインストールします。MCPは公開HTTPSのStreamable HTTPで、認証は不要です。

接続先: `https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/`

インストール後、新しいChatGPT Workチャットで `@PolyOmics Search` を選び、データのリビジョンを尋ねます。実際のツール実行に続き、[評価ケース](evaluation-cases.md)の検索とevidence未公開時の応答を確認します。[公式の取り込み手順](https://developers.openai.com/plugins/build/plugins)と[Workでのテスト](https://developers.openai.com/plugins/quickstart)を参照してください。

MCPそのものの接続テストだけをする場合は、ChatGPTの **Plugins → ＋ → Add custom MCP server** から上記URLと **No authentication** を選べます。この操作だけでは同梱Skillはインストールされません。既に作成したプラグインにクライアント固有のMCP登録が必要なら、そのホストで登録してください。登録情報をソースに書き込む必要はありません。

## CodexでスタンドアロンSkillを使用

1. `dist/skill.zip` を展開し、`polyomics-search` フォルダーをプロジェクトの `.agents/skills/` に配置します。
2. 許可されたローカルCodex環境で `codex mcp add polyomics --url https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/` を実行します。既に同じ接続があるなら登録済みのものを使います。
3. 新しいセッションで `$polyomics-search` を選び、READMEの検索例を使って検証します。

現ワークスペースでは非公開プラグイン作成時にMCP付きプラグインの利用が403で拒否されました。ChatGPTで試すには、ワークスペース管理者にこの権限の有効化を依頼し、その後に非公開登録とWorkでの検証を行ってください。
