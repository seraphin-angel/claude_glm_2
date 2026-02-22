# Plan: sequential-leader エージェント定義ファイルの作成

## Context
`/workspace/agent-team-sequential-pattern.md` の「選択肢C」で定義した逐次サブエージェント使い捨てパターンのリーダーエージェントを、実際に `.claude/agents/` に配置する。既存エージェント定義のフォーマット（YAML フロントマター + マークダウン本文）に合わせて作成する。

## 作成ファイル

**パス**: `.claude/agents/sequential-leader.md`

**YAML フロントマター**:
- `name`: sequential-leader
- `description`: 逐次タスク実行リーダー。タスクごとにサブエージェントを新規起動し、完了後に終了させる使い捨てパターンで大規模なアプリ構築を管理する。
- `tools`: Read, Grep, Glob, Task, SendMessage, TaskCreate, TaskUpdate, TaskList, TaskGet, TeamCreate, Bash
  - コード編集ツール（Edit, Write）は含めない（リーダーはコードを書かない）
  - Read/Grep/Glob は成果物確認・調査用
  - Bash はビルド確認・テスト実行用
- `model`: opus（オーケストレーションに深い推論が必要）

**本文**: `/workspace/agent-team-sequential-pattern.md` の選択肢Cの内容をベースに、既存エージェント定義のトーン・構造に合わせて整形する。

## Verification
- `.claude/agents/sequential-leader.md` が作成されること
- 既存エージェント定義（planner.md 等）と同じフロントマター形式であること
