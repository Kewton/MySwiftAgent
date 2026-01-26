# Issue #412 修正報告

## 概要

| 項目 | 内容 |
|------|------|
| Issue | #412 bug(E2E): test_full_workflow_e2e.shが古いJobVersionを誤って使用する |
| 重大度 | Medium |
| 修正日 | 2026-01-27 |
| 修正者 | Claude Code |

## 根本原因分析

### 問題A: 間違ったJobVersion IDの取得

**原因**: E2Eスクリプトの正規表現 `re.search(r"jv_[a-zA-Z0-9_]+", c)` が、ページ内で「最初に見つかった」`jv_`IDを返していた。generateページには`recentJobVersions`（履歴）が含まれ、それが先に出現するため、古い完了済みJobVersionが選択されていた。

**影響**: 実際に生成中のJob（`currentGeneratingJob`）ではなく、古いGraphAiServer用のJobVersionが使用された。

### 問題B: `active`ステータスを「完了」と誤判定

**原因**: ステータス判定で `if [ "$JOB_STATUS" = "success" ] || [ "$JOB_STATUS" = "active" ]` としていたため、GraphAiServer用の`active`（実行待ち）ステータスを「完了」として扱っていた。

**影響**: 古いGraphAiServer用のJobVersionがHTTP 422エラーで失敗。

## 実施した対策

### 対策A: currentGeneratingJobを明示的に抽出

```python
# 修正後: currentGeneratingJobオブジェクト内のidを抽出
match = re.search(r'currentGeneratingJob.*?"id":\s*"(jv_[a-zA-Z0-9_]+)"', content)
if match:
    print(match.group(1))
else:
    # フォールバック: 従来の動作
    fallback = re.search(r'jv_[a-zA-Z0-9_]+', content)
    print(fallback.group(0) if fallback else "")
```

### 対策B: activeステータスを完了とみなさない

```bash
# 修正前
if [ "$JOB_STATUS" = "success" ] || [ "$JOB_STATUS" = "active" ]; then

# 修正後
if [ "$JOB_STATUS" = "success" ]; then
    # successのみを完了として扱う
elif [ "$JOB_STATUS" = "generating" ] || [ "$JOB_STATUS" = "active" ]; then
    # どちらも待機継続
```

## テスト結果

| テスト | 結果 | 備考 |
|--------|------|------|
| E2Eテスト実行 | ✅ PASSED | 全4タスク成功 |
| メール送信 | ✅ 完了 | Gmail Message ID確認済み |
| ワークフロー実行 | ✅ 正常 | TaskFlowエンジンで実行 |

## 修正ファイル

- `scripts/e2e/cross-service/test_full_workflow_e2e.sh`
  - 363-383行: JobVersion ID取得ロジック
  - 389-404行: ステータス判定ロジック

## 残作業

- [ ] コミット・プッシュ
- [ ] Issue #412 クローズ

## 関連Issue

- Issue #411: myAgentDeskのJobVersionがgenerating状態で停止する問題（未修正、別Issue）
