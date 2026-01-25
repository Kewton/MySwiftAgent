# GraphAI ワークフロー開発 - よくあるエラーパターン集

このドキュメントは、GraphAI ワークフロー開発時に頻繁に発生するエラーパターンと解決策をまとめたものです。

## 目次
- [mapAgent関連エラー](#mapagent関連エラー)
- [stringTemplateAgent関連エラー](#stringtemplateagent関連エラー)
- [環境変数関連エラー](#環境変数関連エラー)
- [HTTPダウンロード関連エラー](#httpダウンロード関連エラー)
- [デバッグ手法](#デバッグ手法)

---

## mapAgent関連エラー

### エラー1: `[object Object]` が表示される

**症状:**
```
メール本文やログに [object Object] と表示される
期待値: 実際のデータ内容
```

**原因:**
- mapAgentで `compositeResult: true` が未指定
- 後続ノードで誤った参照方法（`:mapAgent` ではなく `:mapAgent.isResultノード` が正しい）

**解決策:**

❌ **誤った実装:**
```yaml
format_file_list:
  agent: mapAgent
  inputs:
    rows: :upload_pdfs.files
  graph:
    nodes:
      format_single_file:
        agent: stringTemplateAgent
        # ...
        isResult: true
  # compositeResult が未指定！

join_file_list:
  agent: arrayJoinAgent
  inputs:
    array: :format_file_list  # ← 誤った参照
```

✅ **正しい実装:**
```yaml
format_file_list:
  agent: mapAgent
  inputs:
    rows: :upload_pdfs.files
  params:
    compositeResult: true  # ← 必須！
  graph:
    nodes:
      format_single_file:
        agent: stringTemplateAgent
        # ...
        isResult: true
  console:
    after: true  # ← デバッグ用ログ有効化

join_file_list:
  agent: arrayJoinAgent
  inputs:
    array: :format_file_list.format_single_file  # ← 正しい参照
  params:
    separator: "\n"
```

**参照:** GRAPHAI_WORKFLOW_GENERATION_RULES.md Lines 189-303

---

### エラー2: mapAgent の出力が空

**症状:**
```
後続ノードで mapAgent の結果を参照すると undefined または空配列
```

**原因:**
- subgraph内に `isResult: true` を持つノードがない
- `compositeResult: true` が未指定

**解決策:**

✅ **正しい実装:**
```yaml
process_items:
  agent: mapAgent
  inputs:
    rows: :input_array
  params:
    compositeResult: true  # ← 必須
  graph:
    nodes:
      process_single_item:
        agent: stringTemplateAgent
        inputs:
          data: :row
        params:
          template: "Processed: ${data}"
        isResult: true  # ← subgraph の出力として指定
```

---

## stringTemplateAgent関連エラー

### エラー3: 配列・オブジェクトが `[object Object]` になる

**症状:**
```yaml
format_email:
  agent: stringTemplateAgent
  inputs:
    files: :upload_result.files  # ← 配列
  params:
    template: "Files: ${files}"

# 結果: Files: [object Object],[object Object]
```

**原因:**
- stringTemplateAgent は配列・オブジェクトを自動シリアライズしない
- プリミティブ型（string, number, boolean）のみ直接展開可能

**解決策:**

✅ **mapAgent + arrayJoinAgent で事前文字列化:**
```yaml
# 1. 各要素を文字列に変換
format_file_list:
  agent: mapAgent
  inputs:
    rows: :upload_result.files
  params:
    compositeResult: true
  graph:
    nodes:
      format_single:
        agent: stringTemplateAgent
        inputs:
          name: :row.file_name
          size: :row.file_size
        params:
          template: "- ${name} (${size} bytes)"
        isResult: true

# 2. 配列を1つの文字列に結合
join_files:
  agent: arrayJoinAgent
  inputs:
    array: :format_file_list.format_single
  params:
    separator: "\n"

# 3. 文字列化された結果を使用
format_email:
  agent: stringTemplateAgent
  inputs:
    files: :join_files.text  # ← .text フィールドを参照
  params:
    template: |
      Files:
      ${files}
```

---

### エラー4: テンプレート変数が展開されない

**症状:**
```
出力: "Hello ${name}"
期待: "Hello John"
```

**原因:**
- inputs に該当フィールドが存在しない
- フィールド名のタイポ

**解決策:**

✅ **デバッグ手順:**
```yaml
test_template:
  agent: stringTemplateAgent
  inputs:
    name: :previous_node.user_name  # ← フィールド名を確認
  params:
    template: "Hello ${name}"
  console:
    after: true  # ← ログで inputs を確認
```

```bash
# APIレスポンスで previous_node の出力を確認
curl ... | jq '.results.previous_node'
```

---

## 環境変数関連エラー

### エラー5: subgraph内で環境変数が展開されない

**症状:**
```yaml
upload_files:
  agent: mapAgent
  graph:
    nodes:
      call_api:
        agent: fetchAgent
        inputs:
          url: "${EXPERTAGENT_BASE_URL}/api/upload"  # ← 展開されない
```

**原因:**
- GraphAIの環境変数展開は親グラフのみ実行
- subgraph内では既に展開済みの値を受け取る必要

**解決策:**

✅ **親グラフで環境変数を展開後、inputsで渡す:**
```yaml
# 親グラフで環境変数展開
api_base_url:
  value: "${EXPERTAGENT_BASE_URL}"

upload_files:
  agent: mapAgent
  inputs:
    rows: :file_list
    base_url: :api_base_url  # ← 展開済み値を渡す
  params:
    compositeResult: true
  graph:
    nodes:
      call_api:
        agent: fetchAgent
        inputs:
          url: :base_url  # ← 変数として参照
          # ...
```

---

## HTTPダウンロード関連エラー

### エラー6: ダウンロードしたファイルが破損

**症状:**
- PDFファイルをアップロードしたが、開けない
- ファイルサイズが異常に小さい（< 1KB）
- Content-Type が `text/html`

**原因:**
- サーバーが403/404エラーページを返却（HTML）
- User-Agent ヘッダー未設定によるアクセス拒否

**解決策:**

❌ **誤った実装（検証なし）:**
```python
async def download_file(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content  # ← エラーページもそのまま返す
```

✅ **正しい実装（検証あり）:**
```python
async def download_file_from_url(
    url: str,
    user_agent: str,
    referer: str | None,
    timeout: int,
) -> tuple[str, bytes, str | None]:
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        # 1. Content-Type検証
        content_type = response.headers.get("Content-Type")
        if content_type and "text/html" in content_type.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file: received HTML page (likely 403 Forbidden). URL: {url}"
            )

        # 2. ファイルサイズ検証
        if len(response.content) < 1024:
            logger.warning(
                f"Downloaded file is very small ({len(response.content)} bytes), may be an error page"
            )

        file_name = url.split("/")[-1].split("?")[0]
        return file_name, response.content, content_type
```

**重要:** LLMプロンプトでUser-Agent指定を依頼するのは不安定（成功率60-80%）。確実性が必要な場合はサーバー側API実装を推奨。

---

### エラー7: LLMプロンプトでのHTTPヘッダー指定が無視される

**症状:**
- Action Agent のプロンプトで「User-Agentを設定してください」と指示
- 一部のファイルでは正常、一部では403エラー（成功率60-80%）

**原因:**
- LLMが指示を無視または誤解釈
- プロンプトの解釈に揺らぎがある

**解決策:**

❌ **非推奨（LLMプロンプト依存）:**
```yaml
upload_file:
  agent: fetchAgent
  inputs:
    url: "${ACTION_AGENT_URL}"
    body:
      user_input: |
        Upload this PDF to Google Drive.
        PDF URL: ${pdf_url}

        IMPORTANT: Use these HTTP headers when downloading:
        - User-Agent: Mozilla/5.0...
        - Referer: https://example.com/
  # → LLMが指示を無視する可能性あり
```

✅ **推奨（サーバー側API実装）:**
```python
# expertAgent側で専用API実装
@router.post("/utility/drive/upload_from_url")
async def upload_files_from_urls(request: DriveUploadFromUrlRequest):
    """URL配列からGoogle Driveに一括アップロード（User-Agent保証）"""
    tasks = [
        upload_single_file(
            url=url,
            folder_id=request.folder_id,
            user_agent=request.user_agent,  # ← サーバー側で確実に設定
            referer=request.referer,
            timeout=request.timeout,
        )
        for url in request.urls
    ]
    results = await asyncio.gather(*tasks)
    return DriveUploadFromUrlResponse(files=list(results))
```

```yaml
# ワークフローからAPI直接呼び出し
upload_pdfs:
  agent: fetchAgent
  inputs:
    url: "${EXPERTAGENT_BASE_URL}/v1/utility/drive/upload_from_url"
    method: POST
    body:
      urls: :pdf_links
      folder_id: :drive_folder_id
      user_agent: "Mozilla/5.0..."  # ← 確実に適用される
      referer: "https://example.com/"
```

---

## デバッグ手法

### 手法1: 各ノードの出力を確認

```yaml
# 全ノードに console.after: true を追加
extract_data:
  agent: fetchAgent
  inputs:
    url: "${API_URL}"
  console:
    after: true  # ← ログ有効化

process_data:
  agent: mapAgent
  inputs:
    rows: :extract_data.result
  params:
    compositeResult: true
  console:
    after: true  # ← ログ有効化
```

```bash
# APIレスポンスで各ノードの出力を確認
curl ... | jq '.results.extract_data'
curl ... | jq '.results.process_data'
```

---

### 手法2: 段階的テスト

```bash
# Phase 1: 最小構成（1アイテムのみ）
cat << EOF > /tmp/test_minimal.json
{
  "urls": ["https://example.com/file1.pdf"],
  "folder_id": "TEST_FOLDER_ID"
}
EOF

curl -X POST http://localhost:8105/api/v1/workflow \
  -d @/tmp/test_minimal.json | jq '.results'

# Phase 2: 複数アイテム
cat << EOF > /tmp/test_multiple.json
{
  "urls": [
    "https://example.com/file1.pdf",
    "https://example.com/file2.pdf"
  ],
  "folder_id": "TEST_FOLDER_ID"
}
EOF
```

---

### 手法3: 中間データをファイルに保存

```bash
# APIレスポンス全体を保存
curl ... > /tmp/workflow_result.json

# 各ノードの出力を個別確認
jq '.results.extract_pdf_links' /tmp/workflow_result.json
jq '.results.upload_pdfs.files[]' /tmp/workflow_result.json
jq '.results.format_upload_results' /tmp/workflow_result.json

# エラーノードを抽出
jq '.logs[] | select(.state == "failed")' /tmp/workflow_result.json
```

---

### 手法4: 失敗ノードの特定

```bash
# エラーが発生したノードを特定
curl ... | jq '.logs[] | select(.state != "completed" and .state != "injected") | {nodeId, state, errorMessage}'

# 例:
# {
#   "nodeId": "upload_pdfs",
#   "state": "failed",
#   "errorMessage": "HTTP 403 Forbidden"
# }
```

---

## チェックリスト

### ワークフロー開発前

- [ ] GRAPHAI_WORKFLOW_GENERATION_RULES.md を確認
- [ ] 必須参照ドキュメントを確認
  - WORKFLOW_DEVELOPMENT_TEMPLATE.md
  - ITERATION_RECORD_TEMPLATE.md
- [ ] 外部サイトアクセス時はUser-Agent要否を調査

### 実装時

- [ ] mapAgent使用時は `compositeResult: true` を指定
- [ ] 環境変数は親グラフで展開
- [ ] stringTemplateAgentには単純型のみ渡す
- [ ] 全ノードに `console.after: true` を追加

### テスト時

- [ ] 最小構成（1アイテム）でテスト
- [ ] APIレスポンスの `.results` を確認
- [ ] エラーノードがないか確認 (`jq '.logs[] | select(.state == "failed")'`)
- [ ] ファイルサイズ・Content-Typeを検証

---

## 参考リンク

- [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [WORKFLOW_DEVELOPMENT_TEMPLATE.md](./WORKFLOW_DEVELOPMENT_TEMPLATE.md)
- [ITERATION_RECORD_TEMPLATE.md](./ITERATION_RECORD_TEMPLATE.md)
- [GraphAI 公式ドキュメント](https://github.com/receptron/graphai)

---

**最終更新:** 2025-10-16
**作成者:** Claude Code (AI開発アシスタント)
