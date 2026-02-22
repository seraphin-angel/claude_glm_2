# 桃太郎戦略シミュレーション - 鬼ヶ島遠征

## コンテキスト

日本の昔話「桃太郎」をテーマにした**戦略シミュレーションゲーム**を開発します。従来のターン制バトルRPGではなく、リソース管理、ルート選択、リスク評価などの戦略的決断が鍵となるゲーム設計です。

プレイヤーは桃太郎となり、さる・いぬ・きじの仲間を募集し、きびだんごを管理しながら鬼ヶ島への道のりを戦略的に進みます。

## ゲームデザイン

### コアゲームループ

```
開始 → きびだんご集め → 仲間募集 → ルート計画 →
ノード移動 → イベント発生 → 戦略的決断 →
リソース管理 → 鬼ヶ島到達 → 最終ボス → 勝利/敗北
```

### ゲームフェーズ

1. **準備フェーズ**（里の集落）
   - きびだんごリソースの収集
   - 仲間の募集（さる・いぬ・きじ）
   - ルートオプションの検討
   - リソースの配分

2. **旅フェーズ**（マップナビゲーション）
   - ノード間のルート選択
   - ランダムイベントと遭遇
   - 各ステップでの戦略的決断
   - リソースの消費/獲得

3. **対決フェーズ**（鬼ヶ島）
   - 最終戦略バトル
   - 仲間のシナジー活用
   - リソース管理で結果が決まる

## コアメカニクス

### 1. きびだんごリソースシステム

```typescript
interface KibiDango {
  amount: number              // 現在の量
  maxAmount: number           // 最大所持可能量
  uses: {
    recruitCompanion: number  // 仲間募集コスト
    heal: number              // パーティHP回復
    bribeDemon: number        // 戦闘回避（賄賂）
    negotiate: number         // 特別ルート解放
    rest: number              // スタミナ回復
  }
}
```

### 2. ルート/パスシステム

- **山道**: 高リスク・高報酬（鬼ヶ島への近道）
- **川ルート**: 中リスク（きじの偵察で有利）
- **森の小道**: 低リスク・長距離・資源豊富
- **村の道**: 安全・きびだんご取引可能
- **隠しパス**: 特定の仲間組み合わせが必要

### 3. 仲間の能力（戦略的、非戦闘）

| 仲間 | 受動能力 | 能動能力 | シナジー |
|------|----------|----------|----------|
| **桃太郎** | 桃の加護：きびだんご+1獲得 | 激励：全体スタミナ回復 | チームシナジー：全能力+25% |
| **さる** | 木登り：山・森近道アクセス | 資源探知：きびだんご1-3個発見 | 撹乱：50%で戦闘回避 |
| **いぬ** | 忠義の守り：ダメージ-1 | 危険察知：隣接ノードの危険度表示 | 群れの戦術：さるとでクールダウン-1 |
| **きじ** | 空中偵察：接続ノード可視化 | 伝令：今後のイベント情報取得 | 空中優位：桃太郎とで「翼の道」解放 |

### 4. イベントシステム

**イベント例：**
- **行商人**: きびだんご割引購入、情報収集
- **橋の鬼**: 直接戦闘 / 賄賂 / さるの撹乱 / 別ルート探索
- **嵐**: 突破（スタミナ消費） / 待機（時間消費） / きじの偵察で避難所発見
- **村祭り**: 参加してきびだんご獲得 / 休息して回復 / 情報収集

### 5. 鬼遭遇システム（戦略的、非ターン制）

1. **評価**: きじの偵察で鬼のタイプと弱点を確認
2. **戦略選択**: 仲間とリソースに基づいたアプローチを選択
3. **成功計算**: 仲間シナジー・準備・リソースに基づく計算
4. **解決**: 単一の解決（マルチターンバトルなし）
5. **結果**: 勝利/敗北がリソース、スタミナ、ルートオプションに影響

## 勝利/敗北条件

**勝利条件:**
- 鬼ヶ島で鬼の王を倒す（全仲間募集済み + きびだんゴ15個以上必要）

**敗北条件:**
- きびだんごが0になり回復手段なし
- 全仲間のスタミナ枯渇
- （オプション）ターン制限超過

## エージェントチーム構成

| エージェント | 役割 | 責任範囲 |
|-------------|------|----------|
| **桃太郎（リーダー）** | オーケストレーター | 全エージェント調整、ゲームフロー管理、タスク委任 |
| **きじ** | アーキテクト | システム設計、ファイル構造、型定義、コードレビュー |
| **さる** | UI実装エージェント | Reactコンポーネント開発、UI/UX、アニメーション |
| **いぬ** | テスト/QAエージェント | テスト実装（TDD）、品質保証、80%+カバレッジ |

## 技術スタック

| カテゴリ | 技術 | 理由 |
|---------|------|------|
| フロントエンド | Next.js 15, React 19 | 最新機能、App Router |
| 言語 | TypeScript 5.6+ | 型安全性、優れたDX |
| スタイリング | Tailwind CSS | 迅速なUI開発 |
| 状態管理 | Zustand | 軽量、イミュータブル |
| テスト | Vitest + Playwright | 高速単体テスト、信頼性の高いE2E |
| ビルド | Turbopack | 高速開発ビルド |

## ファイル構造

```
example/momotaro-strategy-sim/
├── src/
│   ├── app/
│   │   ├── layout.tsx                    # ルートレイアウト
│   │   ├── page.tsx                      # ランディング/開始画面
│   │   ├── game/
│   │   │   └── page.tsx                  # メインゲームページ
│   │   └── api/
│   │       └── game/
│   │           ├── route.ts              # ゲーム状態API
│   │           ├── actions/
│   │           │   ├── recruit/route.ts # 仲間募集
│   │           │   ├── travel/route.ts  # ノード移動
│   │           │   └── event/route.ts   # イベント処理
│   │           └── save/route.ts        # セーブ/ロード
│   │
│   ├── components/
│   │   ├── game/
│   │   │   ├── GameContainer.tsx         # メインゲームラッパー
│   │   │   ├── ResourcePanel.tsx        # きびだんご表示
│   │   │   ├── CompanionPanel.tsx       # パーティステータス
│   │   │   ├── RouteMap.tsx             # 視覚的ルート表示
│   │   │   ├── EventModal.tsx           # イベントポップアップ
│   │   │   ├── StrategyMenu.tsx         # 鬼遭遇戦略オプション
│   │   │   ├── NodeInfo.tsx             # 選択ノード詳細
│   │   │   └── JourneyLog.tsx           # ゲーム履歴
│   │   └── ui/
│   │       ├── Button.tsx, Card.tsx, ProgressBar.tsx, Modal.tsx, Tooltip.tsx
│   │
│   ├── hooks/
│   │   ├── useGameState.ts              # ゲーム状態管理
│   │   ├── useRouteNavigation.ts        # ルートロジック
│   │   ├── useEventHandling.ts          # イベント処理
│   │   ├── useDemonEncounter.ts         # 遭遇解決
│   │   └── useGamePersistence.ts        # セーブ/ロード
│   │
│   ├── lib/
│   │   ├── game/
│   │   │   ├── engine.ts                # コアゲームエンジン
│   │   │   ├── events.ts                # イベント定義
│   │   │   ├── routes.ts                # ルートマップ生成
│   │   │   ├── demons.ts                # 鬼の設定
│   │   │   └── companions.ts            # 仲間の能力
│   │   ├── mechanics/
│   │   │   ├── resources.ts             # きびだんごシステム
│   │   │   ├── encounters.ts            # 鬼遭遇ロジック
│   │   │   ├── synergies.ts             # 仲間の組み合わせ
│   │   │   └── probabilities.ts          # RNG with weights
│   │   └── utils/
│   │       ├── validation.ts, calculations.ts, constants.ts
│   │
│   ├── types/
│   │   ├── game.ts, companions.ts, routes.ts, events.ts, demons.ts
│   │
│   └── styles/globals.css
│
├── __tests__/
│   ├── unit/     # lib/, hooks/, utils/ のテスト
│   ├── integration/  # API, 完全フローのテスト
│   └── e2e/      # Playwright テスト
│
├── public/assets/     # 絵文字/SVGアイコン
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── vitest.config.ts
└── playwright.config.ts
```

## 実装フェーズ

### フェーズ1: プロジェクト基盤（きじ/アーキテクト）

**期間**: 1-2日

1. Next.js 15 + TypeScript プロジェクト初期化
2. Tailwind CSS 設定
3. Vitest と Playwright 設定
4. コア型定義作成:
   - `types/game.ts` - GameState, GamePhase
   - `types/companions.ts` - Companion, Ability, Synergy
   - `types/routes.ts` - RouteNode, RouteConnection
   - `types/events.ts` - GameEvent, EventChoice
   - `types/demons.ts` - Demon, EncounterStrategy
5. ゲーム定数作成（`lib/utils/constants.ts`）
6. ベースUIコンポーネント（Button, Card, Modal）

**成果物**: 動作するNext.jsプロジェクト、完全な型システム、ベースコンポーネントライブラリ、テストインフラ

### フェーズ2: コアメカニクス（TDDアプローチ）

**期間**: 3-4日

**タスク**（さるがテスト作成、いぬが実装）:

1. **きびだんごリソースシステム**
   - テスト作成 → `lib/mechanics/resources.ts` 実装
   - 獲得、消費、上限、バリデーション

2. **ルートマップシステム**
   - テスト作成 → `lib/game/routes.ts` 実装
   - ノード接続、経路探索、バリデーション

3. **イベントシステム**
   - テスト作成 → `lib/game/events.ts` 実装
   - イベント選択、選択肢処理、結果

4. **仲間の能力**
   - テスト作成 → `lib/game/companions.ts` 実装
   - 受動効果、能動能力、シナジー

5. **鬼遭遇システム**
   - テスト作成 → `lib/mechanics/encounters.ts` 実装
   - 戦略選択、成功計算

**成果物**: 全コアメカニクス実装、80%+テストカバレッジ、包括的単体テスト

### フェーズ3: ゲームエンジン

**期間**: 2-3日

1. `lib/game/engine.ts` 実装:
   - ゲーム状態管理
   - ターン処理
   - 勝利/敗北判定
   - イベントキュー処理

2. カスタムフック実装:
   - `useGameState.ts` - 状態管理フック
   - `useRouteNavigation.ts` - ルート選択ロジック
   - `useEventHandling.ts` - イベント処理
   - `useDemonEncounter.ts` - 遭遇解決

3. ゲームデータ作成:
   - ルートマップ（10-15ノード）
   - 20+イベント
   - 5種類の鬼
   - 仲間能力定義

**成果物**: 完全なゲームエンジン、動作するゲームループ、全ゲームコンテンツ

### フェーズ4: UIコンポーネント（さる）

**期間**: 3-4日

1. ゲームコンポーネント構築:
   - GameContainer, ResourcePanel, CompanionPanel
   - RouteMap（インタラクティブ）
   - EventModal, StrategyMenu
   - JourneyLog

2. ランディングページ:
   - ゲーム紹介
   - ルール説明
   - スタートボタン

3. 勝利/敗北画面

**成果物**: 完全なゲームUI、レスポンシブデザイン、アニメーションと仕上げ

### フェーズ5: 統合とテスト（桃太郎オーケストレーター）

**期間**: 2-3日

1. 全コンポーネント統合
2. ゲーム状態永続化API
3. 統合テスト（完全フロー）
4. E2Eテスト（Playwright）:
   - 完全な旅
   - 全仲間組み合わせ
   - 勝利・敗北シナリオ
5. パフォーマンス最適化
6. コードレビューと洗練

**成果物**: 完全統合されたゲーム、統合テスト通過、E2Eテスト完了、最適化済み

### フェーズ6: ポリッシュとリリース

**期間**: 1-2日

1. CSSアニメーション
2. アクセシビリティ改善
3. 最終コードレビュー
4. ドキュメント（README）
5. デプロイ準備

## 重要ファイル

| ファイル | 目的 | 優先度 |
|---------|------|--------|
| `src/types/game.ts` | 全ての型定義の基礎 | 最高 |
| `src/lib/game/engine.ts` | ゲーム状態管理とゲームループ | 最高 |
| `src/lib/mechanics/encounters.ts` | 戦略的鬼遭遇解決システム | 高 |
| `src/hooks/useGameState.ts` | React統合と状態管理 | 高 |
| `src/components/game/RouteMap.tsx` | インタラクティブルートナビゲーション | 高 |

## 検証計画

### 単体テスト（Vitest）

```bash
npm run test:unit
npm run test:coverage
npm run test:watch
```

**カバレッジ目標**:
- ゲームエンジン: 90%
- メカニクス: 85%
- フック: 80%
- コンポーネント: 75%

### 統合テスト

- 完全な旅（開始から勝利まで）
- 全仲間募集組み合わせ
- 全イベントタイプ処理
- 全鬼遭遇戦略
- リソース枯渇シナリオ
- セーブ/ロード機能

### E2Eテスト（Playwright）

```bash
npm run test:e2e
npx playwright test basic-gameplay.spec.ts
```

**テストシナリオ**:
1. `basic-gameplay.spec.ts` - ゲーム開始、仲間募集、ルート移動、イベント処理、旅完了
2. `companion-recruitment.spec.ts` - 各仲間募集、能力発動、シナジー確認
3. `victory-scenario.spec.ts` - 最適ルートで勝利、鬼の王撃破、勝利画面確認

### 手動テストチェックリスト

- [ ] エラーなくゲーム開始
- [ ] 全仲間募集可能
- [ ] ルートマップ正しく表示
- [ ] イベント適切にトリガー
- [ ] きびだんごシステム動作
- [ ] 鬼遭遇戦略的に解決
- [ ] 勝利条件達成可能
- [ ] 敗北条件動作
- [ ] セーブ/ロード機能
- [ ] モバイル対応
- [ ] コンソールエラーなし
- [ ] 80%+テストカバレッジ

## 成功基準

- [ ] ゲームがエラーなく起動
- [ ] プレイヤーが完全な旅を完了できる
- [ ] 4人の仲間がそれぞれ固有の戦略的能力を持つ
- [ ] 戦略的決断が勝利に影響する
- [ ] 単体テストカバレッジ80%以上
- [ ] console.log が本番コードにない
- [ ] 不変パターンが使用されている
- [ ] ファイルが800行を超えない
- [ ] E2Eテストが主要なフローをカバー

## 参考資料

- 既存プラン: `.claude/plans/gleaming-mapping-octopus.md`（バトルRPG）
- 既存プラン: `.claude/plans/vivid-snacking-cook.md`（エージェント協調）
- プロジェクトガイドライン: `.claude/skills/project-guidelines-example/SKILL.md`
