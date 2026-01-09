# AIエージェント ワークフロー生成 問題点総合分析レポート

## 概要

- **JobMaster ID**: `jm_01KEF4YWQMF3KG2BNSH0B7YAK3`
- **ジョブ内容**: Google検索 → メール内容生成 → Gmail送信
- **分析日**: 2026-01-09
- **ステータス**: ✅ 修正完了・検証済み（v2: 記事コンテンツ取得対応）
- **成功ジョブID（v1）**: `j_01KEG0CSSNPSQNTMJGWMFZC2GS`（スニペットのみ）
- **成功ジョブID（v2）**: `j_01KEG1MW0F58DWBN7VVD8GQV97`（記事コンテンツ取得）

---

## 発見された問題点カテゴリ

### カテゴリ1: APIスキーマの誤り（全タスク共通）

| 問題 | 発生タスク | 詳細 |
|------|-----------|------|
| パラメータ名の誤り | Task 1 | `query` → `queries`, `num_results` → `num` |
| データ型の誤り | Task 1 | 文字列 → 配列 |
| リクエストボディ構造の誤り | Task 2 | `prompt`/`schema` → `user_input`/`model_name`/`force_json` |
| エンドポイント選択の誤り | Task 2 | `/generate` → `/utility/jsonoutput` |

**根本原因**: AIエージェントがexpertAgentのAPI仕様（OpenAPI/Swagger）を正確に参照していない。

**修正提案**:
1. API仕様書をプロンプトに含める
2. ワークフロー生成前にAPIスキーマ検証を実施
3. Few-shotサンプルに実際に動作するAPI呼び出し例を追加

---

### カテゴリ2: ソースパス参照の誤り（全タスク共通）

| 問題 | 発生タスク | 誤ったパス | 正しいパス |
|------|-----------|-----------|-----------|
| user_input欠落 | Task 1 | `:source.query` | `:source.user_input.query` |
| job_params欠落 | Task 2 | `:source.query` | `:source.job_params.query` |
| タスク出力参照 | Task 2 | `:source.search_results` | `:source.user_input.search_results` |
| user_input欠落 | Task 3 | `:source.email_subject` | `:source.user_input.email_subject` |

**根本原因**: JobQueueのTaskMasterが`body_template`でリクエストを変換する仕組みを理解していない。

**body_template変換ルール**:
```json
{
  "user_input": "{{tasks[N-1].output_data}}" または "{{job.body}}",
  "job_params": "{{job.body}}",
  "model_name": "taskmaster/..."
}
```

**修正提案**:
1. `GRAPHAI_WORKFLOW_GENERATION_RULES.md`にJobQueue統合ルールを追加
2. タスクチェーンのデータフロー図をプロンプトに含める
3. ソースパス検証ロジックを追加

---

### カテゴリ3: タイムアウト単位の誤り（全タスク共通）

| タスク | AI生成値 | 正しい値 | 誤差 |
|-------|---------|---------|------|
| Task 1 | `180` | `180000` | 1000倍 |
| Task 2 | `120` | `120000` | 1000倍 |
| Task 3 | `60` | `60000` | 1000倍 |

**根本原因**: AIエージェントがGraphAIのtimeoutがミリ秒単位であることを認識していない。

**修正提案**:
1. `GRAPHAI_WORKFLOW_GENERATION_RULES.md`にtimeout単位を明記
2. 生成後のYAML検証でtimeout値をチェック（1000未満は警告）
3. Few-shotサンプルで正しいtimeout値を示す

---

### カテゴリ4: stringTemplateAgentの機能誤解 🆕【重大】

**症状**: LLMが検索結果を受け取れず、汎用的な内容のメールが生成された

**原因**: AIエージェントが `${JSON.stringify(results)}` をJavaScript評価されると誤解

**AI生成ワークフロー（誤り）**:
```yaml
build_prompt:
  agent: stringTemplateAgent
  inputs:
    results: :search_results
  params:
    template: |
      検索結果: ${JSON.stringify(results)}  # ❌ 評価されない！
```

**実際の出力**:
```
検索結果: ${JSON.stringify(results)}  # リテラル文字列として出力
```

**技術的事実**:
- `stringTemplateAgent` は**単純な変数置換のみ**を行う
- JavaScript式（`JSON.stringify()`等）は**評価されない**
- オブジェクトは `[object Object]` としてリテラル出力される

**正しい解決方法**:
```yaml
# 1. json_stringify APIを呼び出してオブジェクトを文字列化
stringify_results:
  agent: fetchAgent
  inputs:
    url: http://localhost:8004/aiagent-api/v1/utility/json_stringify
    method: POST
    body:
      data: :source.user_input.search_results
  timeout: 30000

# 2. 文字列化済みの結果をテンプレートに埋め込む
build_prompt:
  agent: stringTemplateAgent
  inputs:
    results: :stringify_results.json_string  # ✅ 文字列
  params:
    template: |
      検索結果: ${results}  # ✅ 正しく展開される
```

**修正提案**:
1. `GRAPHAI_WORKFLOW_GENERATION_RULES.md`にstringTemplateAgentの制限事項を明記
2. `/utility/json_stringify` APIの使用方法をドキュメント化
3. オブジェクト→文字列変換の標準パターンをFew-shotサンプルに追加

---

### カテゴリ5: user_input型制約の誤解 🆕【重大】

**症状**: HTTP 422 "Input should be a valid string"

**AI生成ワークフロー（誤り）**:
```yaml
body:
  user_input:
    task: メール用要約文生成
    keyword: :source.job_params.query
    search_results: :source.user_input.search_results  # ❌ オブジェクト
```

**エラーレスポンス**:
```json
{
  "detail": "Validation error",
  "errors": [{
    "type": "string_type",
    "loc": ["body", "user_input"],
    "msg": "Input should be a valid string"
  }]
}
```

**技術的事実**:
- expertAgentの `/aiagent/utility/jsonoutput` APIの `user_input` は `str` 型
- オブジェクトや配列は受け付けない

**修正提案**:
1. APIスキーマに型制約を明記
2. 構造化データをLLMに渡す場合は事前に文字列化する必要があることをドキュメント化

---

### カテゴリ6: 不要な中間ノードの生成（Task 2, Task 3）

AI生成ワークフローには以下のような不要な中間ノードが含まれていた：

```yaml
# 不要なノード例
extract_search_results:
  agent: copyAgent
  inputs:
    search_results: :source.search_results
  params:
    namedKey: search_results
```

**問題点**:
1. `copyAgent`の`namedKey`の使用方法が誤っている
2. 直接参照できるデータに対して不要な変換を行っている
3. デバッグを困難にしている

**修正提案**:
1. 中間ノードが必要なケースを明確化（データ変換が必要な場合のみ）
2. シンプルなワークフロー設計を推奨するルールを追加
3. 不要ノード検出の検証ロジックを追加

---

### カテゴリ7: 環境変数URLの使用（全タスク共通）

```yaml
# AI生成（誤）
url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/...

# 正しい
url: http://localhost:8004/aiagent-api/v1/...
```

**根本原因**: GraphAI実行時に環境変数`${...}`形式が解決されない。

**修正提案**:
1. ワークフロー生成時に解決済みURLを使用
2. 設定ファイルからベースURLを取得する仕組みを構築
3. URL検証ロジックを追加

---

### カテゴリ8: 記事コンテンツ未取得 🆕【機能改善】

**症状**: メール本文がGoogle検索のスニペット（要約文）のみで構成され、記事の実際の内容が含まれていない

**v1の問題点**:
- Google検索APIは各記事の`snippet`（150文字程度の要約）のみを返す
- LLMはスニペットを「再整形」するだけで、記事の深い内容を含められない
- 結果として、メール本文は表面的な情報の羅列になる

**v1のメール出力例**:
```
大谷翔平選手の妻、真美子さんに関する情報をまとめました。
* 田中真美子 (Wikipedia): 大谷翔平選手は2024年2月29日に結婚を発表し...
  ← スニペットの転記のみ
```

**v2の解決策**:
1. 新規API `/utility/extract_article_urls` を追加（検索結果からURL抽出）
2. 新規API `/utility/fetch_web_content` を追加（URLから記事をMarkdown取得）
3. 上位2記事の全文コンテンツを取得してLLMに渡す

**v2のワークフロー構造**:
```
extract_urls → fetch_article_1 → stringify_articles → build_prompt → generate_email_content
            → fetch_article_2 ↗
            → stringify_search_results ↗
```

**v2のメール出力例**:
```
大谷翔平選手の妻、田中真美子さんに関する情報をお届けします。

田中真美子さんは1996年12月11日生まれの29歳。元バスケットボール選手で、
富士通レッドウェーブに所属していました。ポジションはセンターで、身長180cm。
（中略）
大谷選手との出会いについて、石田雄太氏のインタビューによると...
（中略）
2024年2月29日に大谷選手が自身のInstagramで結婚を発表し...
  ← 記事の実際の内容を深く分析した要約
```

**技術的実装**:
1. `/utility/extract_article_urls`: ネストされた検索結果構造から記事URLを抽出
2. `/utility/fetch_web_content`: URLからHTML取得→Markdown変換→クリーンアップ

**修正提案**:
1. Google検索→記事要約のワークフローパターンをドキュメント化
2. `/utility/fetch_web_content` APIをワークフロー生成ルールに追加
3. 「記事コンテンツ取得」を標準ステップとしてテンプレート化

---

## 問題点サマリー

| カテゴリ | 影響範囲 | 重大度 | 修正優先度 |
|---------|---------|--------|-----------|
| APIスキーマの誤り | 全タスク | 🔴 高 | P0 |
| ソースパス参照の誤り | 全タスク | 🔴 高 | P0 |
| stringTemplateAgent誤解 | Task 2 | 🔴 高 | P0 |
| user_input型制約の誤解 | Task 2 | 🔴 高 | P0 |
| タイムアウト単位の誤り | 全タスク | 🟡 中 | P1 |
| 不要な中間ノード生成 | Task 2, 3 | 🟢 低 | P2 |
| 環境変数URLの使用 | 全タスク | 🟡 中 | P1 |
| **記事コンテンツ未取得** | Task 2 | 🔴 高 | **P0** |

---

## 修正後のワークフロー

### Task 2: メール内容生成（v2: 記事コンテンツ取得対応）

```yaml
version: '0.5'
nodes:
  source: {}

  # 検索結果から記事URLを抽出
  extract_urls:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/extract_article_urls
      method: POST
      body:
        search_results: :source.user_input.search_results
        max_urls: 2
    timeout: 30000

  # 1件目の記事コンテンツを取得
  fetch_article_1:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/fetch_web_content
      method: POST
      body:
        url: :extract_urls.article_url_1
        upload_to_drive: false
    timeout: 60000

  # 2件目の記事コンテンツを取得
  fetch_article_2:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/fetch_web_content
      method: POST
      body:
        url: :extract_urls.article_url_2
        upload_to_drive: false
    timeout: 60000

  # 取得した記事コンテンツをJSON文字列に変換
  stringify_articles:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/json_stringify
      method: POST
      body:
        data:
          article_1: :fetch_article_1.markdown_content
          article_2: :fetch_article_2.markdown_content
    timeout: 30000

  # 検索結果の概要もJSON文字列に変換
  stringify_search_results:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/json_stringify
      method: POST
      body:
        data: :source.user_input.search_results
    timeout: 30000

  # プロンプトを構築（記事の全文コンテンツを含む）
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      query: :source.user_input.query
      search_overview: :stringify_search_results.json_string
      articles: :stringify_articles.json_string
    params:
      template: |
        以下の情報を元に、検索キーワードに関するメール用の要約文を日本語で生成してください。
        【検索キーワード】${query}
        【検索結果概要】${search_overview}
        【記事の本文コンテンツ】${articles}

        記事の本文内容から抽出した具体的な情報を含む詳細なメール本文を作成してください。
        出力はJSON形式: {"email_subject": "件名", "email_body": "本文"}

  # LLMでメール内容を生成
  generate_email_content:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt
        model_name: gemini-2.0-flash
        force_json: true
    timeout: 180000

  # 出力をフォーマット
  output:
    agent: copyAgent
    inputs:
      email_subject: :generate_email_content.result.email_subject
      email_body: :generate_email_content.result.email_body
    isResult: true
```

---

## 改善アクションプラン

### Phase 1: ドキュメント強化（即時対応）

1. **`GRAPHAI_WORKFLOW_GENERATION_RULES.md`の更新**
   - JobQueue統合時のソースパスルール追加
   - タイムアウト単位（ミリ秒）の明記
   - 環境変数URL使用禁止ルール追加
   - **stringTemplateAgentの制限事項を追加** 🆕
   - **`/utility/json_stringify` APIの使用方法を追加** 🆕

2. **Few-shotサンプルの拡充**
   - Google検索ワークフローの完全なサンプル追加
   - **オブジェクト→文字列変換を含むLLM呼び出しサンプル追加** 🆕
   - メール送信ワークフローのサンプル追加

### Phase 2: 検証ロジック強化（短期対応）

1. **APIスキーマ検証**
   - ワークフロー生成前にexpertAgentのOpenAPI仕様を参照
   - リクエストボディのスキーマ検証
   - **user_input型チェック追加** 🆕

2. **stringTemplateAgent検証** 🆕
   - テンプレート内のJavaScript式を検出して警告
   - オブジェクト参照を検出して`json_stringify`使用を推奨

3. **ソースパス検証**
   - `source.user_input`/`source.job_params`の必須化
   - タスクチェーンのデータフロー検証

4. **YAML検証**
   - timeout値の範囲チェック
   - URL形式チェック
   - 不要ノード検出

---

## 検証結果

### v1検証結果（スニペットのみ）

```json
{
  "job_id": "j_01KEG0CSSNPSQNTMJGWMFZC2GS",
  "status": "succeeded",
  "tasks": [
    {"name": "Google検索", "status": "SUCCEEDED", "duration_ms": 1280},
    {"name": "メール生成", "status": "SUCCEEDED", "duration_ms": 3474},
    {"name": "メール送信", "status": "SUCCEEDED", "duration_ms": 561}
  ],
  "total_duration_ms": 5315
}
```

**Task 2 出力サンプル（v1）**: スニペットの再整形のみ
```json
{
  "email_subject": "大谷翔平選手の最新情報：ドジャースでの活躍、同僚の証言、公式Instagram",
  "email_body": "大谷翔平選手に関する最新情報をお届けします。\n\n* 大谷翔平 - Wikipedia: 岩手県奥州市出身のプロ野球選手...\n  ← スニペットの転記のみ"
}
```

### v2検証結果（記事コンテンツ取得対応） ✅

```json
{
  "job_id": "j_01KEG1MW0F58DWBN7VVD8GQV97",
  "status": "succeeded",
  "search_keyword": "大谷翔平の妻"
}
```

**Task 2 出力サンプル（v2）**: 記事の実際の内容を深く分析した要約
```json
{
  "email_subject": "大谷翔平の妻、田中真美子さんとは？出会いから現在までを徹底解剖",
  "email_body": "大谷翔平選手の妻、田中真美子さんに関する情報をお届けします。\n\n田中真美子さんは1996年12月11日生まれの29歳（2026年1月9日時点）。元バスケットボール選手で、富士通レッドウェーブに所属していました。ポジションはセンターで、身長180cm。小学校からバスケットボールを始め、中学3年生の時には身長が177cmに達し、U-16日本代表にも選出されました。2023年4月に引退を発表。\n\n大谷選手との出会いについて、石田雄太氏のインタビューによると、大谷選手自身は最初の出会いをはっきりと覚えていないものの、田中さんは「すれ違いざまに挨拶してくれた」と語っています。その後、2週間ちょっとの間に3回会ったうち、2回は大谷選手も覚えているとのこと。大谷選手は田中さんと一緒にいて「楽だし、楽しい」と感じ、「気を遣う必要がない」ため、結婚を決めたそうです。\n\n2024年2月29日に大谷選手が自身のInstagramで結婚を発表し、3月15日には田中さんと並ぶ写真が初めて公開されました。同年12月29日には、第一子を妊娠していることが発表され、2025年4月19日（日本時間20日）に第一子となる長女が誕生しました。\n\n大谷選手は田中さんのことを「翔平さん」または「翔さん」と呼んでおり、田中さんは大谷選手を名前で呼び捨てにしているそうです。田中さんの誕生日には、サイズオーダーしたシューズをプレゼントしたとのこと。また、大谷選手が作った料理の中で一番美味しかったのは、田中さんがルーから作ったドライカレーだったそうです。\n\n現在、大谷選手は広大な庭とプール付きの家に住んでおり、愛犬デコピンが泳ぎを覚えるのを手伝っているそうです。"
}
```

**v2で改善された点**:
1. 田中真美子さんの具体的なプロフィール（生年月日、身長、所属チーム、ポジション）
2. 大谷選手との出会いの詳細（インタビュー内容の引用）
3. 結婚発表、妊娠発表、出産の具体的な日付
4. 愛称、誕生日プレゼント、料理のエピソードなどの詳細情報
5. 現在の生活状況（家、愛犬デコピン）

---

## 関連ドキュメント

- [Task 1 分析レポート](./task1-google-search-analysis.md)
- [Task 2 分析レポート](./task2-email-generation-analysis.md)
- [Task 3 分析レポート](./task3-gmail-send-analysis.md)
- [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
