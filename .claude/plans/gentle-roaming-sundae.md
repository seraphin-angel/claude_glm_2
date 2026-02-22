# Context7 MCP API キー設定

## Context
Context7 MCP サーバーのクォータ制限に当たっているため、API キーを設定してレート制限を緩和する。

## 変更内容

### 対象ファイル
- `/workspace/.claude/settings.local.json`

### 変更箇所
`env` セクションに `CONTEXT7_API_KEY` を追加する:

```json
{
  "env": {
    "IS_DEMO": "true",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CONTEXT7_API_KEY": "<ユーザーが指定するAPIキー>"
  },
  ...
}
```

## 手順
1. ユーザーから API キー（`ctx7sk-` プレフィックス）を受け取る
2. `settings.local.json` の `env` に `CONTEXT7_API_KEY` を追加
3. Claude Code を再起動して変数が反映されることを確認

## 注意点
- API キーは [context7.com/dashboard](https://context7.com) で取得
- プラグインが環境変数を読み取れない場合は、方法2（MCP 直接登録）にフォールバック

## 検証方法
- `resolve-library-id` や `query-docs` を呼び出してクォータエラーが出ないことを確認
