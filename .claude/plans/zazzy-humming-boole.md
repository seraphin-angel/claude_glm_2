# Plan: Agent Teams 汎用ロール定義 & モデル割り当てルール

## Context

Agent Teams を使う際、リーダー（Opus）とチームメンバー（Sonnet/Haiku）でモデルを分けたい。
現状は `.claude/agents/` に特化型エージェント（planner, code-reviewer 等）のみ存在し、
全て `model: opus` が設定されている。

**目的**: アドホックなチーム作成時でも、毎回モデル指定を書かずに済む汎用ロール定義と、
チーム全体のモデル割り当てルールを整備する。

## 作成するファイル

### 1. `.claude/agents/team-worker.yml` → **新規作成**（`.md` 形式）

汎用実装ワーカー。チームで並列作業する際のデフォルトメンバー。

- **model: sonnet** — コスト効率と十分な実装能力のバランス
- tools: 全ツール（Read, Write, Edit, Bash, Grep, Glob）
- 用途: 実装、修正、テスト作成、リファクタリング等の作業全般

ファイルパス: `.claude/agents/team-worker.md`

### 2. `.claude/agents/team-researcher.md` → **新規作成**

軽量リサーチエージェント。コード調査・情報収集専用。

- **model: haiku** — 軽量タスクに最適、コスト最小
- tools: Read, Grep, Glob のみ（読み取り専用）
- 用途: ファイル探索、パターン調査、依存関係の確認

ファイルパス: `.claude/agents/team-researcher.md`

### 3. `.claude/agents/team-reviewer.md` → **新規作成**

コードレビュー担当。実装後の品質チェック。

- **model: sonnet** — レビューには十分な能力
- tools: Read, Grep, Glob, Bash（テスト実行用）
- 用途: コードレビュー、テスト実行、品質チェック

ファイルパス: `.claude/agents/team-reviewer.md`

### 4. `.claude/rules/agent-teams.md` → **新規作成**

Agent Teams 作成時のモデル割り当てルールを定義。
CLAUDE.md ではなくルールファイルとして配置（既存の `rules/` パターンに合わせる）。

内容:
- リーダー = Opus（メインセッション）
- 実装ワーカー = Sonnet（team-worker）
- リサーチャー = Haiku（team-researcher）
- レビュワー = Sonnet（team-reviewer）
- `model` パラメータ省略禁止のルール

## 既存ファイルへの影響

- **変更なし**: 既存の特化型エージェント（planner, code-reviewer 等）はそのまま維持
- **変更なし**: `.claude/rules/agents.md` — 既存のエージェント一覧はそのまま。新ルールは別ファイルで追加

## フォーマット

既存エージェントのフォーマットに準拠:
```
---
name: team-worker
description: ...
tools: [...]
model: sonnet
---

（プロンプト本文）
```

## 検証方法

1. Agent Teams を作成する際に `subagent_type: "team-worker"` で spawn し、Sonnet が使われることを確認
2. `subagent_type: "team-researcher"` で spawn し、Haiku が使われることを確認
3. `.claude/rules/agent-teams.md` のルールが会話コンテキストに読み込まれることを確認
