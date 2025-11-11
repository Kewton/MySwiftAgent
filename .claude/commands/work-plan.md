# 作業計画立案スキル（Issue単位）

## 概要
Issue単位での具体的な作業計画を立案し、実装タスクの詳細化とスケジュールを策定するスキルです。

## 使用方法
- `/work-plan [Issue番号または概要]`
- 「Issue #123の作業計画を立案してください」

## 前提条件
- Featureは既にIssueに分割済み（`/issue-split`で実施）
- 対象Issueの概要と要件が明確

## 実行内容

あなたはテックリードです。1つのIssue実装のための具体的な作業計画を立案してください：

### 1. Issue概要の確認

```markdown
## Issue: [タイトル]
**Issue番号**: #XXX
**サイズ**: S/M/L
**作業見積**: [X]時間
**優先度**: High/Medium/Low
**依存Issue**: #YYY（あれば）
```

### 2. 詳細タスク分解

#### 実装タスク（Phase 1）
- [ ] **Task 1.1**: データモデル定義
  - 所要時間: 2時間
  - 成果物: `models/user.py`
  - 依存: なし

- [ ] **Task 1.2**: データベースマイグレーション
  - 所要時間: 1時間
  - 成果物: `migrations/001_add_user_profile.sql`
  - 依存: Task 1.1

- [ ] **Task 1.3**: API エンドポイント実装
  - 所要時間: 4時間
  - 成果物: `api/profile.py`
  - 依存: Task 1.2

- [ ] **Task 1.4**: UI コンポーネント実装
  - 所要時間: 3時間
  - 成果物: `components/ProfileView.tsx`
  - 依存: Task 1.3

#### テストタスク（Phase 2）
- [ ] **Task 2.1**: 単体テスト（モデル）
  - 所要時間: 2時間
  - 成果物: `tests/unit/test_user.py`
  - カバレッジ目標: 95%

- [ ] **Task 2.2**: 単体テスト（API）
  - 所要時間: 3時間
  - 成果物: `tests/unit/test_profile_api.py`
  - カバレッジ目標: 90%

- [ ] **Task 2.3**: 結合テスト
  - 所要時間: 2時間
  - 成果物: `tests/integration/test_profile_flow.py`
  - シナリオ数: 3

#### ドキュメントタスク（Phase 3）
- [ ] **Task 3.1**: API仕様書更新
  - 所要時間: 1時間
  - 成果物: `docs/api/profile.md`

- [ ] **Task 3.2**: README更新
  - 所要時間: 0.5時間
  - 成果物: `README.md`

### 3. タスク依存関係

```mermaid
graph TD
    T11[Task 1.1<br/>モデル定義] --> T12[Task 1.2<br/>マイグレーション]
    T12 --> T13[Task 1.3<br/>API実装]
    T13 --> T14[Task 1.4<br/>UI実装]

    T11 --> T21[Task 2.1<br/>単体テスト<br/>モデル]
    T13 --> T22[Task 2.2<br/>単体テスト<br/>API]
    T14 --> T23[Task 2.3<br/>結合テスト]

    T23 --> T31[Task 3.1<br/>API仕様書]
    T23 --> T32[Task 3.2<br/>README]
```

### 4. 作業スケジュール

#### 日次計画

**Day 1 (6時間)**
- 09:00-11:00: Task 1.1（モデル定義）
- 11:00-12:00: Task 1.2（マイグレーション）
- 13:00-17:00: Task 1.3（API実装）

**Day 2 (7時間)**
- 09:00-12:00: Task 1.4（UI実装）
- 13:00-15:00: Task 2.1（単体テスト・モデル）
- 15:00-18:00: Task 2.2（単体テスト・API）

**Day 3 (3.5時間)**
- 09:00-11:00: Task 2.3（結合テスト）
- 11:00-12:00: Task 3.1（API仕様書）
- 13:00-13:30: Task 3.2（README）
- 13:30-15:00: コードレビュー準備、PR作成

**総作業時間**: 16.5時間（約2.5日）

### 5. チェックポイント

| タイミング | 確認事項 | 対応 |
|-----------|---------|------|
| Task 1.2完了時 | マイグレーション動作確認 | ローカルDB確認 |
| Task 1.4完了時 | UI動作確認 | 手動テスト実施 |
| Phase 2完了時 | カバレッジ目標達成 | 未達の場合追加テスト |
| PR作成前 | CI/CDパス | エラー時は修正 |

### 6. リスクと対策

| リスク | 発生確率 | 影響 | 対策 |
|-------|---------|------|------|
| 外部APIレスポンス遅延 | 中 | 実装遅延2時間 | モックAPI先行実装 |
| UIデザイン仕様不明確 | 低 | 実装遅延1時間 | デザイナーと事前確認 |
| テストデータ不足 | 中 | テスト遅延1時間 | フィクスチャ事前準備 |

### 7. 成果物チェックリスト

#### コード
- [ ] `models/user.py`
- [ ] `migrations/001_add_user_profile.sql`
- [ ] `api/profile.py`
- [ ] `components/ProfileView.tsx`

#### テスト
- [ ] `tests/unit/test_user.py`
- [ ] `tests/unit/test_profile_api.py`
- [ ] `tests/integration/test_profile_flow.py`

#### ドキュメント
- [ ] `docs/api/profile.md`
- [ ] `README.md`更新

### 8. Definition of Done

Issue完了条件：
- [ ] すべてのタスクが完了
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テスト全シナリオパス
- [ ] CI/CDグリーン
- [ ] コードレビュー承認
- [ ] ドキュメント更新完了
- [ ] フィーチャーフラグ設定（必要な場合）

### 9. 次のアクション

作業計画承認後：
1. **ブランチ作成**: `issue/XXX-[feature-name]`
2. **worktree作成**: 別セッションで作業開始
3. **タスク実行**: 計画に従って実装
4. **進捗報告**: `/progress-report`で定期報告

## 出力フォーマット

GitHub Issueのコメントやプロジェクト管理ツールに転記可能なMarkdown形式。

## モデル設定
- model: opus（詳細な計画立案のため）
- temperature: 0.5（論理的で具体的な計画のため）