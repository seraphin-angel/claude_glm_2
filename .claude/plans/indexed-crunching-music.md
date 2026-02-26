# Plan: `ask-in-detail` スキルの作成

## Context

プランモード等でClaude Codeが「これで進めていいですか？」と確認してくるとき、ユーザーが「Ask me in detail」「詳しく聞いて」等と入力したら、Claudeが AskUserQuestion ツールを使って不明点・曖昧な点を深掘りして質問してくれるスキルを作成する。

現状、プランモードの確認ステップでは「承認 / 却下 / 自由入力」の選択肢しかなく、Claudeが自発的に質問を掘り下げる仕組みがない。このスキルにより、実装前に要件の抜け漏れを防ぐ「最後の砦」となる。

## Approach

### ファイル構成

```
/workspace/.claude/skills/ask-in-detail/
└── SKILL.md    ← 新規作成（1ファイルのみ）
```

> ユーザー選択: プロジェクト内に配置し、リポジトリにコミット可能にする

### SKILL.md の設計

**フロントマター:**
- `name: ask-in-detail`
- `description:` トリガーフレーズを含む（日英両方）

**本文構成:**
1. **When to Use** — スキル発動条件
2. **The Process** — 5ステップの質問生成フロー
   - Step 1: コンテキスト分析（会話履歴を読み直す）
   - Step 2: SPACEフレームワークで質問生成
     - **S**cope（スコープ）
     - **P**erformance（パフォーマンス・スケール）
     - **A**ssumptions（前提・代替案）
     - **C**orner cases（エッジケース・エラー処理）
     - **E**xperience（ユーザー体験・完了条件）
   - Step 3: フィルタリング（4-8問に厳選）
   - Step 4: 質問を提示（具体的・理由付き・デフォルト提案）
   - Step 5: 回答をプランに反映
3. **Quality Signals** — 良い質問 vs 悪い質問の具体例
4. **Communication Note** — 日本語でのコミュニケーション指示

### 設計上の重要ポイント

- **SPACEフレームワーク**: 固定チェックリストではなく「思考の枠組み」を提供。コンテキストに応じた質問を生成できる
- **フィルタリングステップ**: 15個のジェネリックな質問ではなく、4-8問の高価値な質問に絞る
- **Good/Bad例の対比**: 抽象的なルールより具体例で品質基準を教える
- **デフォルト値の提案**: 「最大ファイルサイズは？10MBをデフォルトにしますが確認です」のように、回答しやすくする

### トリガーフレーズ（descriptionに含める）

- `/ask-in-detail`（明示的呼び出し）
- "Ask me in detail", "ask me questions first", "clarify before proceeding"
- "詳しく聞いて", "もっと質問して", "質問してから進めて"

## Implementation

### Step 1: ディレクトリ作成
```bash
mkdir -p /workspace/.claude/skills/ask-in-detail
```

### Step 2: SKILL.md 作成

`/workspace/.claude/skills/ask-in-detail/SKILL.md` に以下の内容を書き込む:

- フロントマター（name + description with trigger phrases）
- 約90行のMarkdown本文（SPACEフレームワーク、フィルタリングルール、Good/Bad例）
- 日本語コミュニケーション指示
- 質問形式: **一括提示**（4-8問をまとめて提示し、ユーザーがまとめて回答可能）

完全な内容は Plan agent の設計結果に基づく（conversation context 参照）。

## Verification

1. `cat ~/.claude/skills/ask-in-detail/SKILL.md` でファイルの存在と内容を確認
2. Claude Code の新しいセッションで `/ask-in-detail` と入力し、スキルが認識されるか確認
3. プランモードで「詳しく聞いて」と入力し、AskUserQuestion による深掘り質問が生成されるか確認

## Files to Create/Modify

| File | Action |
|------|--------|
| `/workspace/.claude/skills/ask-in-detail/SKILL.md` | **新規作成** |
