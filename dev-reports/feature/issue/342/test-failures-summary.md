# テスト失敗サマリー

**作成日**: 2026-01-09
**テスト実行時間**: 6668.19秒 (1:51:08)
**結果**: 3827 passed, 25 failed, 90 skipped, 130 warnings, 24 errors

---

## 1. ERRORs (24件 - 4テストファイル)

### tests/acceptance/test_issue_342_workflow_quality_acceptance.py
| テスト名 | ステータス |
|---------|-----------|
| test_graphai_yaml_has_inputs_with_url_method_body | ERROR |
| test_slack_notify_pattern_has_correct_structure | ERROR |
| test_agent_selector_maps_gmail_send_to_fetchagent | ERROR |
| test_agent_selector_maps_google_search_to_fetchagent | ERROR |

**推定原因**: 受入テスト環境の設定問題またはAPIキー未設定

---

## 2. FAILEDs (25件)

### 2.1 API Injection / Bug Fixes
| ファイル | テスト名 |
|---------|---------|
| test_issue_342_api_injection_acceptance.py | test_scenario_2_all_tasks_have_recommended_apis |
| test_issue_342_bug_fixes_acceptance.py | test_e2e_workflow_generation_completes |

### 2.2 Integration Tests
| ファイル | テスト名 |
|---------|---------|
| test_e2e_workflow.py | test_e2e_workflow_execution_time |
| test_issue_333_schema_validation.py | test_type_validation_rules_included_in_prompt |
| test_issue_338_generator_schemas.py | test_get_api_response_schemas_is_called_when_recommended_apis_exist |
| test_issue_338_generator_schemas.py | test_generator_continues_if_schema_retrieval_fails |
| test_issue_342_v2_response.py | test_orchestrator_create_result_includes_tasks |
| test_issue_342_v2_response.py | test_end_to_end_flow_includes_task_breakdown |
| test_job_generator_v2_integration.py | test_full_workflow_with_mocked_services |
| test_test_mode_api.py | test_google_search_test_mode |
| test_test_mode_api.py | test_planner_mapper_workflow |

### 2.3 Scenario Tests
| ファイル | テスト名 |
|---------|---------|
| test_issue_177_scenarios.py | TestScenario1_CorporateIRAnalysis::test_job_task_generation |
| test_issue_177_scenarios.py | TestScenario2_WebsitePDFExtraction::test_job_task_generation |
| test_issue_177_scenarios.py | TestScenario2_WebsitePDFExtraction::test_workflow_generation |
| test_issue_177_scenarios.py | TestScenario3_GmailPodcastGeneration::test_workflow_generation |
| test_issue_177_scenarios.py | TestScenario4_KeywordPodcastGeneration::test_job_task_generation |
| test_issue_177_scenarios.py | TestScenario4_KeywordPodcastGeneration::test_workflow_generation |

### 2.4 Unit Tests
| ファイル | テスト名 |
|---------|---------|
| test_job_generator_endpoints.py | test_create_job_in_background_success |
| test_job_generator_endpoints.py | test_create_job_in_background_failure |
| test_workflow_gen/test_workflow.py | test_default_initialization |
| test_workflow_gen/test_yaml_generator.py | test_default_initialization |
| test_schemas.py | test_search_utility_request_full |
| test_task_breakdown_workflow.py | test_generate_handles_llm_error |
| test_utility_endpoints.py | test_google_search_with_num |
| test_utility_endpoints.py | test_overview_with_num |

---

## 3. 分析

### 3.1 `num`パラメータ関連の失敗

以下のテストは`num`パラメータの制限変更(`le=3`)に関連している可能性が高い：

- `test_schemas.py::test_search_utility_request_full`
- `test_utility_endpoints.py::test_google_search_with_num`
- `test_utility_endpoints.py::test_overview_with_num`

**対応**: テストの期待値を`num <= 3`に更新する必要あり

### 3.2 Job Generator V2関連

以下のテストはJob Generator V2の変更に影響を受けている可能性：

- `test_job_generator_v2_integration.py::test_full_workflow_with_mocked_services`
- `test_issue_342_v2_response.py`内の2テスト
- `test_workflow_gen/test_workflow.py::test_default_initialization`
- `test_workflow_gen/test_yaml_generator.py::test_default_initialization`

### 3.3 シナリオテスト

`test_issue_177_scenarios.py`の6つの失敗は、ワークフロー生成ロジックの変更に起因している可能性あり

---

## 4. 推奨アクション

### 優先度: 高
1. [ ] `num`パラメータ制限に関連するテストの修正
2. [ ] Job Generator V2の統合テスト確認

### 優先度: 中
3. [ ] シナリオテストの期待値見直し
4. [ ] 受入テストの環境設定確認

### 優先度: 低
5. [ ] 警告(130件)の確認・対応

---

## 5. 備考

- 全3827テスト中、25件(0.65%)が失敗
- 多くの失敗は`num`パラメータのスキーマ制限変更に起因すると推定
- 受入テストのERRORは環境依存の可能性が高い
