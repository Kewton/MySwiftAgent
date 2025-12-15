<script lang="ts">
	// Pattern A: Professional Blue - Enhanced MVP with full functionality
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';

	// ===== COMPREHENSIVE MOCK DATA =====

	// Multiple Projects
	const projects = [
		{
			id: 'proj_001',
			name: 'Default Project',
			description: 'AI workflow automation project',
			workbenchCount: 5,
			createdAt: '2024-11-01T00:00:00Z'
		},
		{
			id: 'proj_002',
			name: 'Marketing Automation',
			description: 'Content generation and scheduling',
			workbenchCount: 3,
			createdAt: '2024-11-15T00:00:00Z'
		},
		{
			id: 'proj_003',
			name: 'Data Pipeline',
			description: 'ETL and data processing workflows',
			workbenchCount: 4,
			createdAt: '2024-12-01T00:00:00Z'
		}
	];

	// Workbenches by project
	const workbenchesByProject: Record<
		string,
		Array<{
			id: string;
			name: string;
			status: string;
			lastRunAt: string | null;
			description: string;
		}>
	> = {
		proj_001: [
			{
				id: 'wb_001',
				name: 'Email Summarizer',
				status: 'active',
				lastRunAt: '2024-12-14T12:00:00Z',
				description: 'Gmailの未読メールを要約してSlackに投稿'
			},
			{
				id: 'wb_002',
				name: 'Report Generator',
				status: 'active',
				lastRunAt: '2024-12-13T10:00:00Z',
				description: 'Weekly sales report generation'
			},
			{
				id: 'wb_003',
				name: 'Data Pipeline',
				status: 'idle',
				lastRunAt: '2024-12-10T08:00:00Z',
				description: 'ETL pipeline for customer data'
			},
			{
				id: 'wb_004',
				name: 'Slack Bot',
				status: 'inactive',
				lastRunAt: null,
				description: 'Interactive Slack assistant'
			},
			{
				id: 'wb_005',
				name: 'Invoice Processor',
				status: 'active',
				lastRunAt: '2024-12-14T09:30:00Z',
				description: 'OCR and invoice data extraction'
			}
		],
		proj_002: [
			{
				id: 'wb_006',
				name: 'Blog Writer',
				status: 'active',
				lastRunAt: '2024-12-14T11:00:00Z',
				description: 'AI-powered blog content generation'
			},
			{
				id: 'wb_007',
				name: 'Social Scheduler',
				status: 'active',
				lastRunAt: '2024-12-14T08:00:00Z',
				description: 'Multi-platform social media scheduling'
			},
			{
				id: 'wb_008',
				name: 'Newsletter Builder',
				status: 'idle',
				lastRunAt: '2024-12-12T14:00:00Z',
				description: 'Weekly newsletter composition'
			}
		],
		proj_003: [
			{
				id: 'wb_009',
				name: 'Customer ETL',
				status: 'active',
				lastRunAt: '2024-12-14T06:00:00Z',
				description: 'Customer data transformation'
			},
			{
				id: 'wb_010',
				name: 'Analytics Sync',
				status: 'active',
				lastRunAt: '2024-12-14T07:00:00Z',
				description: 'Sync data to analytics platforms'
			},
			{
				id: 'wb_011',
				name: 'Backup Manager',
				status: 'active',
				lastRunAt: '2024-12-14T03:00:00Z',
				description: 'Automated database backups'
			},
			{
				id: 'wb_012',
				name: 'Log Processor',
				status: 'idle',
				lastRunAt: '2024-12-13T23:00:00Z',
				description: 'Log aggregation and analysis'
			}
		]
	};

	// Requirements versions
	const requirementVersions = [
		{
			id: 'rv_v5',
			version: 5,
			status: 'active',
			content: `## Email Summarizer v5

### 概要
Gmailの未読メールを自動で取得し、AI要約を生成してSlackに投稿するワークフロー。

### Input
- **Gmail API**: 未読メール取得 (過去24時間)
- **フィルター**: 重要度高のみ
- **認証**: OAuth2.0

### Process
1. **fetchAgent**: Gmail APIからメール取得
2. **filterAgent**: 重要度でフィルタリング
3. **geminiAgent**: 内容分析・要約生成
4. **validationAgent**: 要約品質チェック (スコア0.7以上)
5. **fetchAgent**: Slack API経由で投稿

### Output
- **投稿先**: Slack #email-summary
- **要約形式**: 構造化マークダウン
- **含む情報**:
  - 送信者
  - 件名
  - 要約 (3行以内)
  - アクションアイテム
  - 緊急度タグ

### 制約事項
- 最大処理メール数: 100件/実行
- 要約生成タイムアウト: 30秒
- Slack投稿レート制限: 1件/秒`,
			changeSummary: '重要度フィルターと品質チェックを追加',
			createdAt: '2024-12-14T10:00:00Z'
		},
		{
			id: 'rv_v4',
			version: 4,
			status: 'deprecated',
			content: `## Email Summarizer v4

### 概要
Gmailの未読メールを取得し、要約をSlackに投稿。

### Input
- **Gmail API**: 未読メール取得 (過去24時間)
- **認証**: OAuth2.0

### Process
1. **fetchAgent**: Gmail APIからメール取得
2. **geminiAgent**: 内容分析・要約生成
3. **fetchAgent**: Slack API経由で投稿

### Output
- **投稿先**: Slack #email-summary
- **要約形式**: マークダウン形式
- **含む情報**:
  - 送信者
  - 件名
  - 要約

### 変更点 (v3からの改善)
- Slack投稿時のフォーマットを改善
- スレッド投稿に対応`,
			changeSummary: 'Slack投稿形式を改善',
			createdAt: '2024-12-13T10:00:00Z'
		},
		{
			id: 'rv_v3',
			version: 3,
			status: 'deprecated',
			content: `## Email Summarizer v3

### 概要
Gmailの未読メールを取得し、要約をSlackに通知。

### Input
- **Gmail API**: 未読メール取得 (過去24時間)

### Process
1. **fetchAgent**: Gmail APIからメール取得
2. **geminiAgent**: 要約生成
3. **fetchAgent**: Slack通知

### Output
- **投稿先**: Slack #general
- **形式**: テキスト

### 変更点 (v2からの改善)
- Slack投稿機能を追加
- チャンネル指定が可能に`,
			changeSummary: 'Slack投稿機能を追加',
			createdAt: '2024-12-12T10:00:00Z'
		},
		{
			id: 'rv_v2',
			version: 2,
			status: 'deprecated',
			content: `## Email Summarizer v2

### 概要
Gmailの未読メールを取得し、要約を生成。

### Input
- **Gmail API**: 未読メール取得

### Process
1. **fetchAgent**: Gmail APIからメール取得
2. **geminiAgent**: 要約生成

### Output
- **形式**: JSON
- **フィールド**: subject, from, summary

### 変更点 (v1からの改善)
- 要約フォーマットを構造化
- 複数メールの一括処理に対応`,
			changeSummary: '要約フォーマットを改善',
			createdAt: '2024-12-11T10:00:00Z'
		},
		{
			id: 'rv_v1',
			version: 1,
			status: 'deprecated',
			content: `## Email Summarizer v1

### 概要
Gmailの未読メールを取得し、簡単な要約を生成する初期バージョン。

### Input
- **Gmail API**: 未読メール取得

### Process
1. **fetchAgent**: メール取得
2. **geminiAgent**: 要約生成

### Output
- **形式**: プレーンテキスト

### 備考
- 初期プロトタイプ
- 単一メールのみ対応`,
			changeSummary: '初期バージョン',
			createdAt: '2024-12-10T10:00:00Z'
		}
	];

	// Job versions with vN.M format (N=RequirementVersion, M=GenerationCount)
	// vN.M: N -> 要件定義バージョン, M -> Job生成ワークフロー実行回数
	const jobVersions = [
		{
			id: 'jv_v5.2',
			majorVersion: 5,
			minorVersion: 2,
			versionLabel: 'v5.2',
			status: 'active',
			sourceRequirementVersionId: 'rv_v5',
			generatedAt: '2024-12-14T11:00:00Z',
			generationReason: 'LLMモデル更新後の再生成',
			taskBreakdown: [
				{
					id: 't1',
					name: 'Initialize Gmail Connection',
					description: 'OAuth2認証でGmail APIに接続',
					agentType: 'fetchAgent',
					status: 'completed',
					estimatedDuration: '5s',
					inputInterface: {
						type: 'object',
						properties: {
							credentials_path: { type: 'string', description: 'OAuth2認証情報のパス' },
							scopes: { type: 'array', items: { type: 'string' }, description: 'Gmail APIスコープ' }
						},
						required: ['credentials_path']
					},
					outputInterface: {
						type: 'object',
						properties: {
							connection_id: { type: 'string', description: '接続ID' },
							authenticated: { type: 'boolean', description: '認証成功フラグ' },
							user_email: { type: 'string', description: '認証ユーザーのメールアドレス' }
						}
					}
				},
				{
					id: 't2',
					name: 'Fetch Unread Emails',
					description: '過去24時間の未読メールを取得',
					agentType: 'fetchAgent',
					status: 'completed',
					estimatedDuration: '10s',
					inputInterface: {
						type: 'object',
						properties: {
							connection_id: { type: 'string', description: '接続ID' },
							hours_back: { type: 'number', description: '取得期間（時間）', default: 24 },
							max_results: { type: 'number', description: '最大取得件数', default: 100 }
						},
						required: ['connection_id']
					},
					outputInterface: {
						type: 'object',
						properties: {
							emails: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										id: { type: 'string' },
										subject: { type: 'string' },
										from: { type: 'string' },
										date: { type: 'string' },
										snippet: { type: 'string' }
									}
								},
								description: '未読メール一覧'
							},
							total_count: { type: 'number', description: '取得件数' }
						}
					}
				},
				{
					id: 't3',
					name: 'Filter by Importance',
					description: '重要度高のメールをフィルタリング',
					agentType: 'filterAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							emails: { type: 'array', description: 'メール一覧' },
							importance_threshold: {
								type: 'string',
								enum: ['high', 'medium', 'low'],
								description: '重要度閾値'
							}
						},
						required: ['emails']
					},
					outputInterface: {
						type: 'object',
						properties: {
							filtered_emails: { type: 'array', description: 'フィルタ後メール' },
							filtered_count: { type: 'number', description: 'フィルタ後件数' },
							removed_count: { type: 'number', description: '除外件数' }
						}
					}
				},
				{
					id: 't4',
					name: 'Extract Email Bodies',
					description: 'メール本文をプレーンテキストに変換',
					agentType: 'parseAgent',
					status: 'completed',
					estimatedDuration: '3s',
					inputInterface: {
						type: 'object',
						properties: {
							filtered_emails: { type: 'array', description: 'フィルタ済みメール' },
							strip_html: { type: 'boolean', default: true, description: 'HTMLタグ除去' }
						},
						required: ['filtered_emails']
					},
					outputInterface: {
						type: 'object',
						properties: {
							parsed_emails: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										id: { type: 'string' },
										subject: { type: 'string' },
										body_text: { type: 'string' },
										word_count: { type: 'number' }
									}
								},
								description: 'パース済みメール'
							}
						}
					}
				},
				{
					id: 't5',
					name: 'Batch Emails for Processing',
					description: '処理効率のためメールをバッチ化',
					agentType: 'batchAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							parsed_emails: { type: 'array', description: 'パース済みメール' },
							batch_size: { type: 'number', default: 5, description: 'バッチサイズ' }
						},
						required: ['parsed_emails']
					},
					outputInterface: {
						type: 'object',
						properties: {
							batches: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										batch_id: { type: 'string' },
										emails: { type: 'array' },
										size: { type: 'number' }
									}
								},
								description: 'バッチ一覧'
							},
							total_batches: { type: 'number', description: 'バッチ総数' }
						}
					}
				},
				{
					id: 't6',
					name: 'Analyze Email Content',
					description: 'メール内容の感情分析と分類',
					agentType: 'geminiAgent',
					status: 'completed',
					estimatedDuration: '15s',
					inputInterface: {
						type: 'object',
						properties: {
							batches: { type: 'array', description: 'メールバッチ' },
							analysis_types: {
								type: 'array',
								items: { type: 'string', enum: ['sentiment', 'category', 'urgency'] },
								description: '分析タイプ'
							}
						},
						required: ['batches']
					},
					outputInterface: {
						type: 'object',
						properties: {
							analyzed_emails: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										id: { type: 'string' },
										sentiment: { type: 'string', enum: ['positive', 'neutral', 'negative'] },
										category: { type: 'string' },
										urgency: { type: 'string', enum: ['high', 'medium', 'low'] }
									}
								},
								description: '分析結果'
							}
						}
					}
				},
				{
					id: 't7',
					name: 'Generate Summary Draft',
					description: '各メールの要約ドラフトを生成',
					agentType: 'geminiAgent',
					status: 'completed',
					estimatedDuration: '20s',
					inputInterface: {
						type: 'object',
						properties: {
							analyzed_emails: { type: 'array', description: '分析済みメール' },
							summary_length: {
								type: 'string',
								enum: ['short', 'medium', 'long'],
								default: 'medium',
								description: '要約長さ'
							},
							language: { type: 'string', default: 'ja', description: '出力言語' }
						},
						required: ['analyzed_emails']
					},
					outputInterface: {
						type: 'object',
						properties: {
							summaries: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										email_id: { type: 'string' },
										summary: { type: 'string' },
										key_points: { type: 'array', items: { type: 'string' } }
									}
								},
								description: '要約一覧'
							}
						}
					}
				},
				{
					id: 't8',
					name: 'Extract Action Items',
					description: 'アクションアイテムを抽出',
					agentType: 'geminiAgent',
					status: 'completed',
					estimatedDuration: '10s',
					inputInterface: {
						type: 'object',
						properties: {
							summaries: { type: 'array', description: '要約一覧' },
							extract_deadlines: { type: 'boolean', default: true, description: '期限抽出' }
						},
						required: ['summaries']
					},
					outputInterface: {
						type: 'object',
						properties: {
							action_items: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										id: { type: 'string' },
										action: { type: 'string' },
										source_email_id: { type: 'string' },
										deadline: { type: 'string', nullable: true },
										assignee: { type: 'string', nullable: true }
									}
								},
								description: 'アクションアイテム'
							}
						}
					}
				},
				{
					id: 't9',
					name: 'Prioritize Items',
					description: '緊急度に基づく優先順位付け',
					agentType: 'geminiAgent',
					status: 'completed',
					estimatedDuration: '5s',
					inputInterface: {
						type: 'object',
						properties: {
							action_items: { type: 'array', description: 'アクションアイテム' },
							priority_factors: {
								type: 'array',
								items: { type: 'string' },
								default: ['deadline', 'urgency', 'sender_importance'],
								description: '優先度要因'
							}
						},
						required: ['action_items']
					},
					outputInterface: {
						type: 'object',
						properties: {
							prioritized_items: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										id: { type: 'string' },
										action: { type: 'string' },
										priority: { type: 'number', minimum: 1, maximum: 5 },
										priority_reason: { type: 'string' }
									}
								},
								description: '優先順位付きアイテム'
							}
						}
					}
				},
				{
					id: 't10',
					name: 'Validate Summary Quality',
					description: '要約の品質スコアを計算',
					agentType: 'validationAgent',
					status: 'completed',
					estimatedDuration: '3s',
					inputInterface: {
						type: 'object',
						properties: {
							summaries: { type: 'array', description: '要約一覧' },
							quality_threshold: { type: 'number', default: 0.7, description: '品質閾値' }
						},
						required: ['summaries']
					},
					outputInterface: {
						type: 'object',
						properties: {
							validated_summaries: {
								type: 'array',
								items: {
									type: 'object',
									properties: {
										email_id: { type: 'string' },
										quality_score: { type: 'number' },
										passed: { type: 'boolean' }
									}
								},
								description: '検証結果'
							},
							average_quality: { type: 'number', description: '平均品質スコア' }
						}
					}
				},
				{
					id: 't11',
					name: 'Check for Duplicates',
					description: '重複コンテンツのチェック',
					agentType: 'validationAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							validated_summaries: { type: 'array', description: '検証済み要約' },
							similarity_threshold: { type: 'number', default: 0.85, description: '類似度閾値' }
						},
						required: ['validated_summaries']
					},
					outputInterface: {
						type: 'object',
						properties: {
							unique_summaries: { type: 'array', description: '重複除去済み要約' },
							duplicates_found: { type: 'number', description: '重複件数' },
							duplicate_pairs: { type: 'array', description: '重複ペア' }
						}
					}
				},
				{
					id: 't12',
					name: 'Format as Markdown',
					description: 'Slack用マークダウン形式に変換',
					agentType: 'formatAgent',
					status: 'completed',
					estimatedDuration: '3s',
					inputInterface: {
						type: 'object',
						properties: {
							unique_summaries: { type: 'array', description: '重複除去済み要約' },
							prioritized_items: { type: 'array', description: '優先順位付きアイテム' },
							format_style: {
								type: 'string',
								enum: ['slack', 'github', 'standard'],
								default: 'slack',
								description: 'フォーマットスタイル'
							}
						},
						required: ['unique_summaries', 'prioritized_items']
					},
					outputInterface: {
						type: 'object',
						properties: {
							markdown_content: { type: 'string', description: 'マークダウンコンテンツ' },
							sections: { type: 'array', items: { type: 'string' }, description: 'セクション一覧' }
						}
					}
				},
				{
					id: 't13',
					name: 'Add Metadata Headers',
					description: 'タイムスタンプと統計情報を追加',
					agentType: 'formatAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							markdown_content: { type: 'string', description: 'マークダウンコンテンツ' },
							include_stats: { type: 'boolean', default: true, description: '統計情報含む' },
							timezone: { type: 'string', default: 'Asia/Tokyo', description: 'タイムゾーン' }
						},
						required: ['markdown_content']
					},
					outputInterface: {
						type: 'object',
						properties: {
							final_content: { type: 'string', description: '最終コンテンツ' },
							metadata: {
								type: 'object',
								properties: {
									generated_at: { type: 'string' },
									email_count: { type: 'number' },
									action_item_count: { type: 'number' }
								},
								description: 'メタデータ'
							}
						}
					}
				},
				{
					id: 't14',
					name: 'Resolve Slack Channel',
					description: '投稿先チャンネルIDを解決',
					agentType: 'fetchAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							channel_name: {
								type: 'string',
								default: '#email-summary',
								description: 'チャンネル名'
							},
							workspace_id: { type: 'string', description: 'ワークスペースID' }
						},
						required: ['channel_name']
					},
					outputInterface: {
						type: 'object',
						properties: {
							channel_id: { type: 'string', description: 'チャンネルID' },
							channel_name: { type: 'string', description: 'チャンネル名' },
							is_private: { type: 'boolean', description: 'プライベートフラグ' }
						}
					}
				},
				{
					id: 't15',
					name: 'Post Summary to Slack',
					description: 'Slack Webhookで要約を投稿',
					agentType: 'fetchAgent',
					status: 'completed',
					estimatedDuration: '3s',
					inputInterface: {
						type: 'object',
						properties: {
							channel_id: { type: 'string', description: 'チャンネルID' },
							final_content: { type: 'string', description: '投稿コンテンツ' },
							webhook_url: { type: 'string', description: 'Webhook URL' }
						},
						required: ['channel_id', 'final_content']
					},
					outputInterface: {
						type: 'object',
						properties: {
							message_ts: { type: 'string', description: 'メッセージタイムスタンプ' },
							permalink: { type: 'string', description: 'パーマリンク' },
							posted: { type: 'boolean', description: '投稿成功フラグ' }
						}
					}
				},
				{
					id: 't16',
					name: 'Post Action Items Thread',
					description: 'アクションアイテムをスレッドに投稿',
					agentType: 'fetchAgent',
					status: 'completed',
					estimatedDuration: '3s',
					inputInterface: {
						type: 'object',
						properties: {
							channel_id: { type: 'string', description: 'チャンネルID' },
							message_ts: { type: 'string', description: '親メッセージTS' },
							prioritized_items: { type: 'array', description: 'アクションアイテム' }
						},
						required: ['channel_id', 'message_ts', 'prioritized_items']
					},
					outputInterface: {
						type: 'object',
						properties: {
							thread_ts: { type: 'string', description: 'スレッドTS' },
							replies_count: { type: 'number', description: '返信数' }
						}
					}
				},
				{
					id: 't17',
					name: 'Update Read Status',
					description: '処理済みメールを既読にマーク',
					agentType: 'fetchAgent',
					status: 'completed',
					estimatedDuration: '5s',
					inputInterface: {
						type: 'object',
						properties: {
							connection_id: { type: 'string', description: '接続ID' },
							email_ids: { type: 'array', items: { type: 'string' }, description: 'メールID一覧' },
							mark_as: {
								type: 'string',
								enum: ['read', 'archived'],
								default: 'read',
								description: 'マーク種別'
							}
						},
						required: ['connection_id', 'email_ids']
					},
					outputInterface: {
						type: 'object',
						properties: {
							updated_count: { type: 'number', description: '更新件数' },
							failed_ids: { type: 'array', items: { type: 'string' }, description: '失敗ID' }
						}
					}
				},
				{
					id: 't18',
					name: 'Log Execution Metrics',
					description: '実行メトリクスをログに記録',
					agentType: 'logAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							metrics: {
								type: 'object',
								properties: {
									total_emails: { type: 'number' },
									processed_emails: { type: 'number' },
									execution_time_ms: { type: 'number' }
								},
								description: '実行メトリクス'
							},
							log_level: {
								type: 'string',
								enum: ['debug', 'info', 'warn'],
								default: 'info',
								description: 'ログレベル'
							}
						},
						required: ['metrics']
					},
					outputInterface: {
						type: 'object',
						properties: {
							log_id: { type: 'string', description: 'ログID' },
							logged_at: { type: 'string', description: 'ログ日時' }
						}
					}
				},
				{
					id: 't19',
					name: 'Send Completion Notification',
					description: '完了通知を送信',
					agentType: 'notifyAgent',
					status: 'completed',
					estimatedDuration: '2s',
					inputInterface: {
						type: 'object',
						properties: {
							notification_type: {
								type: 'string',
								enum: ['email', 'slack', 'webhook'],
								default: 'slack',
								description: '通知タイプ'
							},
							recipients: { type: 'array', items: { type: 'string' }, description: '受信者' },
							summary: { type: 'string', description: '通知サマリー' }
						},
						required: ['notification_type', 'summary']
					},
					outputInterface: {
						type: 'object',
						properties: {
							sent: { type: 'boolean', description: '送信成功' },
							notification_id: { type: 'string', description: '通知ID' }
						}
					}
				},
				{
					id: 't20',
					name: 'Cleanup Temporary Data',
					description: '一時データをクリーンアップ',
					agentType: 'cleanupAgent',
					status: 'completed',
					estimatedDuration: '1s',
					inputInterface: {
						type: 'object',
						properties: {
							cleanup_targets: {
								type: 'array',
								items: { type: 'string', enum: ['cache', 'temp_files', 'session'] },
								description: 'クリーンアップ対象'
							},
							force: { type: 'boolean', default: false, description: '強制削除' }
						},
						required: ['cleanup_targets']
					},
					outputInterface: {
						type: 'object',
						properties: {
							cleaned_items: { type: 'number', description: '削除アイテム数' },
							freed_bytes: { type: 'number', description: '解放バイト数' }
						}
					}
				}
			]
		},
		{
			id: 'jv_v5.1',
			majorVersion: 5,
			minorVersion: 1,
			versionLabel: 'v5.1',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v5',
			generatedAt: '2024-12-14T09:00:00Z',
			generationReason: '要件v5からの初回生成',
			taskBreakdown: Array.from({ length: 18 }, (_, i) => ({
				id: `t51_${i + 1}`,
				name: `Task ${i + 1} (v5.1)`,
				description: `要件v5・生成1回目のタスク ${i + 1}`,
				agentType: i % 3 === 0 ? 'fetchAgent' : i % 3 === 1 ? 'geminiAgent' : 'validationAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 2}s`
			}))
		},
		{
			id: 'jv_v4.3',
			majorVersion: 4,
			minorVersion: 3,
			versionLabel: 'v4.3',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v4',
			generatedAt: '2024-12-13T15:00:00Z',
			generationReason: 'Agent定義ファイル更新後の再生成',
			taskBreakdown: Array.from({ length: 15 }, (_, i) => ({
				id: `t43_${i + 1}`,
				name: `Task ${i + 1} (v4.3)`,
				description: `要件v4・生成3回目のタスク ${i + 1}`,
				agentType: i % 3 === 0 ? 'fetchAgent' : i % 3 === 1 ? 'geminiAgent' : 'validationAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 2}s`
			}))
		},
		{
			id: 'jv_v4.2',
			majorVersion: 4,
			minorVersion: 2,
			versionLabel: 'v4.2',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v4',
			generatedAt: '2024-12-13T11:00:00Z',
			generationReason: 'プロンプト調整後の再生成',
			taskBreakdown: Array.from({ length: 14 }, (_, i) => ({
				id: `t42_${i + 1}`,
				name: `Task ${i + 1} (v4.2)`,
				description: `要件v4・生成2回目のタスク ${i + 1}`,
				agentType: i % 2 === 0 ? 'fetchAgent' : 'geminiAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 2}s`
			}))
		},
		{
			id: 'jv_v4.1',
			majorVersion: 4,
			minorVersion: 1,
			versionLabel: 'v4.1',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v4',
			generatedAt: '2024-12-13T08:00:00Z',
			generationReason: '要件v4からの初回生成',
			taskBreakdown: Array.from({ length: 13 }, (_, i) => ({
				id: `t41_${i + 1}`,
				name: `Task ${i + 1} (v4.1)`,
				description: `要件v4・生成1回目のタスク ${i + 1}`,
				agentType: i % 2 === 0 ? 'fetchAgent' : 'geminiAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 2}s`
			}))
		},
		{
			id: 'jv_v3.2',
			majorVersion: 3,
			minorVersion: 2,
			versionLabel: 'v3.2',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v3',
			generatedAt: '2024-12-12T14:00:00Z',
			generationReason: 'LLM非決定性による出力改善のための再生成',
			taskBreakdown: Array.from({ length: 12 }, (_, i) => ({
				id: `t32_${i + 1}`,
				name: `Task ${i + 1} (v3.2)`,
				description: `要件v3・生成2回目のタスク ${i + 1}`,
				agentType: i % 2 === 0 ? 'fetchAgent' : 'geminiAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 2}s`
			}))
		},
		{
			id: 'jv_v3.1',
			majorVersion: 3,
			minorVersion: 1,
			versionLabel: 'v3.1',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v3',
			generatedAt: '2024-12-12T11:00:00Z',
			generationReason: '要件v3からの初回生成',
			taskBreakdown: Array.from({ length: 11 }, (_, i) => ({
				id: `t31_${i + 1}`,
				name: `Task ${i + 1} (v3.1)`,
				description: `要件v3・生成1回目のタスク ${i + 1}`,
				agentType: 'fetchAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 3}s`
			}))
		},
		{
			id: 'jv_v2.1',
			majorVersion: 2,
			minorVersion: 1,
			versionLabel: 'v2.1',
			status: 'deprecated',
			sourceRequirementVersionId: 'rv_v2',
			generatedAt: '2024-12-11T11:00:00Z',
			generationReason: '要件v2からの初回生成',
			taskBreakdown: Array.from({ length: 8 }, (_, i) => ({
				id: `t21_${i + 1}`,
				name: `Task ${i + 1} (v2.1)`,
				description: `要件v2・生成1回目のタスク ${i + 1}`,
				agentType: 'fetchAgent',
				status: 'completed',
				estimatedDuration: `${(i + 1) * 3}s`
			}))
		}
	];

	// All workbenches flat list for run/schedule assignment
	const allWorkbenchesFlat = [
		{
			id: 'wb_001',
			name: 'Email Summarizer',
			projectId: 'proj_001',
			projectName: 'Default Project'
		},
		{
			id: 'wb_002',
			name: 'Report Generator',
			projectId: 'proj_001',
			projectName: 'Default Project'
		},
		{ id: 'wb_003', name: 'Data Pipeline', projectId: 'proj_001', projectName: 'Default Project' },
		{
			id: 'wb_006',
			name: 'Blog Writer',
			projectId: 'proj_002',
			projectName: 'Marketing Automation'
		},
		{
			id: 'wb_007',
			name: 'Social Scheduler',
			projectId: 'proj_002',
			projectName: 'Marketing Automation'
		},
		{ id: 'wb_009', name: 'Customer ETL', projectId: 'proj_003', projectName: 'Data Pipeline' },
		{ id: 'wb_010', name: 'Analytics Sync', projectId: 'proj_003', projectName: 'Data Pipeline' }
	];

	// Generate 150 runs with various statuses using vN.M job versions
	function generateRuns(count: number) {
		const statuses = [
			'success',
			'success',
			'success',
			'success',
			'success',
			'success',
			'failed',
			'running'
		];
		const runs = [];
		const now = new Date('2024-12-14T14:00:00Z');

		// Job version mapping for runs (vN.M format)
		// Recent runs use latest versions, older runs use older versions
		const jobVersionMapping = [
			{ range: [0, 30], versionId: 'jv_v5.2', versionLabel: 'v5.2' },
			{ range: [30, 50], versionId: 'jv_v5.1', versionLabel: 'v5.1' },
			{ range: [50, 70], versionId: 'jv_v4.3', versionLabel: 'v4.3' },
			{ range: [70, 90], versionId: 'jv_v4.2', versionLabel: 'v4.2' },
			{ range: [90, 110], versionId: 'jv_v4.1', versionLabel: 'v4.1' },
			{ range: [110, 130], versionId: 'jv_v3.2', versionLabel: 'v3.2' },
			{ range: [130, 145], versionId: 'jv_v3.1', versionLabel: 'v3.1' },
			{ range: [145, 150], versionId: 'jv_v2.1', versionLabel: 'v2.1' }
		];

		for (let i = 0; i < count; i++) {
			const status = i === 0 ? 'running' : statuses[Math.floor(Math.random() * statuses.length)];
			const startTime = new Date(now.getTime() - i * 15 * 60 * 1000); // 15 min intervals

			// Find appropriate job version based on run index
			const versionInfo =
				jobVersionMapping.find((m) => i >= m.range[0] && i < m.range[1]) ||
				jobVersionMapping[jobVersionMapping.length - 1];
			const duration =
				status === 'running'
					? null
					: `${Math.floor(Math.random() * 3) + 1}m ${Math.floor(Math.random() * 60)}s`;

			// Assign workbench (most runs to Email Summarizer, some to others)
			const workbench =
				i < 100 ? allWorkbenchesFlat[0] : allWorkbenchesFlat[i % allWorkbenchesFlat.length];

			runs.push({
				id: `run_${String(i + 1).padStart(4, '0')}`,
				workbenchId: workbench.id,
				workbenchName: workbench.name,
				projectId: workbench.projectId,
				projectName: workbench.projectName,
				jobVersionId: versionInfo.versionId,
				jobVersionLabel: versionInfo.versionLabel,
				status,
				startedAt: startTime.toISOString(),
				completedAt:
					status === 'running'
						? null
						: new Date(startTime.getTime() + (Math.random() * 180000 + 60000)).toISOString(),
				duration,
				progress:
					status === 'running'
						? Math.floor(Math.random() * 80) + 10
						: status === 'success'
							? 100
							: Math.floor(Math.random() * 90),
				currentTask: status === 'running' ? `t${Math.floor(Math.random() * 20) + 1}` : null,
				errorMessage:
					status === 'failed'
						? [
								'Gmail API rate limit exceeded',
								'Slack webhook timeout',
								'Network connection failed',
								'Authentication expired'
							][Math.floor(Math.random() * 4)]
						: null,
				traceId: `trace_${Math.random().toString(36).substr(2, 12)}`,
				tasksCompleted:
					status === 'success'
						? 20
						: status === 'running'
							? Math.floor(Math.random() * 18) + 1
							: Math.floor(Math.random() * 15),
				totalTasks: 20
			});
		}
		return runs;
	}

	const allRuns = generateRuns(150);

	// Schedules (using vN.M job version format) - with workbench association
	const schedules = [
		{
			id: 'sched_001',
			name: 'Daily Morning Summary',
			workbenchId: 'wb_001',
			workbenchName: 'Email Summarizer',
			projectId: 'proj_001',
			projectName: 'Default Project',
			targetJobVersionId: 'jv_v5.2',
			targetJobVersionLabel: 'v5.2',
			cronExpression: '0 8 * * *',
			isEnabled: true,
			nextRunAt: '2024-12-15T08:00:00Z',
			lastRunAt: '2024-12-14T08:00:00Z'
		},
		{
			id: 'sched_002',
			name: 'Weekly Digest',
			workbenchId: 'wb_001',
			workbenchName: 'Email Summarizer',
			projectId: 'proj_001',
			projectName: 'Default Project',
			targetJobVersionId: 'jv_v5.2',
			targetJobVersionLabel: 'v5.2',
			cronExpression: '0 10 * * 1',
			isEnabled: true,
			nextRunAt: '2024-12-16T10:00:00Z',
			lastRunAt: '2024-12-09T10:00:00Z'
		},
		{
			id: 'sched_003',
			name: 'Hourly Check',
			workbenchId: 'wb_002',
			workbenchName: 'Report Generator',
			projectId: 'proj_001',
			projectName: 'Default Project',
			targetJobVersionId: 'jv_v4.3',
			targetJobVersionLabel: 'v4.3',
			cronExpression: '0 * * * *',
			isEnabled: false,
			nextRunAt: null,
			lastRunAt: '2024-12-13T15:00:00Z'
		},
		{
			id: 'sched_004',
			name: 'End of Day Report',
			workbenchId: 'wb_002',
			workbenchName: 'Report Generator',
			projectId: 'proj_001',
			projectName: 'Default Project',
			targetJobVersionId: 'jv_v5.2',
			targetJobVersionLabel: 'v5.2',
			cronExpression: '0 18 * * 1-5',
			isEnabled: true,
			nextRunAt: '2024-12-16T18:00:00Z',
			lastRunAt: '2024-12-13T18:00:00Z'
		},
		{
			id: 'sched_005',
			name: 'Daily ETL Sync',
			workbenchId: 'wb_009',
			workbenchName: 'Customer ETL',
			projectId: 'proj_003',
			projectName: 'Data Pipeline',
			targetJobVersionId: 'jv_v5.2',
			targetJobVersionLabel: 'v5.2',
			cronExpression: '0 6 * * *',
			isEnabled: true,
			nextRunAt: '2024-12-15T06:00:00Z',
			lastRunAt: '2024-12-14T06:00:00Z'
		},
		{
			id: 'sched_006',
			name: 'Blog Publishing',
			workbenchId: 'wb_006',
			workbenchName: 'Blog Writer',
			projectId: 'proj_002',
			projectName: 'Marketing Automation',
			targetJobVersionId: 'jv_v5.1',
			targetJobVersionLabel: 'v5.1',
			cronExpression: '0 9 * * 1,3,5',
			isEnabled: true,
			nextRunAt: '2024-12-16T09:00:00Z',
			lastRunAt: '2024-12-13T09:00:00Z'
		}
	];

	// ===== STATE MANAGEMENT =====
	const baseUrl = '/mockups/feature-279/pattern-a';

	// Current selections from URL
	const currentView = $derived($page.url.searchParams.get('view') || 'workbenches');
	const currentTab = $derived($page.url.searchParams.get('tab') || 'review');
	const selectedProjectId = $derived($page.url.searchParams.get('project') || 'proj_001');
	const selectedWorkbenchId = $derived($page.url.searchParams.get('workbench') || 'wb_001');
	const selectedJobVersionId = $derived($page.url.searchParams.get('jobVersion') || 'jv_v5.2');
	const selectedRunId = $derived($page.url.searchParams.get('run'));
	const selectedRequirementVersionId = $derived(
		$page.url.searchParams.get('reqVersion') || 'rv_v5'
	);
	const runsPage = $derived(parseInt($page.url.searchParams.get('runsPage') || '1'));

	// Derived data
	const currentProject = $derived(projects.find((p) => p.id === selectedProjectId) || projects[0]);
	const currentWorkbenches = $derived(workbenchesByProject[selectedProjectId] || []);
	const currentWorkbench = $derived(
		currentWorkbenches.find((w) => w.id === selectedWorkbenchId) || currentWorkbenches[0]
	);
	const activeRequirement = $derived(requirementVersions.find((r) => r.status === 'active'));
	const selectedJobVersion = $derived(
		jobVersions.find((j) => j.id === selectedJobVersionId) || jobVersions[0]
	);
	const selectedRun = $derived(selectedRunId ? allRuns.find((r) => r.id === selectedRunId) : null);
	const selectedRequirementVersion = $derived(
		requirementVersions.find((r) => r.id === selectedRequirementVersionId) || requirementVersions[0]
	);

	// Filter runs and schedules by selected project
	const projectRuns = $derived(allRuns.filter((r) => r.projectId === selectedProjectId));
	const projectSchedules = $derived(schedules.filter((s) => s.projectId === selectedProjectId));

	// Pagination (based on filtered project runs)
	const runsPerPage = 15;
	const totalRunsPages = $derived(Math.ceil(projectRuns.length / runsPerPage));
	const paginatedRuns = $derived(
		projectRuns.slice((runsPage - 1) * runsPerPage, runsPage * runsPerPage)
	);

	// Stats (based on filtered project runs)
	const runStats = $derived(() => {
		const runs = projectRuns;
		if (runs.length === 0) {
			return { total: 0, success: 0, failed: 0, successRate: 0, avgDuration: '0m 0s' };
		}
		const successRuns = runs.filter((r) => r.status === 'success').length;
		const failedRuns = runs.filter((r) => r.status === 'failed').length;
		const runsWithDuration = runs.filter((r) => r.duration);
		const avgDuration =
			runsWithDuration.length > 0
				? Math.floor(
						runsWithDuration.reduce((acc, r) => {
							const match = r.duration?.match(/(\d+)m\s*(\d+)s/);
							return acc + (match ? parseInt(match[1]) * 60 + parseInt(match[2]) : 0);
						}, 0) / runsWithDuration.length
					)
				: 0;
		return {
			total: runs.length,
			success: successRuns,
			failed: failedRuns,
			successRate: runs.length > 0 ? Math.round((successRuns / runs.length) * 100) : 0,
			avgDuration: `${Math.floor(avgDuration / 60)}m ${avgDuration % 60}s`
		};
	});

	// Modal states
	let showProjectModal = $state(false);
	let showWorkbenchModal = $state(false);
	let showProjectDropdown = $state(false);
	let showGenerateConfirm = $state(false);
	let newProjectName = $state('');
	let newWorkbenchName = $state('');
	let newWorkbenchDesc = $state('');
	let taskExpanded = $state<Record<string, boolean>>({});
	let selectedTaskId = $state<string | null>(null);
	let requirementsViewMode = $state<'edit' | 'preview'>('edit');
	let editedContent = $state<string>('');

	// Workbench edit states
	let showWorkbenchEditModal = $state(false);
	let editingWorkbenchName = $state('');
	let editingWorkbenchDesc = $state('');
	let editingWorkbenchStatus = $state('');

	// Initialize workbench edit form
	function openWorkbenchEditModal() {
		if (currentWorkbench) {
			editingWorkbenchName = currentWorkbench.name;
			editingWorkbenchDesc = currentWorkbench.description;
			editingWorkbenchStatus = currentWorkbench.status;
			showWorkbenchEditModal = true;
		}
	}

	// Sync editedContent when selectedRequirementVersion changes
	$effect(() => {
		if (selectedRequirementVersion) {
			editedContent = selectedRequirementVersion.content;
		}
	});

	// Selected task for interface display
	const selectedTask = $derived(
		selectedTaskId && selectedJobVersion
			? selectedJobVersion.taskBreakdown.find((t: { id: string }) => t.id === selectedTaskId)
			: null
	);

	// Function to select a task
	function selectTask(taskId: string) {
		selectedTaskId = selectedTaskId === taskId ? null : taskId;
	}

	// Navigation helpers - use get(page) to avoid scoped subscription error
	function navigateToTab(tabId: string) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('tab', tabId);
		goto(`${baseUrl}?${params.toString()}`);
	}

	function navigateToView(viewId: string) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('view', viewId);
		goto(`${baseUrl}?${params.toString()}`);
	}

	function selectProject(projectId: string) {
		const workbenches = workbenchesByProject[projectId] || [];
		const firstWb = workbenches[0]?.id || '';
		const tab = get(page).url.searchParams.get('tab') || 'review';
		goto(`${baseUrl}?project=${projectId}&workbench=${firstWb}&tab=${tab}`);
		showProjectDropdown = false;
	}

	function selectWorkbench(workbenchId: string) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('workbench', workbenchId);
		goto(`${baseUrl}?${params.toString()}`);
	}

	function selectJobVersion(jobVersionId: string) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('jobVersion', jobVersionId);
		goto(`${baseUrl}?${params.toString()}`);
	}

	function selectRequirementVersion(reqVersionId: string) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('reqVersion', reqVersionId);
		goto(`${baseUrl}?${params.toString()}`);
	}

	function viewRunDetail(runId: string) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('run', runId);
		goto(`${baseUrl}?${params.toString()}`);
	}

	function closeRunDetail() {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.delete('run');
		goto(`${baseUrl}?${params.toString()}`);
	}

	function goToRunsPage(pageNum: number) {
		const params = new URLSearchParams(get(page).url.searchParams);
		params.set('runsPage', pageNum.toString());
		goto(`${baseUrl}?${params.toString()}`);
	}

	// Status helpers
	function getStatusColor(status: string): string {
		const colors: Record<string, string> = {
			active: '#22c55e',
			success: '#22c55e',
			running: '#3b82f6',
			failed: '#ef4444',
			pending: '#94a3b8',
			deprecated: '#94a3b8',
			idle: '#f59e0b',
			inactive: '#6b7280',
			completed: '#22c55e'
		};
		return colors[status] || '#94a3b8';
	}

	function getStatusBgColor(status: string): string {
		const colors: Record<string, string> = {
			active: '#dcfce7',
			success: '#dcfce7',
			running: '#dbeafe',
			failed: '#fee2e2',
			pending: '#f1f5f9',
			deprecated: '#f1f5f9',
			idle: '#fef3c7',
			inactive: '#f3f4f6',
			completed: '#dcfce7'
		};
		return colors[status] || '#f1f5f9';
	}

	function formatDateTime(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString('ja-JP', {
			month: 'numeric',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('ja-JP');
	}

	// Next action logic
	const nextAction = $derived(() => {
		switch (currentTab) {
			case 'requirements':
				return {
					text: 'Generate Job from current requirements',
					action: () => navigateToTab('generate'),
					button: 'Generate Job'
				};
			case 'generate':
				return {
					text: 'Review generated job configuration',
					action: () => navigateToTab('review'),
					button: 'Review Job'
				};
			case 'review':
				return {
					text: 'Start a new run with this job',
					action: () => navigateToTab('runs'),
					button: 'Start Run'
				};
			case 'runs':
				return {
					text: 'Analyze run results',
					action: () => navigateToTab('analyze'),
					button: 'View Analysis'
				};
			case 'analyze':
				return {
					text: 'Improve requirements based on analysis',
					action: () => navigateToTab('improve'),
					button: 'Improve'
				};
			case 'improve':
				return {
					text: 'Update requirements with improvements',
					action: () => navigateToTab('requirements'),
					button: 'Update Requirements'
				};
			case 'schedule':
				return {
					text: 'Configure automatic scheduling',
					action: () => {},
					button: 'Save Schedule'
				};
			default:
				return { text: 'Continue to next step', action: () => {}, button: 'Continue' };
		}
	});

	const tabs = [
		{ id: 'requirements', label: 'Requirements' },
		{ id: 'generate', label: 'Generate' },
		{ id: 'review', label: 'Review' },
		{ id: 'runs', label: 'Runs', badge: allRuns.filter((r) => r.status === 'running').length },
		{ id: 'analyze', label: 'Analyze' },
		{ id: 'improve', label: 'Improve' },
		{ id: 'schedule', label: 'Schedule' }
	];

	const sideNavItems = [
		{ id: 'overview', label: 'Overview', icon: 'home' },
		{ id: 'workbenches', label: 'Workbenches', icon: 'layers' },
		{ id: 'runs', label: 'All Runs', icon: 'play', badge: runStats().total },
		{ id: 'schedules', label: 'Schedules', icon: 'clock' },
		{ id: 'vault', label: 'Vault Settings', icon: 'key' }
	];
</script>

<div class="app-shell">
	<!-- App Header -->
	<header class="app-header">
		<div class="header-left">
			<div class="logo">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
					<rect width="24" height="24" rx="6" fill="#2563eb" />
					<path d="M7 12h10M12 7v10" stroke="white" stroke-width="2" stroke-linecap="round" />
				</svg>
				<span class="logo-text">myAgentDesk</span>
			</div>
		</div>
		<nav class="header-nav">
			<a
				href="{baseUrl}?project={selectedProjectId}&workbench={selectedWorkbenchId}&tab={currentTab}"
				class="nav-link active">Dashboard</a
			>
			<a
				href="{baseUrl}?project={selectedProjectId}&workbench={selectedWorkbenchId}&tab={currentTab}"
				class="nav-link">Docs</a
			>
			<a
				href="{baseUrl}?project={selectedProjectId}&workbench={selectedWorkbenchId}&tab={currentTab}"
				class="nav-link">Support</a
			>
		</nav>
		<div class="header-right">
			<button class="icon-btn" aria-label="Notifications">
				<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
					<path
						d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zm0 16a2 2 0 01-2-2h4a2 2 0 01-2 2z"
					/>
				</svg>
				<span class="notification-badge">3</span>
			</button>
			<div class="avatar">U</div>
		</div>
	</header>

	<div class="app-body">
		<!-- Sidebar -->
		<aside class="sidebar">
			<!-- Project Selector with Dropdown -->
			<div class="project-selector">
				<button class="project-btn" onclick={() => (showProjectDropdown = !showProjectDropdown)}>
					<div class="project-icon">
						<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
							<path
								d="M2 3a1 1 0 011-1h4.586a1 1 0 01.707.293l1.414 1.414a1 1 0 00.707.293H13a1 1 0 011 1v8a1 1 0 01-1 1H3a1 1 0 01-1-1V3z"
							/>
						</svg>
					</div>
					<span class="project-name">{currentProject.name}</span>
					<svg
						class="chevron"
						class:rotated={showProjectDropdown}
						width="12"
						height="12"
						viewBox="0 0 12 12"
					>
						<path d="M3 4.5l3 3 3-3" stroke="currentColor" stroke-width="1.5" fill="none" />
					</svg>
				</button>

				{#if showProjectDropdown}
					<div class="project-dropdown">
						<div class="dropdown-header">
							<span>Projects</span>
							<button
								class="dropdown-add-btn"
								onclick={() => {
									showProjectModal = true;
									showProjectDropdown = false;
								}}
							>
								+ New
							</button>
						</div>
						{#each projects as project}
							<button
								class="dropdown-item"
								class:active={project.id === selectedProjectId}
								onclick={() => selectProject(project.id)}
							>
								<span class="dropdown-item-name">{project.name}</span>
								<span class="dropdown-item-meta">{project.workbenchCount} workbenches</span>
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Navigation -->
			<nav class="side-nav">
				{#each sideNavItems as item}
					<button
						class="side-nav-link"
						class:active={currentView === item.id}
						onclick={() => navigateToView(item.id)}
					>
						<span class="nav-icon">
							{#if item.icon === 'home'}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
									><path d="M8 1.5l-6 5v7.5h4.5v-4h3v4H14V6.5l-6-5z" /></svg
								>
							{:else if item.icon === 'layers'}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
									><path d="M8 1L1 5l7 4 7-4-7-4zM1 8l7 4 7-4M1 11l7 4 7-4" /></svg
								>
							{:else if item.icon === 'play'}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
									><path d="M4 2l10 6-10 6V2z" /></svg
								>
							{:else if item.icon === 'clock'}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
									><circle cx="8" cy="8" r="6" stroke="currentColor" fill="none" /><path
										d="M8 4v4l3 2"
									/></svg
								>
							{:else if item.icon === 'key'}
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
									><path
										d="M10 1a5 5 0 00-4.9 6.1L1 11.2V15h3.8l.1-1.9 1.9-.1.1-1.9L8.8 11a5 5 0 101.2-10zm1 4a1 1 0 110-2 1 1 0 010 2z"
									/></svg
								>
							{/if}
						</span>
						<span class="nav-label">{item.label}</span>
						{#if item.badge}
							<span class="nav-badge">{item.badge}</span>
						{/if}
					</button>
				{/each}
			</nav>

			<!-- Workbenches Section -->
			<div class="sidebar-section">
				<div class="section-header">
					<span class="section-title">Workbenches</span>
					<button
						class="add-btn"
						aria-label="Add workbench"
						onclick={() => (showWorkbenchModal = true)}
					>
						<svg width="14" height="14" viewBox="0 0 14 14">
							<path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="2" fill="none" />
						</svg>
					</button>
				</div>
				<div class="workbench-list">
					{#each currentWorkbenches as wb}
						<button
							class="workbench-item"
							class:active={wb.id === selectedWorkbenchId}
							onclick={() => selectWorkbench(wb.id)}
						>
							<span class="wb-status" style="background: {getStatusColor(wb.status)}"></span>
							<span class="wb-name">{wb.name}</span>
							{#if wb.status === 'active'}
								<span class="wb-indicator"></span>
							{/if}
						</button>
					{/each}
				</div>
			</div>
		</aside>

		<!-- Main Content -->
		<main class="main-content">
			{#if currentView === 'workbenches'}
				<!-- Breadcrumb -->
				<div class="breadcrumb-bar">
					<nav class="breadcrumb">
						<button class="crumb" onclick={() => (showProjectDropdown = true)}>Projects</button>
						<span class="crumb-sep">/</span>
						<button class="crumb" onclick={() => (showProjectDropdown = true)}
							>{currentProject.name}</button
						>
						<span class="crumb-sep">/</span>
						<span class="crumb current">{currentWorkbench?.name}</span>
					</nav>
				</div>

				<!-- Workbench Header -->
				<div class="workbench-header">
					<div class="header-info">
						<div class="title-row">
							<h1>{currentWorkbench?.name}</h1>
							<span
								class="status-badge"
								style="background: {getStatusBgColor(
									currentWorkbench?.status || ''
								)}; color: {getStatusColor(currentWorkbench?.status || '')}"
							>
								{currentWorkbench?.status}
							</span>
						</div>
						<p class="description">{currentWorkbench?.description}</p>
					</div>
					<div class="header-actions">
						<button class="btn-secondary" onclick={() => openWorkbenchEditModal()}>
							<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
								<path
									d="M12.146.854a.5.5 0 01.708 0l2.292 2.292a.5.5 0 010 .708L5.146 13.854a.5.5 0 01-.168.11l-4 1.5a.5.5 0 01-.632-.632l1.5-4a.5.5 0 01.11-.168L12.146.854zM11.5 2.5L2.793 11.207l-.707 1.414 1.414-.707L12.207 3.207 11.5 2.5z"
								/>
							</svg>
							Edit
						</button>
						<button class="btn-secondary">
							<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
								<path d="M8 1v6m0 0l-3-3m3 3l3-3M1 10v3a2 2 0 002 2h10a2 2 0 002-2v-3" />
							</svg>
							Export
						</button>
						<button class="btn-secondary">
							<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
								<path
									d="M8 2a1.5 1.5 0 100 3 1.5 1.5 0 000-3zM8 6.5a1.5 1.5 0 100 3 1.5 1.5 0 000-3zM8 11a1.5 1.5 0 100 3 1.5 1.5 0 000-3z"
								/>
							</svg>
						</button>
					</div>
				</div>

				<!-- Tab Navigation -->
				<nav class="tab-nav">
					{#each tabs as tab}
						<button
							class="tab-btn"
							class:active={currentTab === tab.id}
							onclick={() => navigateToTab(tab.id)}
						>
							{tab.label}
							{#if tab.badge && tab.badge > 0}
								<span class="tab-badge">{tab.badge}</span>
							{/if}
						</button>
					{/each}
				</nav>

				<!-- Content Area -->
				<div class="content-area">
					<!-- REQUIREMENTS TAB -->
					{#if currentTab === 'requirements'}
						<div class="tab-content wide">
							<div class="content-header">
								<h2>Requirements</h2>
								<button class="btn-primary btn-sm">+ New Version</button>
							</div>
							<div class="requirements-split">
								<!-- Version List (Left) -->
								<div class="versions-list-panel">
									<div class="versions-list-header">
										<h3>Versions ({requirementVersions.length})</h3>
										<span class="version-hint">バージョンを選択して詳細を表示</span>
									</div>
									<div class="versions-list">
										{#each requirementVersions as req}
											<button
												class="version-card-btn"
												class:selected={req.id === selectedRequirementVersionId}
												class:active-version={req.status === 'active'}
												onclick={() => selectRequirementVersion(req.id)}
											>
												<div class="version-header">
													<div class="version-info">
														<span class="version-badge">v{req.version}</span>
														<span
															class="version-status"
															style="background: {getStatusBgColor(
																req.status
															)}; color: {getStatusColor(req.status)}"
														>
															{req.status}
														</span>
													</div>
													<span class="version-date">{formatDate(req.createdAt)}</span>
												</div>
												<p class="change-summary">{req.changeSummary}</p>
											</button>
										{/each}
									</div>
								</div>

								<!-- Markdown Editor/Viewer (Right) -->
								<div class="markdown-viewer-panel">
									{#if selectedRequirementVersion}
										<div class="markdown-viewer-header">
											<div class="viewer-title-row">
												<h3>v{selectedRequirementVersion.version}</h3>
												<span
													class="version-status"
													style="background: {getStatusBgColor(
														selectedRequirementVersion.status
													)}; color: {getStatusColor(selectedRequirementVersion.status)}"
												>
													{selectedRequirementVersion.status}
												</span>
											</div>
											<div class="viewer-mode-tabs">
												<button
													class="mode-tab"
													class:active={requirementsViewMode === 'edit'}
													onclick={() => (requirementsViewMode = 'edit')}
												>
													<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
														<path
															d="M10.5 1.5l2 2-7 7-3 1 1-3 7-7zm-1.5 3l-5 5-.5 1.5 1.5-.5 5-5-1-1z"
														/>
													</svg>
													Edit
												</button>
												<button
													class="mode-tab"
													class:active={requirementsViewMode === 'preview'}
													onclick={() => (requirementsViewMode = 'preview')}
												>
													<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
														<path
															d="M7 3C3 3 1 7 1 7s2 4 6 4 6-4 6-4-2-4-6-4zm0 6a2 2 0 110-4 2 2 0 010 4z"
														/>
													</svg>
													Preview
												</button>
											</div>
										</div>

										<!-- Edit Mode -->
										{#if requirementsViewMode === 'edit'}
											<div class="markdown-editor-content">
												<textarea
													class="markdown-textarea"
													bind:value={editedContent}
													placeholder="Markdownで要件を記述してください..."
												></textarea>
												<div class="editor-footer">
													<span class="editor-hint">Markdown形式で記述できます</span>
													<div class="editor-actions">
														<button
															class="btn-secondary btn-sm"
															onclick={() => (editedContent = selectedRequirementVersion.content)}
														>
															リセット
														</button>
														<button class="btn-primary btn-sm"> 保存 </button>
													</div>
												</div>
											</div>

											<!-- Preview Mode -->
										{:else}
											<div class="markdown-viewer-content">
												<div class="markdown-body">
													{#each editedContent.split('\n') as line}
														{#if line.startsWith('## ')}
															<h2 class="md-h2">{line.slice(3)}</h2>
														{:else if line.startsWith('### ')}
															<h3 class="md-h3">{line.slice(4)}</h3>
														{:else if line.startsWith('- **')}
															<p class="md-list-item">
																<span class="md-bold"
																	>{line.match(/\*\*([^*]+)\*\*/)?.[1] || ''}</span
																>{line.replace(/- \*\*[^*]+\*\*:?/, '')}
															</p>
														{:else if line.startsWith('- ')}
															<p class="md-list-item">{line.slice(2)}</p>
														{:else if line.match(/^\d+\. \*\*/)}
															<p class="md-numbered-item">
																<span class="md-num">{line.match(/^\d+/)?.[0]}.</span>
																<span class="md-bold"
																	>{line.match(/\*\*([^*]+)\*\*/)?.[1] || ''}</span
																>{line.replace(/^\d+\. \*\*[^*]+\*\*:?/, '')}
															</p>
														{:else if line.match(/^\d+\./)}
															<p class="md-numbered-item">
																<span class="md-num">{line.match(/^\d+/)?.[0]}.</span>
																{line.replace(/^\d+\.\s*/, '')}
															</p>
														{:else if line.startsWith('  - ')}
															<p class="md-nested-item">{line.slice(4)}</p>
														{:else if line.trim() === ''}
															<div class="md-spacer"></div>
														{:else}
															<p class="md-para">{line}</p>
														{/if}
													{/each}
												</div>
											</div>
										{/if}
									{:else}
										<div class="markdown-placeholder">
											<svg width="48" height="48" viewBox="0 0 48 48" fill="none">
												<rect
													x="8"
													y="8"
													width="32"
													height="32"
													rx="4"
													stroke="currentColor"
													stroke-width="2"
												/>
												<path
													d="M16 18h16M16 24h12M16 30h8"
													stroke="currentColor"
													stroke-width="2"
													stroke-linecap="round"
												/>
											</svg>
											<p>バージョンを選択してください</p>
										</div>
									{/if}
								</div>
							</div>
						</div>

						<!-- GENERATE TAB -->
					{:else if currentTab === 'generate'}
						<div class="tab-content">
							<div class="content-header">
								<h2>Generate Job</h2>
							</div>
							<div class="generate-card">
								<div class="source-info">
									<span class="source-label">Source Requirements:</span>
									<span class="source-version">v{activeRequirement?.version}</span>
									<span
										class="source-status"
										style="background: {getStatusBgColor('active')}; color: {getStatusColor(
											'active'
										)}">active</span
									>
								</div>
								<p class="generate-desc">
									Generate a new JobVersion from the current active requirements. This will analyze
									the requirements and create an optimized task breakdown with up to 20 tasks.
								</p>
								{#if showGenerateConfirm}
									<div class="confirm-box">
										<p>
											This will create a new JobVersion (v{jobVersions[0]?.majorVersion ||
												5}.{(jobVersions[0]?.minorVersion || 0) + 1}). Continue?
										</p>
										<div class="confirm-actions">
											<button class="btn-secondary" onclick={() => (showGenerateConfirm = false)}
												>Cancel</button
											>
											<button
												class="btn-primary"
												onclick={() => {
													showGenerateConfirm = false;
													navigateToTab('review');
												}}
											>
												Confirm Generate
											</button>
										</div>
									</div>
								{:else}
									<button class="btn-primary" onclick={() => (showGenerateConfirm = true)}>
										Start Generation
									</button>
								{/if}
							</div>
						</div>

						<!-- REVIEW TAB -->
					{:else if currentTab === 'review'}
						<div class="tab-content">
							<div class="content-header">
								<h2>Review Job</h2>
								<!-- Job Version Selector -->
								<div class="version-selector">
									<label for="job-version">Job Version:</label>
									<select
										id="job-version"
										class="version-select"
										onchange={(e) => selectJobVersion((e.target as HTMLSelectElement).value)}
									>
										{#each jobVersions as jv}
											<option value={jv.id} selected={jv.id === selectedJobVersionId}>
												{jv.versionLabel} ({jv.status}) - {jv.taskBreakdown.length} tasks
											</option>
										{/each}
									</select>
								</div>
							</div>

							{#if selectedJobVersion}
								<div class="job-card">
									<div class="job-header">
										<div class="job-title">
											<span class="job-badge">JobVersion</span>
											<span class="version-num">{selectedJobVersion.versionLabel}</span>
											<span
												class="job-status"
												style="background: {getStatusBgColor(
													selectedJobVersion.status
												)}; color: {getStatusColor(selectedJobVersion.status)}"
											>
												{selectedJobVersion.status}
											</span>
										</div>
										<span class="job-date"
											>Generated: {formatDateTime(selectedJobVersion.generatedAt)}</span
										>
									</div>
									<div class="job-meta">
										<span class="meta-item"
											><strong>Source:</strong> Requirements v{requirementVersions.find(
												(r) => r.id === selectedJobVersion.sourceRequirementVersionId
											)?.version}</span
										>
										<span class="meta-item"
											><strong>Tasks:</strong> {selectedJobVersion.taskBreakdown.length}</span
										>
										<span class="meta-item"
											><strong>Est. Duration:</strong> ~{Math.ceil(
												(selectedJobVersion.taskBreakdown.length * 5) / 60
											)}m</span
										>
										{#if selectedJobVersion.generationReason}
											<span class="meta-item"
												><strong>生成理由:</strong> {selectedJobVersion.generationReason}</span
											>
										{/if}
									</div>
								</div>

								<!-- Task Breakdown with split layout -->
								<div class="task-section-split">
									<div class="task-list-panel">
										<div class="task-section-header">
											<h3>Task Breakdown ({selectedJobVersion.taskBreakdown.length} tasks)</h3>
											<span class="task-hint">タスクをクリックしてインタフェースを表示</span>
										</div>
										<div class="task-list">
											{#each selectedJobVersion.taskBreakdown as task, i}
												<button
													class="task-card-btn"
													class:selected={selectedTaskId === task.id}
													onclick={() => selectTask(task.id)}
												>
													<div class="task-number">{i + 1}</div>
													<div class="task-title-area">
														<span class="task-name">{task.name}</span>
														<span class="task-agent">{task.agentType}</span>
													</div>
													<span
														class="task-status"
														style="background: {getStatusBgColor(
															task.status
														)}; color: {getStatusColor(task.status)}"
													>
														{task.status}
													</span>
												</button>
											{/each}
										</div>
									</div>

									<!-- Task Interface Panel -->
									<div class="task-interface-panel" class:visible={selectedTask}>
										{#if selectedTask}
											<div class="interface-panel-header">
												<h3>{selectedTask.name}</h3>
												<button
													class="close-panel-btn"
													onclick={() => (selectedTaskId = null)}
													aria-label="Close"
												>
													<svg width="16" height="16" viewBox="0 0 16 16"
														><path
															d="M4 4l8 8M12 4l-8 8"
															stroke="currentColor"
															stroke-width="2"
														/></svg
													>
												</button>
											</div>
											<div class="interface-panel-content">
												<div class="task-overview">
													<p class="task-desc">{selectedTask.description}</p>
													<div class="task-meta-row">
														<span class="task-meta-item"
															><strong>Agent:</strong> {selectedTask.agentType}</span
														>
														<span class="task-meta-item"
															><strong>Est. Duration:</strong>
															{selectedTask.estimatedDuration}</span
														>
													</div>
												</div>

												<!-- Input Interface -->
												<div class="interface-section">
													<div class="interface-section-header">
														<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
															><path d="M2 8l4-4v3h8v2H6v3L2 8z" /></svg
														>
														<h4>Input Interface</h4>
													</div>
													{#if selectedTask.inputInterface}
														<div class="interface-schema">
															<div class="schema-type">
																Type: <code>{selectedTask.inputInterface.type}</code>
															</div>
															{#if selectedTask.inputInterface.properties}
																<div class="schema-properties">
																	<div class="properties-header">Properties:</div>
																	{#each Object.entries(selectedTask.inputInterface.properties) as [propName, propDef]}
																		<div class="property-item">
																			<div class="property-name">
																				<code>{propName}</code>
																				{#if selectedTask.inputInterface.required?.includes(propName)}
																					<span class="required-badge">required</span>
																				{/if}
																			</div>
																			<div class="property-type">
																				<span class="type-badge">{propDef.type}</span>
																				{#if propDef.enum}
																					<span class="enum-values"
																						>enum: [{propDef.enum.join(', ')}]</span
																					>
																				{/if}
																				{#if propDef.default !== undefined}
																					<span class="default-value"
																						>default: {JSON.stringify(propDef.default)}</span
																					>
																				{/if}
																			</div>
																			{#if propDef.description}
																				<div class="property-desc">{propDef.description}</div>
																			{/if}
																		</div>
																	{/each}
																</div>
															{/if}
														</div>
													{:else}
														<div class="no-interface">インタフェース定義なし</div>
													{/if}
												</div>

												<!-- Output Interface -->
												<div class="interface-section">
													<div class="interface-section-header">
														<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
															><path d="M14 8l-4 4V9H2V7h8V4l4 4z" /></svg
														>
														<h4>Output Interface</h4>
													</div>
													{#if selectedTask.outputInterface}
														<div class="interface-schema">
															<div class="schema-type">
																Type: <code>{selectedTask.outputInterface.type}</code>
															</div>
															{#if selectedTask.outputInterface.properties}
																<div class="schema-properties">
																	<div class="properties-header">Properties:</div>
																	{#each Object.entries(selectedTask.outputInterface.properties) as [propName, propDef]}
																		<div class="property-item">
																			<div class="property-name">
																				<code>{propName}</code>
																			</div>
																			<div class="property-type">
																				<span class="type-badge">{propDef.type}</span>
																				{#if propDef.items}
																					<span class="items-type">items: {propDef.items.type}</span
																					>
																				{/if}
																			</div>
																			{#if propDef.description}
																				<div class="property-desc">{propDef.description}</div>
																			{/if}
																		</div>
																	{/each}
																</div>
															{/if}
														</div>
													{:else}
														<div class="no-interface">インタフェース定義なし</div>
													{/if}
												</div>
											</div>
										{:else}
											<div class="interface-placeholder">
												<svg width="48" height="48" viewBox="0 0 48 48" fill="none">
													<rect
														x="8"
														y="8"
														width="32"
														height="32"
														rx="4"
														stroke="currentColor"
														stroke-width="2"
													/>
													<path
														d="M16 20h16M16 28h10"
														stroke="currentColor"
														stroke-width="2"
														stroke-linecap="round"
													/>
												</svg>
												<p>タスクを選択してインタフェースを表示</p>
											</div>
										{/if}
									</div>
								</div>
							{/if}
						</div>

						<!-- RUNS TAB -->
					{:else if currentTab === 'runs'}
						<div class="tab-content wide">
							{#if selectedRun}
								<!-- Run Detail View -->
								<div class="run-detail-view">
									<div class="detail-header">
										<button class="back-btn" onclick={closeRunDetail}>
											<svg width="16" height="16" viewBox="0 0 16 16"
												><path
													d="M10 4L6 8l4 4"
													stroke="currentColor"
													stroke-width="2"
													fill="none"
												/></svg
											>
											Back to Runs
										</button>
										<h2>Run Details</h2>
									</div>

									<div class="run-detail-card">
										<div class="run-detail-header">
											<div class="run-detail-title">
												<span class="run-id-large">{selectedRun.id}</span>
												<span
													class="run-status-large"
													style="background: {getStatusBgColor(
														selectedRun.status
													)}; color: {getStatusColor(selectedRun.status)}"
												>
													{selectedRun.status}
												</span>
											</div>
											<div class="run-version-info">
												<strong>Job Version:</strong>
												{selectedRun.jobVersionLabel}
											</div>
										</div>

										<div class="run-stats-grid">
											<div class="run-stat">
												<span class="stat-label">Started</span>
												<span class="stat-value">{formatDateTime(selectedRun.startedAt)}</span>
											</div>
											<div class="run-stat">
												<span class="stat-label">Duration</span>
												<span class="stat-value">{selectedRun.duration || 'In progress...'}</span>
											</div>
											<div class="run-stat">
												<span class="stat-label">Tasks</span>
												<span class="stat-value"
													>{selectedRun.tasksCompleted} / {selectedRun.totalTasks}</span
												>
											</div>
											<div class="run-stat">
												<span class="stat-label">Trace ID</span>
												<span class="stat-value trace-link">{selectedRun.traceId}</span>
											</div>
										</div>

										{#if selectedRun.status === 'running'}
											<div class="run-progress-section">
												<div class="progress-header">
													<span>Progress</span>
													<span>{selectedRun.progress}%</span>
												</div>
												<div class="progress-bar large">
													<div class="progress-fill" style="width: {selectedRun.progress}%"></div>
												</div>
												<p class="current-task">Current Task: {selectedRun.currentTask}</p>
											</div>
										{/if}

										{#if selectedRun.errorMessage}
											<div class="run-error">
												<strong>Error:</strong>
												{selectedRun.errorMessage}
											</div>
										{/if}

										<div class="run-actions">
											<button class="btn-secondary">View Logs</button>
											<button class="btn-secondary">Open in Langfuse</button>
											{#if selectedRun.status === 'running'}
												<button class="btn-danger">Cancel Run</button>
											{:else if selectedRun.status === 'failed'}
												<button class="btn-primary">Retry Run</button>
											{/if}
										</div>
									</div>
								</div>
							{:else}
								<!-- Runs List View -->
								<div class="content-header">
									<div class="header-left-section">
										<h2>Runs</h2>
										<span class="runs-count">{allRuns.length} total runs</span>
									</div>
									<button class="btn-primary btn-sm">+ New Run</button>
								</div>

								<!-- Run Stats Summary -->
								<div class="runs-summary">
									<div class="summary-stat">
										<span class="summary-value">{runStats().total}</span>
										<span class="summary-label">Total</span>
									</div>
									<div class="summary-stat success">
										<span class="summary-value">{runStats().success}</span>
										<span class="summary-label">Success</span>
									</div>
									<div class="summary-stat failed">
										<span class="summary-value">{runStats().failed}</span>
										<span class="summary-label">Failed</span>
									</div>
									<div class="summary-stat">
										<span class="summary-value">{runStats().successRate}%</span>
										<span class="summary-label">Success Rate</span>
									</div>
									<div class="summary-stat">
										<span class="summary-value">{runStats().avgDuration}</span>
										<span class="summary-label">Avg Duration</span>
									</div>
								</div>

								<!-- Runs Table -->
								<div class="runs-table">
									<div class="table-header">
										<div class="th id">Run ID</div>
										<div class="th version">Job Version</div>
										<div class="th status">Status</div>
										<div class="th progress">Progress</div>
										<div class="th started">Started</div>
										<div class="th duration">Duration</div>
										<div class="th actions">Actions</div>
									</div>
									{#each paginatedRuns as run}
										<div
											class="table-row"
											class:running={run.status === 'running'}
											class:failed={run.status === 'failed'}
										>
											<div class="td id">
												<button class="run-link" onclick={() => viewRunDetail(run.id)}
													>{run.id}</button
												>
											</div>
											<div class="td version">
												<span class="version-tag">{run.jobVersionLabel}</span>
											</div>
											<div class="td status">
												<span
													class="run-status"
													style="background: {getStatusBgColor(run.status)}; color: {getStatusColor(
														run.status
													)}"
												>
													{run.status}
												</span>
											</div>
											<div class="td progress">
												<div class="mini-progress">
													<div class="mini-progress-bar">
														<div
															class="mini-progress-fill"
															style="width: {run.progress}%; background: {getStatusColor(
																run.status
															)}"
														></div>
													</div>
													<span class="mini-progress-text"
														>{run.tasksCompleted}/{run.totalTasks}</span
													>
												</div>
											</div>
											<div class="td started">{formatDateTime(run.startedAt)}</div>
											<div class="td duration">{run.duration || '-'}</div>
											<div class="td actions">
												<button
													class="action-btn"
													onclick={() => viewRunDetail(run.id)}
													aria-label="View details"
												>
													<svg width="16" height="16" viewBox="0 0 16 16"
														><path
															d="M8 3a5 5 0 015 5 5 5 0 01-5 5 5 5 0 01-5-5 5 5 0 015-5zm0 2a3 3 0 100 6 3 3 0 000-6z"
															fill="currentColor"
														/></svg
													>
												</button>
											</div>
										</div>
									{/each}
								</div>

								<!-- Pagination -->
								<div class="pagination">
									<button
										class="page-btn"
										disabled={runsPage === 1}
										onclick={() => goToRunsPage(runsPage - 1)}
									>
										<svg width="16" height="16" viewBox="0 0 16 16"
											><path
												d="M10 4L6 8l4 4"
												stroke="currentColor"
												stroke-width="1.5"
												fill="none"
											/></svg
										>
									</button>
									<div class="page-numbers">
										{#each Array.from({ length: Math.min(5, totalRunsPages) }, (_, i) => {
											if (totalRunsPages <= 5) return i + 1;
											if (runsPage <= 3) return i + 1;
											if (runsPage >= totalRunsPages - 2) return totalRunsPages - 4 + i;
											return runsPage - 2 + i;
										}) as pageNum}
											<button
												class="page-num"
												class:active={pageNum === runsPage}
												onclick={() => goToRunsPage(pageNum)}
											>
												{pageNum}
											</button>
										{/each}
										{#if totalRunsPages > 5 && runsPage < totalRunsPages - 2}
											<span class="page-ellipsis">...</span>
											<button class="page-num" onclick={() => goToRunsPage(totalRunsPages)}
												>{totalRunsPages}</button
											>
										{/if}
									</div>
									<button
										class="page-btn"
										disabled={runsPage === totalRunsPages}
										onclick={() => goToRunsPage(runsPage + 1)}
									>
										<svg width="16" height="16" viewBox="0 0 16 16"
											><path
												d="M6 4l4 4-4 4"
												stroke="currentColor"
												stroke-width="1.5"
												fill="none"
											/></svg
										>
									</button>
									<span class="page-info">
										Page {runsPage} of {totalRunsPages}
									</span>
								</div>
							{/if}
						</div>

						<!-- ANALYZE TAB -->
					{:else if currentTab === 'analyze'}
						<div class="tab-content">
							<div class="content-header">
								<h2>Analysis</h2>
							</div>
							<div class="analysis-grid">
								<div class="stat-card primary">
									<span class="stat-label">Success Rate</span>
									<span class="stat-value">{runStats().successRate}%</span>
								</div>
								<div class="stat-card">
									<span class="stat-label">Avg Duration</span>
									<span class="stat-value">{runStats().avgDuration}</span>
								</div>
								<div class="stat-card">
									<span class="stat-label">Total Runs</span>
									<span class="stat-value">{runStats().total}</span>
								</div>
								<div class="stat-card">
									<span class="stat-label">Failed Runs</span>
									<span class="stat-value failed">{runStats().failed}</span>
								</div>
							</div>

							<!-- Version Performance -->
							<div class="performance-section">
								<h3>Performance by Job Version</h3>
								<div class="version-perf-list">
									{#each jobVersions.slice(0, 4) as jv}
										{@const versionRuns = allRuns.filter((r) => r.jobVersionId === jv.id)}
										{@const versionSuccess = versionRuns.filter(
											(r) => r.status === 'success'
										).length}
										<div class="version-perf-item">
											<span class="version-label">{jv.versionLabel}</span>
											<div class="perf-bar-container">
												<div
													class="perf-bar"
													style="width: {versionRuns.length > 0
														? (versionSuccess / versionRuns.length) * 100
														: 0}%"
												></div>
											</div>
											<span class="perf-value"
												>{versionRuns.length > 0
													? Math.round((versionSuccess / versionRuns.length) * 100)
													: 0}% ({versionRuns.length} runs)</span
											>
										</div>
									{/each}
								</div>
							</div>

							<div class="trace-section">
								<h3>Langfuse Traces</h3>
								<p>View detailed execution traces and cost analysis in the Langfuse dashboard.</p>
								<button class="btn-secondary">Open Langfuse</button>
							</div>
						</div>

						<!-- IMPROVE TAB -->
					{:else if currentTab === 'improve'}
						<div class="tab-content">
							<div class="content-header">
								<h2>Improvements</h2>
							</div>
							<div class="improve-section">
								<h3>AI-Suggested Improvements</h3>
								<ul class="improvement-list">
									<li class="high">
										<span class="priority">High</span> Add retry logic for Gmail API rate limit errors
									</li>
									<li class="medium">
										<span class="priority">Medium</span> Implement exponential backoff for Slack webhook
									</li>
									<li class="medium">
										<span class="priority">Medium</span> Add timeout configuration for long-running tasks
									</li>
									<li class="low">
										<span class="priority">Low</span> Consider parallel processing for email analysis
									</li>
									<li class="low">
										<span class="priority">Low</span> Add caching for frequently accessed data
									</li>
								</ul>
							</div>
							<div class="current-req">
								<h3>Current Requirements (v{activeRequirement?.version})</h3>
								<pre class="markdown">{activeRequirement?.content}</pre>
							</div>
						</div>

						<!-- SCHEDULE TAB -->
					{:else if currentTab === 'schedule'}
						<div class="tab-content">
							<div class="content-header">
								<h2>Schedules</h2>
								<button class="btn-primary btn-sm">+ New Schedule</button>
							</div>
							<div class="schedule-list">
								{#each projectSchedules as schedule}
									<div class="schedule-card" class:enabled={schedule.isEnabled}>
										<div class="schedule-header">
											<span class="schedule-name">{schedule.name}</span>
											<div class="schedule-toggle">
												<label class="toggle">
													<input type="checkbox" checked={schedule.isEnabled} />
													<span class="toggle-slider"></span>
												</label>
											</div>
										</div>
										<div class="schedule-details">
											<div class="schedule-meta">
												<span class="cron">{schedule.cronExpression}</span>
												<span class="schedule-version">Job {schedule.targetJobVersionLabel}</span>
											</div>
											<div class="schedule-times">
												{#if schedule.nextRunAt}
													<span class="next-run">Next: {formatDateTime(schedule.nextRunAt)}</span>
												{:else}
													<span class="next-run disabled">Disabled</span>
												{/if}
												<span class="last-run">Last: {formatDateTime(schedule.lastRunAt)}</span>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>

				<!-- Next Action Bar -->
				<div class="next-action-bar">
					<div class="action-content">
						<span class="action-text">{nextAction().text}</span>
						<button class="btn-primary" onclick={nextAction().action}>
							{nextAction().button}
							<svg width="16" height="16" viewBox="0 0 16 16">
								<path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="2" fill="none" />
							</svg>
						</button>
					</div>
				</div>
			{/if}

			<!-- ===== OVERVIEW VIEW ===== -->
			{#if currentView === 'overview'}
				<div class="overview-content">
					<div class="overview-header">
						<h1>Dashboard Overview</h1>
						<p class="overview-subtitle">Welcome to {currentProject.name}</p>
					</div>

					<!-- Quick Stats Cards -->
					<div class="overview-stats">
						<div class="stat-card">
							<div class="stat-icon blue">
								<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"
									><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg
								>
							</div>
							<div class="stat-info">
								<span class="stat-value">{currentWorkbenches.length}</span>
								<span class="stat-label">Workbenches</span>
							</div>
						</div>
						<div class="stat-card">
							<div class="stat-icon green">
								<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"
									><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg
								>
							</div>
							<div class="stat-info">
								<span class="stat-value">{runStats().success}</span>
								<span class="stat-label">Successful Runs</span>
							</div>
						</div>
						<div class="stat-card">
							<div class="stat-icon red">
								<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"
									><path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg
								>
							</div>
							<div class="stat-info">
								<span class="stat-value">{runStats().failed}</span>
								<span class="stat-label">Failed Runs</span>
							</div>
						</div>
						<div class="stat-card">
							<div class="stat-icon purple">
								<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"
									><circle
										cx="12"
										cy="12"
										r="9"
										stroke="currentColor"
										fill="none"
										stroke-width="2"
									/><path d="M12 6v6l4 2" /></svg
								>
							</div>
							<div class="stat-info">
								<span class="stat-value">{runStats().avgDuration}</span>
								<span class="stat-label">Avg Duration</span>
							</div>
						</div>
					</div>

					<!-- Recent Activity & Quick Actions -->
					<div class="overview-grid">
						<!-- Recent Activity -->
						<div class="overview-panel">
							<div class="panel-header">
								<h3>Recent Activity</h3>
								<button class="btn-link" onclick={() => navigateToView('runs')}>View All →</button>
							</div>
							<div class="activity-list">
								{#each allRuns.slice(0, 5) as run}
									<div class="activity-item">
										<span class="activity-status" style="background: {getStatusColor(run.status)}"
										></span>
										<div class="activity-info">
											<span class="activity-title"
												>Run #{run.id.slice(-4)} ({run.jobVersionLabel})</span
											>
											<span class="activity-time">{formatDateTime(run.startedAt)}</span>
										</div>
										<span
											class="activity-badge"
											style="background: {getStatusBgColor(run.status)}; color: {getStatusColor(
												run.status
											)}"
										>
											{run.status}
										</span>
									</div>
								{/each}
							</div>
						</div>

						<!-- Active Workbenches -->
						<div class="overview-panel">
							<div class="panel-header">
								<h3>Active Workbenches</h3>
								<button class="btn-link" onclick={() => navigateToView('workbenches')}
									>View All →</button
								>
							</div>
							<div class="workbench-overview-list">
								{#each currentWorkbenches.filter((w) => w.status === 'active').slice(0, 4) as wb}
									<div class="workbench-overview-item">
										<span class="wb-status-dot" style="background: {getStatusColor(wb.status)}"
										></span>
										<div class="wb-overview-info">
											<span class="wb-overview-name">{wb.name}</span>
											<span class="wb-overview-desc">{wb.description}</span>
										</div>
										<span class="wb-last-run">Last: {formatDateTime(wb.lastRunAt)}</span>
									</div>
								{/each}
							</div>
						</div>

						<!-- Success Rate Chart (Placeholder) -->
						<div class="overview-panel wide">
							<div class="panel-header">
								<h3>Success Rate (Last 7 Days)</h3>
							</div>
							<div class="chart-placeholder">
								<div class="chart-bar-container">
									{#each [85, 92, 88, 75, 95, 90, 94] as rate, i}
										<div class="chart-bar-wrapper">
											<div class="chart-bar" style="height: {rate}%"></div>
											<span class="chart-label"
												>{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}</span
											>
										</div>
									{/each}
								</div>
								<div class="chart-legend">
									<span class="legend-item"
										><span class="legend-dot success"></span> Success Rate: {runStats()
											.successRate}%</span
									>
								</div>
							</div>
						</div>

						<!-- Upcoming Schedules -->
						<div class="overview-panel">
							<div class="panel-header">
								<h3>Upcoming Schedules</h3>
								<button class="btn-link" onclick={() => navigateToView('schedules')}
									>View All →</button
								>
							</div>
							<div class="upcoming-list">
								{#each projectSchedules.filter((s) => s.isEnabled).slice(0, 3) as schedule}
									<div class="upcoming-item">
										<div class="upcoming-icon">
											<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
												><circle cx="8" cy="8" r="6" stroke="currentColor" fill="none" /><path
													d="M8 4v4l3 2"
												/></svg
											>
										</div>
										<div class="upcoming-info">
											<span class="upcoming-name">{schedule.name}</span>
											<span class="upcoming-cron">{schedule.cronExpression}</span>
										</div>
										<span class="upcoming-next">{formatDateTime(schedule.nextRunAt)}</span>
									</div>
								{/each}
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- ===== ALL RUNS VIEW ===== -->
			{#if currentView === 'runs'}
				<div class="all-runs-content">
					<div class="all-runs-header">
						<div class="header-left">
							<h1>All Runs</h1>
							<span class="runs-count">{allRuns.length} total runs</span>
						</div>
						<div class="header-actions">
							<div class="search-box">
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"
									><circle cx="7" cy="7" r="5" stroke="currentColor" fill="none" /><path
										d="M11 11l3 3"
									/></svg
								>
								<input type="text" placeholder="Search runs..." class="search-input" />
							</div>
							<select class="filter-select">
								<option value="">All Status</option>
								<option value="success">Success</option>
								<option value="failed">Failed</option>
								<option value="running">Running</option>
							</select>
							<select class="filter-select">
								<option value="">All Versions</option>
								{#each jobVersions as jv}
									<option value={jv.id}>{jv.versionLabel}</option>
								{/each}
							</select>
						</div>
					</div>

					<!-- Stats Summary -->
					<div class="runs-stats-bar">
						<div class="runs-stat">
							<span class="runs-stat-value">{runStats().total}</span>
							<span class="runs-stat-label">Total</span>
						</div>
						<div class="runs-stat success">
							<span class="runs-stat-value">{runStats().success}</span>
							<span class="runs-stat-label">Success</span>
						</div>
						<div class="runs-stat failed">
							<span class="runs-stat-value">{runStats().failed}</span>
							<span class="runs-stat-label">Failed</span>
						</div>
						<div class="runs-stat running">
							<span class="runs-stat-value"
								>{allRuns.filter((r) => r.status === 'running').length}</span
							>
							<span class="runs-stat-label">Running</span>
						</div>
						<div class="runs-stat">
							<span class="runs-stat-value">{runStats().successRate}%</span>
							<span class="runs-stat-label">Success Rate</span>
						</div>
					</div>

					<!-- Runs Table -->
					<div class="runs-table-container">
						<table class="runs-table">
							<thead>
								<tr>
									<th>Workbench</th>
									<th>Run ID</th>
									<th>Job Version</th>
									<th>Status</th>
									<th>Started</th>
									<th>Duration</th>
									<th>Tasks</th>
									<th>Actions</th>
								</tr>
							</thead>
							<tbody>
								{#each paginatedRuns as run}
									<tr class:running={run.status === 'running'}>
										<td class="workbench-cell">
											<div class="workbench-info-cell">
												<span class="wb-cell-name">{run.workbenchName}</span>
												<span class="wb-cell-project">{run.projectName}</span>
											</div>
										</td>
										<td class="run-id">
											<span class="mono">{run.id}</span>
											<span class="trace-id">Trace: {run.traceId}</span>
										</td>
										<td>
											<span class="version-tag">{run.jobVersionLabel}</span>
										</td>
										<td>
											<span
												class="status-pill"
												style="background: {getStatusBgColor(run.status)}; color: {getStatusColor(
													run.status
												)}"
											>
												{#if run.status === 'running'}
													<span class="status-spinner"></span>
												{/if}
												{run.status}
											</span>
										</td>
										<td class="time-cell">{formatDateTime(run.startedAt)}</td>
										<td class="duration-cell">{run.duration || '-'}</td>
										<td class="tasks-cell">
											<div class="tasks-progress">
												<span class="tasks-count">{run.tasksCompleted}/{run.totalTasks}</span>
												<div class="tasks-bar">
													<div
														class="tasks-fill"
														style="width: {(run.tasksCompleted / run.totalTasks) *
															100}%; background: {getStatusColor(run.status)}"
													></div>
												</div>
											</div>
										</td>
										<td class="actions-cell">
											<button
												class="icon-btn-sm"
												title="View Details"
												onclick={() => viewRunDetail(run.id)}
											>
												<svg width="14" height="14" viewBox="0 0 14 14"
													><path
														d="M7 3C3 3 1 7 1 7s2 4 6 4 6-4 6-4-2-4-6-4zm0 6a2 2 0 110-4 2 2 0 010 4z"
														fill="currentColor"
													/></svg
												>
											</button>
											<button class="icon-btn-sm" title="Re-run">
												<svg width="14" height="14" viewBox="0 0 14 14"
													><path
														d="M11 7A4 4 0 113 7m0 0l-2 2m2-2l2 2"
														stroke="currentColor"
														fill="none"
														stroke-width="1.5"
													/></svg
												>
											</button>
											{#if run.status === 'failed'}
												<button class="icon-btn-sm error" title="View Error">
													<svg width="14" height="14" viewBox="0 0 14 14"
														><path
															d="M7 1l6 12H1L7 1zm0 4v3m0 2h.01"
															stroke="currentColor"
															fill="none"
														/></svg
													>
												</button>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>

					<!-- Pagination -->
					<div class="pagination">
						<span class="pagination-info"
							>Showing {(runsPage - 1) * runsPerPage + 1}-{Math.min(
								runsPage * runsPerPage,
								allRuns.length
							)} of {allRuns.length}</span
						>
						<div class="pagination-controls">
							<button
								class="pagination-btn"
								disabled={runsPage === 1}
								onclick={() => goToRunsPage(runsPage - 1)}>← Prev</button
							>
							{#each Array.from({ length: Math.min(5, totalRunsPages) }, (_, i) => {
								const startPage = Math.max(1, Math.min(runsPage - 2, totalRunsPages - 4));
								return startPage + i;
							}) as pageNum}
								<button
									class="pagination-btn"
									class:active={pageNum === runsPage}
									onclick={() => goToRunsPage(pageNum)}>{pageNum}</button
								>
							{/each}
							{#if totalRunsPages > 5 && runsPage < totalRunsPages - 2}
								<span class="pagination-ellipsis">...</span>
								<button class="pagination-btn" onclick={() => goToRunsPage(totalRunsPages)}
									>{totalRunsPages}</button
								>
							{/if}
							<button
								class="pagination-btn"
								disabled={runsPage === totalRunsPages}
								onclick={() => goToRunsPage(runsPage + 1)}>Next →</button
							>
						</div>
					</div>
				</div>
			{/if}

			<!-- ===== SCHEDULES VIEW ===== -->
			{#if currentView === 'schedules'}
				<div class="schedules-content">
					<div class="schedules-header">
						<div class="header-left">
							<h1>Schedules</h1>
							<span class="schedules-count"
								>{projectSchedules.length} schedules ({projectSchedules.filter((s) => s.isEnabled)
									.length} active)</span
							>
						</div>
						<div class="header-actions">
							<button class="btn-primary">
								<svg width="16" height="16" viewBox="0 0 16 16"
									><path
										d="M8 1v14M1 8h14"
										stroke="currentColor"
										stroke-width="2"
										fill="none"
									/></svg
								>
								New Schedule
							</button>
						</div>
					</div>

					<!-- Schedules Grid -->
					<div class="schedules-grid">
						{#each projectSchedules as schedule}
							<div class="schedule-card" class:disabled={!schedule.isEnabled}>
								<div class="schedule-card-header">
									<div class="schedule-title-row">
										<h3 class="schedule-name">{schedule.name}</h3>
										<label class="toggle-switch">
											<input type="checkbox" checked={schedule.isEnabled} />
											<span class="toggle-slider"></span>
										</label>
									</div>
									<div class="schedule-meta-row">
										<span class="schedule-workbench">
											<svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor"
												><path
													d="M6 1L1 3.5l5 2.5 5-2.5L6 1zM1 6l5 2.5L11 6M1 8.5l5 2.5 5-2.5"
												/></svg
											>
											{schedule.workbenchName}
										</span>
										<span class="schedule-project">({schedule.projectName})</span>
									</div>
									<span class="schedule-version">Job: {schedule.targetJobVersionLabel}</span>
								</div>
								<div class="schedule-card-body">
									<div class="cron-display">
										<span class="cron-label">Cron Expression</span>
										<code class="cron-value">{schedule.cronExpression}</code>
									</div>
									<div class="schedule-timing">
										<div class="timing-item">
											<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"
												><path d="M7 1l5 5-5 5-5-5 5-5z" /></svg
											>
											<span class="timing-label">Next Run</span>
											<span class="timing-value"
												>{schedule.nextRunAt
													? formatDateTime(schedule.nextRunAt)
													: 'Disabled'}</span
											>
										</div>
										<div class="timing-item">
											<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"
												><path
													d="M9 5l-4 4M5 5l4 4"
													stroke="currentColor"
													stroke-width="2"
													fill="none"
												/></svg
											>
											<span class="timing-label">Last Run</span>
											<span class="timing-value">{formatDateTime(schedule.lastRunAt)}</span>
										</div>
									</div>
								</div>
								<div class="schedule-card-footer">
									<button class="btn-secondary btn-sm">Edit</button>
									<button class="btn-secondary btn-sm">Run Now</button>
									<button class="btn-ghost btn-sm">Delete</button>
								</div>
							</div>
						{/each}

						<!-- Add New Schedule Card -->
						<div class="schedule-card add-card">
							<div class="add-card-content">
								<svg
									width="40"
									height="40"
									viewBox="0 0 40 40"
									fill="currentColor"
									class="add-icon"
								>
									<circle
										cx="20"
										cy="20"
										r="18"
										stroke="currentColor"
										stroke-width="2"
										fill="none"
										stroke-dasharray="4 2"
									/>
									<path d="M20 12v16M12 20h16" stroke="currentColor" stroke-width="2" />
								</svg>
								<span class="add-text">Add New Schedule</span>
								<p class="add-hint">Configure automated job execution</p>
							</div>
						</div>
					</div>

					<!-- Cron Help Section -->
					<div class="cron-help-panel">
						<h4>Cron Expression Reference</h4>
						<div class="cron-examples">
							<div class="cron-example">
								<code>0 8 * * *</code>
								<span>Every day at 8:00 AM</span>
							</div>
							<div class="cron-example">
								<code>0 */2 * * *</code>
								<span>Every 2 hours</span>
							</div>
							<div class="cron-example">
								<code>0 10 * * 1</code>
								<span>Every Monday at 10:00 AM</span>
							</div>
							<div class="cron-example">
								<code>0 18 * * 1-5</code>
								<span>Weekdays at 6:00 PM</span>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- ===== VAULT SETTINGS VIEW ===== -->
			{#if currentView === 'vault'}
				<div class="vault-content">
					<div class="vault-header">
						<div class="header-left">
							<h1>Vault Settings</h1>
							<p class="vault-subtitle">
								Manage API keys, credentials, and secrets for {currentProject.name}
							</p>
						</div>
					</div>

					<!-- Warning Banner -->
					<div class="warning-banner">
						<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"
							><path d="M10 2L2 18h16L10 2zm0 6v4m0 2h.01" /></svg
						>
						<div class="warning-content">
							<strong>Security Notice</strong>
							<p>
								Secrets are encrypted at rest. Never share or expose these values in logs or code.
							</p>
						</div>
					</div>

					<!-- Secrets Grid -->
					<div class="secrets-grid">
						<!-- Gmail API Section -->
						<div class="secrets-section">
							<div class="section-title-row">
								<div class="section-icon gmail">
									<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"
										><path d="M2 4l8 5 8-5M2 4v12h16V4H2z" /></svg
									>
								</div>
								<div class="section-title-info">
									<h3>Gmail API</h3>
									<span class="secret-status connected">Connected</span>
								</div>
							</div>
							<div class="secrets-list">
								<div class="secret-item">
									<span class="secret-key">GMAIL_CLIENT_ID</span>
									<span class="secret-value masked"
										>••••••••••••3456.apps.googleusercontent.com</span
									>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
								<div class="secret-item">
									<span class="secret-key">GMAIL_CLIENT_SECRET</span>
									<span class="secret-value masked">••••••••••••••••</span>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
								<div class="secret-item">
									<span class="secret-key">GMAIL_REFRESH_TOKEN</span>
									<span class="secret-value masked">••••••••••••••••</span>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
							</div>
							<div class="section-footer">
								<span class="last-updated">Last updated: Dec 14, 2024</span>
								<button class="btn-link">Test Connection</button>
							</div>
						</div>

						<!-- Slack API Section -->
						<div class="secrets-section">
							<div class="section-title-row">
								<div class="section-icon slack">
									<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"
										><path
											d="M7 2a2 2 0 00-2 2v3H3a2 2 0 000 4h2v3a2 2 0 104 0v-3h4v3a2 2 0 104 0V9h2a2 2 0 000-4h-2V4a2 2 0 10-4 0v1H9V4a2 2 0 00-2-2z"
										/></svg
									>
								</div>
								<div class="section-title-info">
									<h3>Slack API</h3>
									<span class="secret-status connected">Connected</span>
								</div>
							</div>
							<div class="secrets-list">
								<div class="secret-item">
									<span class="secret-key">SLACK_WEBHOOK_URL</span>
									<span class="secret-value masked"
										>https://hooks.slack.com/services/T••••••••/B••••••••/••••••••</span
									>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
								<div class="secret-item">
									<span class="secret-key">SLACK_BOT_TOKEN</span>
									<span class="secret-value masked"
										>xoxb-••••••••••••-••••••••••••-••••••••••••••••••••••••</span
									>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
							</div>
							<div class="section-footer">
								<span class="last-updated">Last updated: Dec 12, 2024</span>
								<button class="btn-link">Test Connection</button>
							</div>
						</div>

						<!-- Gemini API Section -->
						<div class="secrets-section">
							<div class="section-title-row">
								<div class="section-icon gemini">
									<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"
										><circle
											cx="10"
											cy="10"
											r="8"
											stroke="currentColor"
											fill="none"
											stroke-width="2"
										/><circle cx="10" cy="10" r="3" fill="currentColor" /></svg
									>
								</div>
								<div class="section-title-info">
									<h3>Gemini API</h3>
									<span class="secret-status connected">Connected</span>
								</div>
							</div>
							<div class="secrets-list">
								<div class="secret-item">
									<span class="secret-key">GOOGLE_API_KEY</span>
									<span class="secret-value masked">AIza••••••••••••••••••••••••••••••••••••</span>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
							</div>
							<div class="section-footer">
								<span class="last-updated">Last updated: Dec 14, 2024</span>
								<button class="btn-link">Test Connection</button>
							</div>
						</div>

						<!-- Custom Secrets Section -->
						<div class="secrets-section">
							<div class="section-title-row">
								<div class="section-icon custom">
									<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"
										><path
											d="M12 1a5 5 0 00-4.9 6.1L2 12.2V17h4.8l.1-2.9 2.9-.1.1-2.9L11.8 10A5 5 0 1012 1z"
										/></svg
									>
								</div>
								<div class="section-title-info">
									<h3>Custom Secrets</h3>
									<span class="secret-count">2 secrets</span>
								</div>
							</div>
							<div class="secrets-list">
								<div class="secret-item">
									<span class="secret-key">DATABASE_URL</span>
									<span class="secret-value masked"
										>postgresql://••••••••:••••••••@localhost:5432/myagent</span
									>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
								<div class="secret-item">
									<span class="secret-key">ENCRYPTION_KEY</span>
									<span class="secret-value masked">••••••••••••••••••••••••••••••••</span>
									<button class="btn-icon" title="Copy"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><rect
												x="4"
												y="4"
												width="8"
												height="8"
												rx="1"
												stroke="currentColor"
												fill="none"
											/><path d="M2 10V2h8" stroke="currentColor" fill="none" /></svg
										></button
									>
									<button class="btn-icon" title="Edit"
										><svg width="14" height="14" viewBox="0 0 14 14"
											><path d="M10 2l2 2-8 8H2v-2l8-8z" stroke="currentColor" fill="none" /></svg
										></button
									>
								</div>
							</div>
							<div class="section-footer">
								<button class="btn-secondary btn-sm">+ Add Secret</button>
							</div>
						</div>
					</div>

					<!-- Vault Settings -->
					<div class="vault-settings-panel">
						<h3>Vault Configuration</h3>
						<div class="settings-list">
							<div class="setting-item">
								<div class="setting-info">
									<span class="setting-label">Auto-rotate secrets</span>
									<span class="setting-desc">Automatically rotate API keys every 90 days</span>
								</div>
								<label class="toggle-switch">
									<input type="checkbox" checked />
									<span class="toggle-slider"></span>
								</label>
							</div>
							<div class="setting-item">
								<div class="setting-info">
									<span class="setting-label">Audit logging</span>
									<span class="setting-desc">Log all secret access and modifications</span>
								</div>
								<label class="toggle-switch">
									<input type="checkbox" checked />
									<span class="toggle-slider"></span>
								</label>
							</div>
							<div class="setting-item">
								<div class="setting-info">
									<span class="setting-label">Secret versioning</span>
									<span class="setting-desc">Keep history of previous secret values</span>
								</div>
								<label class="toggle-switch">
									<input type="checkbox" />
									<span class="toggle-slider"></span>
								</label>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</main>
	</div>
</div>

<!-- Project Modal -->
{#if showProjectModal}
	<div class="modal-overlay" onclick={() => (showProjectModal = false)}>
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h3>Create New Project</h3>
				<button class="modal-close" onclick={() => (showProjectModal = false)}>×</button>
			</div>
			<div class="modal-body">
				<div class="form-group">
					<label for="project-name">Project Name</label>
					<input
						type="text"
						id="project-name"
						bind:value={newProjectName}
						placeholder="Enter project name"
					/>
				</div>
				<div class="form-group">
					<label for="project-desc">Description</label>
					<textarea id="project-desc" placeholder="Enter project description" rows="3"></textarea>
				</div>
			</div>
			<div class="modal-footer">
				<button class="btn-secondary" onclick={() => (showProjectModal = false)}>Cancel</button>
				<button
					class="btn-primary"
					onclick={() => {
						showProjectModal = false;
					}}>Create Project</button
				>
			</div>
		</div>
	</div>
{/if}

<!-- Workbench Modal -->
{#if showWorkbenchModal}
	<div class="modal-overlay" onclick={() => (showWorkbenchModal = false)}>
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h3>Create New Workbench</h3>
				<button class="modal-close" onclick={() => (showWorkbenchModal = false)}>×</button>
			</div>
			<div class="modal-body">
				<div class="form-group">
					<label for="wb-name">Workbench Name</label>
					<input
						type="text"
						id="wb-name"
						bind:value={newWorkbenchName}
						placeholder="Enter workbench name"
					/>
				</div>
				<div class="form-group">
					<label for="wb-desc">Description</label>
					<textarea
						id="wb-desc"
						bind:value={newWorkbenchDesc}
						placeholder="Enter workbench description"
						rows="3"
					></textarea>
				</div>
				<div class="form-group">
					<label for="wb-project">Project</label>
					<select id="wb-project">
						{#each projects as project}
							<option value={project.id} selected={project.id === selectedProjectId}
								>{project.name}</option
							>
						{/each}
					</select>
				</div>
			</div>
			<div class="modal-footer">
				<button class="btn-secondary" onclick={() => (showWorkbenchModal = false)}>Cancel</button>
				<button
					class="btn-primary"
					onclick={() => {
						showWorkbenchModal = false;
					}}>Create Workbench</button
				>
			</div>
		</div>
	</div>
{/if}

<!-- Workbench Edit Modal -->
{#if showWorkbenchEditModal}
	<div class="modal-overlay" onclick={() => (showWorkbenchEditModal = false)}>
		<div class="modal modal-wide" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h3>Edit Workbench</h3>
				<button class="modal-close" onclick={() => (showWorkbenchEditModal = false)}>×</button>
			</div>
			<div class="modal-body">
				<div class="form-group">
					<label for="edit-wb-name">Workbench Name</label>
					<input
						type="text"
						id="edit-wb-name"
						bind:value={editingWorkbenchName}
						placeholder="Enter workbench name"
					/>
				</div>
				<div class="form-group">
					<label for="edit-wb-desc">Description</label>
					<textarea
						id="edit-wb-desc"
						bind:value={editingWorkbenchDesc}
						placeholder="Enter workbench description"
						rows="4"
					></textarea>
				</div>
				<div class="form-group">
					<label for="edit-wb-status">Status</label>
					<select id="edit-wb-status" bind:value={editingWorkbenchStatus}>
						<option value="active">Active</option>
						<option value="idle">Idle</option>
						<option value="inactive">Inactive</option>
					</select>
				</div>
				<div class="form-group">
					<label>Project</label>
					<p class="form-static">{currentProject.name}</p>
					<span class="form-hint">Workbench cannot be moved to another project</span>
				</div>
				<div class="form-group">
					<label>Created</label>
					<p class="form-static">
						{currentWorkbench?.lastRunAt ? formatDateTime(currentWorkbench.lastRunAt) : 'Never'}
					</p>
				</div>
			</div>
			<div class="modal-footer">
				<button
					class="btn-danger-outline"
					onclick={() => {
						showWorkbenchEditModal = false;
					}}
				>
					<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
						<path
							d="M4.5 1v1H1v1h12V2h-3.5V1h-5zM2 5v8a1 1 0 001 1h8a1 1 0 001-1V5H2zm3 2h1v5H5V7zm3 0h1v5H8V7z"
						/>
					</svg>
					Delete
				</button>
				<div class="modal-actions-right">
					<button class="btn-secondary" onclick={() => (showWorkbenchEditModal = false)}
						>Cancel</button
					>
					<button
						class="btn-primary"
						onclick={() => {
							showWorkbenchEditModal = false;
						}}>Save Changes</button
					>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ===== RESET & VARIABLES ===== */
	* {
		box-sizing: border-box;
		margin: 0;
		padding: 0;
	}
	:root {
		--primary: #2563eb;
		--primary-hover: #1d4ed8;
		--bg: #f9fafb;
		--surface: #ffffff;
		--border: #e5e7eb;
		--text-primary: #111827;
		--text-secondary: #6b7280;
		--text-muted: #9ca3af;
		--danger: #ef4444;
	}

	/* ===== APP SHELL ===== */
	.app-shell {
		min-height: 100vh;
		background: var(--bg);
		display: flex;
		flex-direction: column;
	}

	/* ===== HEADER ===== */
	.app-header {
		height: 56px;
		background: var(--surface);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 16px;
		position: sticky;
		top: 0;
		z-index: 100;
	}
	.header-left {
		display: flex;
		align-items: center;
	}
	.logo {
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 600;
		font-size: 16px;
		color: var(--text-primary);
	}
	.header-nav {
		display: flex;
		gap: 24px;
	}
	.nav-link {
		font-size: 14px;
		color: var(--text-secondary);
		text-decoration: none;
		padding: 8px 0;
		border-bottom: 2px solid transparent;
	}
	.nav-link:hover {
		color: var(--text-primary);
	}
	.nav-link.active {
		color: var(--primary);
		border-bottom-color: var(--primary);
	}
	.header-right {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.icon-btn {
		position: relative;
		width: 36px;
		height: 36px;
		border-radius: 8px;
		border: none;
		background: transparent;
		color: var(--text-secondary);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.icon-btn:hover {
		background: var(--bg);
	}
	.notification-badge {
		position: absolute;
		top: 4px;
		right: 4px;
		min-width: 16px;
		height: 16px;
		background: var(--danger);
		color: white;
		font-size: 10px;
		font-weight: 600;
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.avatar {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: var(--primary);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 13px;
		font-weight: 500;
	}

	/* ===== APP BODY ===== */
	.app-body {
		display: flex;
		flex: 1;
	}

	/* ===== SIDEBAR ===== */
	.sidebar {
		width: 240px;
		background: var(--surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		position: sticky;
		top: 56px;
		height: calc(100vh - 56px);
		flex-shrink: 0;
	}
	.project-selector {
		padding: 12px;
		border-bottom: 1px solid var(--border);
		position: relative;
	}
	.project-btn {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 10px;
		background: var(--bg);
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
		text-align: left;
	}
	.project-icon {
		color: var(--text-secondary);
	}
	.project-name {
		flex: 1;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.chevron {
		color: var(--text-muted);
		transition: transform 0.2s;
	}
	.chevron.rotated {
		transform: rotate(180deg);
	}

	/* Project Dropdown */
	.project-dropdown {
		position: absolute;
		top: 100%;
		left: 12px;
		right: 12px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		z-index: 200;
		margin-top: 4px;
	}
	.dropdown-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
		font-size: 12px;
		color: var(--text-muted);
	}
	.dropdown-add-btn {
		font-size: 12px;
		color: var(--primary);
		background: none;
		border: none;
		cursor: pointer;
	}
	.dropdown-item {
		width: 100%;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		padding: 10px 12px;
		border: none;
		background: transparent;
		cursor: pointer;
		text-align: left;
	}
	.dropdown-item:hover {
		background: var(--bg);
	}
	.dropdown-item.active {
		background: #eff6ff;
	}
	.dropdown-item-name {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.dropdown-item-meta {
		font-size: 11px;
		color: var(--text-muted);
	}

	.side-nav {
		padding: 12px 8px;
		border-bottom: 1px solid var(--border);
	}
	.side-nav-link {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		border-radius: 6px;
		font-size: 13px;
		color: var(--text-secondary);
		text-decoration: none;
	}
	.side-nav-link:hover {
		background: var(--bg);
		color: var(--text-primary);
	}
	.side-nav-link.active {
		background: #eff6ff;
		color: var(--primary);
	}
	.nav-icon {
		width: 16px;
		height: 16px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.nav-label {
		flex: 1;
	}
	.nav-badge {
		font-size: 10px;
		padding: 2px 6px;
		background: var(--bg);
		border-radius: 10px;
		color: var(--text-muted);
	}

	.sidebar-section {
		padding: 12px;
		flex: 1;
	}
	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}
	.section-title {
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		color: var(--text-muted);
		letter-spacing: 0.5px;
	}
	.add-btn {
		width: 20px;
		height: 20px;
		border-radius: 4px;
		border: none;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.add-btn:hover {
		background: var(--bg);
		color: var(--text-primary);
	}

	.workbench-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.workbench-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		border-radius: 6px;
		font-size: 13px;
		color: var(--text-secondary);
		border: none;
		background: transparent;
		cursor: pointer;
		text-align: left;
		width: 100%;
	}
	.workbench-item:hover {
		background: var(--bg);
	}
	.workbench-item.active {
		background: #eff6ff;
		color: var(--primary);
	}
	.wb-status {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.wb-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.wb-indicator {
		width: 6px;
		height: 6px;
		background: var(--primary);
		border-radius: 50%;
		animation: pulse 2s infinite;
	}
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	/* ===== MAIN CONTENT ===== */
	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
		height: calc(100vh - 56px);
		overflow-y: auto;
	}
	.breadcrumb-bar {
		padding: 12px 24px;
		border-bottom: 1px solid var(--border);
		background: var(--surface);
	}
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
	}
	.crumb {
		color: var(--text-secondary);
		text-decoration: none;
		background: none;
		border: none;
		cursor: pointer;
		font-size: 13px;
	}
	.crumb:hover {
		color: var(--primary);
	}
	.crumb.current {
		color: var(--text-primary);
		font-weight: 500;
		cursor: default;
	}
	.crumb-sep {
		color: var(--text-muted);
	}

	.workbench-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		padding: 20px 24px;
		background: var(--surface);
		border-bottom: 1px solid var(--border);
	}
	.header-info h1 {
		font-size: 20px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.title-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.status-badge {
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
	}
	.description {
		font-size: 14px;
		color: var(--text-secondary);
		margin-top: 4px;
	}
	.header-actions {
		display: flex;
		gap: 8px;
	}

	/* ===== TAB NAVIGATION ===== */
	.tab-nav {
		display: flex;
		gap: 0;
		padding: 0 24px;
		background: var(--surface);
		border-bottom: 1px solid var(--border);
	}
	.tab-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 12px 16px;
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		font-size: 14px;
		color: var(--text-secondary);
		cursor: pointer;
		margin-bottom: -1px;
	}
	.tab-btn:hover {
		color: var(--text-primary);
	}
	.tab-btn.active {
		color: var(--primary);
		border-bottom-color: var(--primary);
		font-weight: 500;
	}
	.tab-badge {
		font-size: 10px;
		padding: 2px 6px;
		background: var(--primary);
		color: white;
		border-radius: 10px;
	}

	/* ===== CONTENT AREA ===== */
	.content-area {
		flex: 1;
		padding: 24px;
		overflow-y: auto;
	}
	.tab-content {
		max-width: 900px;
	}
	.tab-content.wide {
		max-width: 1200px;
	}
	.content-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 20px;
	}
	.content-header h2 {
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.header-left-section {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.runs-count {
		font-size: 13px;
		color: var(--text-muted);
	}

	/* ===== BUTTONS ===== */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 10px 16px;
		background: var(--primary);
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
	}
	.btn-primary:hover {
		background: var(--primary-hover);
	}
	.btn-secondary {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 10px 16px;
		background: var(--surface);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
	}
	.btn-secondary:hover {
		background: var(--bg);
	}
	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 10px 16px;
		background: var(--danger);
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
	}
	.btn-sm {
		padding: 6px 12px;
		font-size: 13px;
	}

	/* ===== VERSION SELECTOR ===== */
	.version-selector {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.version-selector label {
		font-size: 13px;
		color: var(--text-secondary);
	}
	.version-select {
		padding: 6px 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 13px;
		background: var(--surface);
		cursor: pointer;
	}

	/* ===== CARDS ===== */
	.version-card,
	.job-card,
	.run-card,
	.schedule-card,
	.generate-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 16px;
		margin-bottom: 12px;
	}
	.version-card.active {
		border-color: var(--primary);
	}
	.version-header,
	.job-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}
	.version-info,
	.job-title {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.version-badge {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.version-status,
	.job-status,
	.run-status,
	.task-status,
	.schedule-enabled {
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
	}
	.version-date,
	.job-date {
		font-size: 12px;
		color: var(--text-muted);
	}
	.change-summary {
		font-size: 14px;
		color: var(--text-secondary);
		margin-bottom: 12px;
	}
	.version-content {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid var(--border);
	}
	.markdown {
		font-size: 13px;
		line-height: 1.6;
		white-space: pre-wrap;
		font-family: inherit;
		color: var(--text-primary);
		background: var(--bg);
		padding: 12px;
		border-radius: 6px;
	}

	/* ===== REQUIREMENTS SPLIT LAYOUT ===== */
	.requirements-split {
		display: grid;
		grid-template-columns: 320px 1fr;
		gap: 24px;
		margin-top: 16px;
	}
	.versions-list-panel {
		min-width: 0;
	}
	.versions-list-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}
	.versions-list-header h3 {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}
	.version-hint {
		font-size: 11px;
		color: var(--text-muted);
	}
	.versions-list-panel .versions-list {
		display: flex;
		flex-direction: column;
		gap: 8px;
		max-height: calc(100vh - 320px);
		overflow-y: auto;
	}
	.version-card-btn {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 12px 14px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		cursor: pointer;
		text-align: left;
		transition: all 0.15s;
	}
	.version-card-btn:hover {
		border-color: var(--primary);
		background: #f8fafc;
	}
	.version-card-btn.selected {
		border-color: var(--primary);
		background: #eff6ff;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}
	.version-card-btn.active-version {
		border-left: 3px solid var(--primary);
	}
	.version-card-btn .version-header {
		margin-bottom: 0;
	}
	.version-card-btn .change-summary {
		margin: 0;
		font-size: 13px;
	}

	/* ===== MARKDOWN VIEWER PANEL ===== */
	.markdown-viewer-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		height: fit-content;
		max-height: calc(100vh - 280px);
		overflow-y: auto;
		position: sticky;
		top: 20px;
		align-self: flex-start;
	}
	.markdown-viewer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px;
		border-bottom: 1px solid var(--border);
		background: var(--bg);
		position: sticky;
		top: 0;
		z-index: 10;
	}
	.viewer-title-row {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.viewer-title-row h3 {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}
	.viewer-date {
		font-size: 12px;
		color: var(--text-muted);
	}
	.markdown-viewer-content {
		padding: 20px;
	}
	.markdown-body {
		font-size: 14px;
		line-height: 1.7;
		color: var(--text-primary);
	}
	.markdown-body .md-h2 {
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 12px 0;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}
	.markdown-body .md-h3 {
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 16px 0 8px 0;
	}
	.markdown-body .md-list-item {
		margin: 4px 0;
		padding-left: 16px;
		position: relative;
	}
	.markdown-body .md-list-item::before {
		content: '•';
		position: absolute;
		left: 0;
		color: var(--primary);
	}
	.markdown-body .md-numbered-item {
		margin: 4px 0;
		padding-left: 20px;
		position: relative;
	}
	.markdown-body .md-num {
		position: absolute;
		left: 0;
		color: var(--primary);
		font-weight: 500;
	}
	.markdown-body .md-nested-item {
		margin: 2px 0;
		padding-left: 32px;
		position: relative;
		color: var(--text-secondary);
	}
	.markdown-body .md-nested-item::before {
		content: '◦';
		position: absolute;
		left: 16px;
		color: var(--text-muted);
	}
	.markdown-body .md-bold {
		font-weight: 600;
		color: var(--text-primary);
	}
	.markdown-body .md-para {
		margin: 4px 0;
		color: var(--text-secondary);
	}
	.markdown-body .md-spacer {
		height: 8px;
	}
	.markdown-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 60px 20px;
		color: var(--text-muted);
	}
	.markdown-placeholder svg {
		margin-bottom: 16px;
		opacity: 0.5;
	}
	.markdown-placeholder p {
		font-size: 14px;
	}

	/* ===== MODE TABS ===== */
	.viewer-mode-tabs {
		display: flex;
		gap: 4px;
		background: var(--bg);
		padding: 3px;
		border-radius: 6px;
	}
	.mode-tab {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 5px 10px;
		font-size: 12px;
		font-weight: 500;
		color: var(--text-muted);
		background: transparent;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.15s;
	}
	.mode-tab:hover {
		color: var(--text-secondary);
	}
	.mode-tab.active {
		color: var(--text-primary);
		background: var(--surface);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}
	.mode-tab svg {
		opacity: 0.7;
	}
	.mode-tab.active svg {
		opacity: 1;
	}

	/* ===== MARKDOWN EDITOR ===== */
	.markdown-editor-content {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 360px);
		min-height: 300px;
	}
	.markdown-textarea {
		flex: 1;
		width: 100%;
		padding: 16px 20px;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 13px;
		line-height: 1.6;
		color: var(--text-primary);
		background: var(--surface);
		border: none;
		resize: none;
		outline: none;
	}
	.markdown-textarea::placeholder {
		color: var(--text-muted);
	}
	.editor-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		background: var(--bg);
		border-top: 1px solid var(--border);
	}
	.editor-hint {
		font-size: 12px;
		color: var(--text-muted);
	}
	.editor-actions {
		display: flex;
		gap: 8px;
	}

	.job-badge {
		font-size: 12px;
		color: var(--text-muted);
	}
	.version-num {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.job-meta {
		display: flex;
		gap: 24px;
		font-size: 13px;
		color: var(--text-secondary);
	}

	/* ===== TASK SECTION ===== */
	.task-section {
		margin-top: 24px;
	}
	.task-section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}
	.task-section h3 {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}
	.task-hint {
		font-size: 12px;
		color: var(--text-muted);
	}
	.task-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.task-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.task-header-btn {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
	}
	.task-number {
		width: 24px;
		height: 24px;
		background: var(--bg);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-secondary);
		flex-shrink: 0;
	}
	.task-title-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.task-name {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.task-agent {
		font-size: 11px;
		color: var(--text-muted);
	}
	.task-chevron {
		color: var(--text-muted);
		transition: transform 0.2s;
		flex-shrink: 0;
	}
	.task-chevron.rotated {
		transform: rotate(180deg);
	}
	.task-details {
		padding: 0 16px 16px 52px;
	}
	.task-desc {
		font-size: 13px;
		color: var(--text-secondary);
		margin-bottom: 8px;
		margin: 0 0 8px 0;
	}
	.task-meta-row {
		display: flex;
		gap: 16px;
		font-size: 12px;
		color: var(--text-muted);
		flex-wrap: wrap;
	}
	.task-meta-item {
		display: flex;
		gap: 4px;
	}

	/* ===== TASK SPLIT LAYOUT ===== */
	.task-section-split {
		display: grid;
		grid-template-columns: 1fr 380px;
		gap: 24px;
		margin-top: 24px;
	}
	.task-list-panel {
		min-width: 0;
	}
	.task-list-panel .task-list {
		max-height: 600px;
		overflow-y: auto;
	}
	.task-card-btn {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		cursor: pointer;
		text-align: left;
		transition: all 0.15s;
	}
	.task-card-btn:hover {
		border-color: var(--primary);
		background: #f8fafc;
	}
	.task-card-btn.selected {
		border-color: var(--primary);
		background: #eff6ff;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}
	.task-card-btn.selected .task-number {
		background: var(--primary);
		color: white;
	}

	/* ===== TASK INTERFACE PANEL ===== */
	.task-interface-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		height: fit-content;
		max-height: calc(100vh - 280px);
		overflow-y: auto;
		position: sticky;
		top: 20px;
		align-self: flex-start;
	}
	.interface-panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px;
		border-bottom: 1px solid var(--border);
		background: var(--bg);
	}
	.interface-panel-header h3 {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}
	.close-panel-btn {
		width: 28px;
		height: 28px;
		border-radius: 4px;
		border: none;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.close-panel-btn:hover {
		background: var(--border);
		color: var(--text-primary);
	}
	.interface-panel-content {
		padding: 16px;
	}
	.task-overview {
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--border);
	}
	.interface-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 60px 20px;
		color: var(--text-muted);
		text-align: center;
	}
	.interface-placeholder svg {
		margin-bottom: 12px;
		opacity: 0.4;
	}
	.interface-placeholder p {
		font-size: 13px;
		margin: 0;
	}

	/* ===== INTERFACE SCHEMA ===== */
	.interface-section {
		margin-bottom: 20px;
	}
	.interface-section:last-child {
		margin-bottom: 0;
	}
	.interface-section-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 12px;
	}
	.interface-section-header svg {
		color: var(--primary);
	}
	.interface-section-header h4 {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}
	.interface-schema {
		background: var(--bg);
		border-radius: 6px;
		padding: 12px;
	}
	.schema-type {
		font-size: 12px;
		color: var(--text-secondary);
		margin-bottom: 12px;
	}
	.schema-type code {
		background: var(--surface);
		padding: 2px 6px;
		border-radius: 4px;
		font-family: 'SF Mono', Monaco, monospace;
		font-size: 11px;
		color: var(--primary);
	}
	.properties-header {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		margin-bottom: 8px;
	}
	.schema-properties {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.property-item {
		padding: 8px;
		background: var(--surface);
		border-radius: 6px;
		border: 1px solid var(--border);
	}
	.property-name {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 4px;
	}
	.property-name code {
		font-family: 'SF Mono', Monaco, monospace;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.required-badge {
		font-size: 9px;
		font-weight: 600;
		text-transform: uppercase;
		padding: 2px 5px;
		background: #fee2e2;
		color: #dc2626;
		border-radius: 3px;
	}
	.property-type {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		align-items: center;
		margin-bottom: 4px;
	}
	.type-badge {
		font-size: 10px;
		font-weight: 500;
		padding: 2px 6px;
		background: #dbeafe;
		color: #1d4ed8;
		border-radius: 3px;
	}
	.enum-values {
		font-size: 10px;
		color: var(--text-muted);
	}
	.default-value {
		font-size: 10px;
		color: #059669;
		background: #d1fae5;
		padding: 2px 5px;
		border-radius: 3px;
	}
	.items-type {
		font-size: 10px;
		color: var(--text-muted);
	}
	.property-desc {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.4;
	}
	.no-interface {
		font-size: 12px;
		color: var(--text-muted);
		font-style: italic;
		padding: 12px;
		background: var(--bg);
		border-radius: 6px;
		text-align: center;
	}

	/* ===== RUNS TABLE ===== */
	.runs-summary {
		display: flex;
		gap: 16px;
		margin-bottom: 20px;
	}
	.summary-stat {
		flex: 1;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 16px;
		text-align: center;
	}
	.summary-stat.success {
		border-color: #22c55e;
	}
	.summary-stat.failed {
		border-color: #ef4444;
	}
	.summary-value {
		display: block;
		font-size: 24px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.summary-stat.success .summary-value {
		color: #22c55e;
	}
	.summary-stat.failed .summary-value {
		color: #ef4444;
	}
	.summary-label {
		font-size: 12px;
		color: var(--text-muted);
	}

	.runs-table {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.table-header {
		display: flex;
		padding: 12px 16px;
		background: var(--bg);
		border-bottom: 1px solid var(--border);
		font-size: 12px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
	}
	.table-row {
		display: flex;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
		align-items: center;
	}
	.table-row:last-child {
		border-bottom: none;
	}
	.table-row:hover {
		background: var(--bg);
	}
	.table-row.running {
		background: #eff6ff;
	}
	.table-row.failed {
		background: #fef2f2;
	}
	.th,
	.td {
		font-size: 13px;
	}
	.th.id,
	.td.id {
		width: 120px;
	}
	.th.version,
	.td.version {
		width: 100px;
	}
	.th.status,
	.td.status {
		width: 100px;
	}
	.th.progress,
	.td.progress {
		width: 140px;
	}
	.th.started,
	.td.started {
		flex: 1;
	}
	.th.duration,
	.td.duration {
		width: 100px;
	}
	.th.actions,
	.td.actions {
		width: 60px;
		text-align: center;
	}

	.run-link {
		color: var(--primary);
		background: none;
		border: none;
		cursor: pointer;
		font-size: 13px;
		font-weight: 500;
	}
	.run-link:hover {
		text-decoration: underline;
	}
	.version-tag {
		font-size: 12px;
		font-weight: 500;
		padding: 2px 6px;
		background: var(--bg);
		border-radius: 4px;
	}
	.mini-progress {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.mini-progress-bar {
		flex: 1;
		height: 6px;
		background: var(--border);
		border-radius: 3px;
		overflow: hidden;
	}
	.mini-progress-fill {
		height: 100%;
		border-radius: 3px;
	}
	.mini-progress-text {
		font-size: 11px;
		color: var(--text-muted);
		min-width: 40px;
	}
	.action-btn {
		width: 28px;
		height: 28px;
		border-radius: 4px;
		border: none;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.action-btn:hover {
		background: var(--border);
		color: var(--text-primary);
	}

	/* Pagination */
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		padding: 16px;
	}
	.page-btn {
		width: 32px;
		height: 32px;
		border-radius: 6px;
		border: 1px solid var(--border);
		background: var(--surface);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-secondary);
	}
	.page-btn:hover:not(:disabled) {
		background: var(--bg);
	}
	.page-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.page-numbers {
		display: flex;
		gap: 4px;
	}
	.page-num {
		width: 32px;
		height: 32px;
		border-radius: 6px;
		border: none;
		background: transparent;
		cursor: pointer;
		font-size: 13px;
		color: var(--text-secondary);
	}
	.page-num:hover {
		background: var(--bg);
	}
	.page-num.active {
		background: var(--primary);
		color: white;
	}
	.page-ellipsis {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		color: var(--text-muted);
	}
	.page-info {
		font-size: 13px;
		color: var(--text-muted);
		margin-left: 12px;
	}

	/* Run Detail View */
	.run-detail-view {
		max-width: 800px;
	}
	.detail-header {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-bottom: 20px;
	}
	.back-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		font-size: 13px;
	}
	.back-btn:hover {
		color: var(--primary);
	}
	.run-detail-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 24px;
	}
	.run-detail-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--border);
	}
	.run-detail-title {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.run-id-large {
		font-size: 18px;
		font-weight: 600;
	}
	.run-status-large {
		padding: 4px 12px;
		font-size: 12px;
	}
	.run-version-info {
		font-size: 14px;
		color: var(--text-secondary);
	}
	.run-stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
		margin-bottom: 20px;
	}
	.run-stat {
		text-align: center;
	}
	.run-stat .stat-label {
		display: block;
		font-size: 11px;
		color: var(--text-muted);
		margin-bottom: 4px;
	}
	.run-stat .stat-value {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.run-stat .stat-value.trace-link {
		color: var(--primary);
		font-family: monospace;
		font-size: 12px;
	}
	.run-progress-section {
		margin-bottom: 20px;
		padding: 16px;
		background: var(--bg);
		border-radius: 8px;
	}
	.progress-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 8px;
		font-size: 13px;
	}
	.progress-bar.large {
		height: 8px;
	}
	.current-task {
		font-size: 13px;
		color: var(--text-secondary);
		margin-top: 8px;
	}
	.run-error {
		padding: 12px;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 6px;
		color: #b91c1c;
		font-size: 13px;
		margin-bottom: 20px;
	}
	.run-actions {
		display: flex;
		gap: 8px;
	}

	/* ===== ANALYSIS ===== */
	.analysis-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
		margin-bottom: 24px;
	}
	.stat-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 20px;
		text-align: center;
	}
	.stat-card.primary {
		border-color: var(--primary);
	}
	.stat-card .stat-label {
		display: block;
		font-size: 12px;
		color: var(--text-muted);
		margin-bottom: 4px;
	}
	.stat-card .stat-value {
		font-size: 28px;
		font-weight: 600;
		color: var(--primary);
	}
	.stat-card .stat-value.failed {
		color: var(--danger);
	}

	.performance-section {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 20px;
		margin-bottom: 24px;
	}
	.performance-section h3 {
		font-size: 16px;
		font-weight: 600;
		margin-bottom: 16px;
	}
	.version-perf-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.version-perf-item {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.version-perf-item .version-label {
		width: 40px;
		font-weight: 500;
	}
	.perf-bar-container {
		flex: 1;
		height: 8px;
		background: var(--border);
		border-radius: 4px;
		overflow: hidden;
	}
	.perf-bar {
		height: 100%;
		background: var(--primary);
		border-radius: 4px;
	}
	.perf-value {
		width: 140px;
		font-size: 12px;
		color: var(--text-muted);
		text-align: right;
	}

	.trace-section {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 20px;
	}
	.trace-section h3 {
		font-size: 16px;
		font-weight: 600;
		margin-bottom: 8px;
	}
	.trace-section p {
		font-size: 14px;
		color: var(--text-secondary);
		margin-bottom: 12px;
	}

	/* ===== IMPROVE ===== */
	.improve-section,
	.current-req {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 20px;
		margin-bottom: 16px;
	}
	.improve-section h3,
	.current-req h3 {
		font-size: 16px;
		font-weight: 600;
		margin-bottom: 12px;
	}
	.improvement-list {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.improvement-list li {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 0;
		border-bottom: 1px solid var(--border);
		font-size: 14px;
	}
	.improvement-list li:last-child {
		border-bottom: none;
	}
	.priority {
		font-size: 10px;
		font-weight: 600;
		padding: 2px 6px;
		border-radius: 4px;
		text-transform: uppercase;
	}
	.improvement-list li.high .priority {
		background: #fee2e2;
		color: #b91c1c;
	}
	.improvement-list li.medium .priority {
		background: #fef3c7;
		color: #92400e;
	}
	.improvement-list li.low .priority {
		background: #dbeafe;
		color: #1e40af;
	}

	/* ===== SCHEDULE ===== */
	.schedule-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.schedule-card {
		transition: border-color 0.2s;
	}
	.schedule-card.enabled {
		border-color: #22c55e;
	}
	.schedule-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}
	.schedule-name {
		font-size: 15px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.toggle {
		position: relative;
		width: 44px;
		height: 24px;
	}
	.toggle input {
		opacity: 0;
		width: 0;
		height: 0;
	}
	.toggle-slider {
		position: absolute;
		inset: 0;
		background: var(--border);
		border-radius: 12px;
		cursor: pointer;
		transition: 0.3s;
	}
	.toggle-slider::before {
		content: '';
		position: absolute;
		width: 20px;
		height: 20px;
		left: 2px;
		bottom: 2px;
		background: white;
		border-radius: 50%;
		transition: 0.3s;
	}
	.toggle input:checked + .toggle-slider {
		background: #22c55e;
	}
	.toggle input:checked + .toggle-slider::before {
		transform: translateX(20px);
	}
	.schedule-details {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.schedule-meta {
		display: flex;
		gap: 12px;
		align-items: center;
	}
	.cron {
		font-family: monospace;
		font-size: 12px;
		background: var(--bg);
		padding: 4px 8px;
		border-radius: 4px;
	}
	.schedule-version {
		font-size: 12px;
		color: var(--text-muted);
	}
	.schedule-times {
		display: flex;
		gap: 16px;
		font-size: 12px;
		color: var(--text-secondary);
	}
	.next-run.disabled {
		color: var(--text-muted);
	}

	/* ===== GENERATE ===== */
	.source-info {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 12px;
	}
	.source-label {
		font-size: 13px;
		color: var(--text-secondary);
	}
	.source-version {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.source-status {
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
	}
	.generate-desc {
		font-size: 14px;
		color: var(--text-secondary);
		margin-bottom: 16px;
		line-height: 1.5;
	}
	.confirm-box {
		background: #fef3c7;
		border: 1px solid #fbbf24;
		border-radius: 8px;
		padding: 16px;
		margin-bottom: 16px;
	}
	.confirm-box p {
		font-size: 14px;
		margin-bottom: 12px;
	}
	.confirm-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}

	/* ===== NEXT ACTION BAR ===== */
	.next-action-bar {
		padding: 16px 24px;
		background: var(--surface);
		border-top: 1px solid var(--border);
		position: sticky;
		bottom: 0;
		z-index: 50;
		box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
	}
	.action-content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		max-width: 900px;
	}
	.action-text {
		font-size: 14px;
		color: var(--text-secondary);
	}

	/* ===== MODALS ===== */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	.modal {
		background: var(--surface);
		border-radius: 12px;
		width: 100%;
		max-width: 480px;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
	}
	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border);
	}
	.modal-header h3 {
		font-size: 16px;
		font-weight: 600;
	}
	.modal-close {
		width: 28px;
		height: 28px;
		border-radius: 6px;
		border: none;
		background: transparent;
		font-size: 20px;
		color: var(--text-muted);
		cursor: pointer;
	}
	.modal-close:hover {
		background: var(--bg);
	}
	.modal-body {
		padding: 20px;
	}
	.form-group {
		margin-bottom: 16px;
	}
	.form-group:last-child {
		margin-bottom: 0;
	}
	.form-group label {
		display: block;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
		margin-bottom: 6px;
	}
	.form-group input,
	.form-group textarea,
	.form-group select {
		width: 100%;
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 14px;
	}
	.form-group input:focus,
	.form-group textarea:focus,
	.form-group select:focus {
		outline: none;
		border-color: var(--primary);
	}
	.modal-footer {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
		padding: 16px 20px;
		border-top: 1px solid var(--border);
	}

	/* ===== OVERVIEW VIEW ===== */
	.overview-content {
		padding: 24px;
	}
	.overview-header {
		margin-bottom: 24px;
	}
	.overview-header h1 {
		font-size: 24px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.overview-subtitle {
		font-size: 14px;
		color: var(--text-secondary);
	}

	.overview-stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
		margin-bottom: 24px;
	}
	.stat-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 20px;
		display: flex;
		align-items: center;
		gap: 16px;
	}
	.stat-icon {
		width: 48px;
		height: 48px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.stat-icon.blue {
		background: #dbeafe;
		color: #2563eb;
	}
	.stat-icon.green {
		background: #dcfce7;
		color: #22c55e;
	}
	.stat-icon.red {
		background: #fee2e2;
		color: #ef4444;
	}
	.stat-icon.purple {
		background: #f3e8ff;
		color: #9333ea;
	}
	.stat-info {
		display: flex;
		flex-direction: column;
	}
	.stat-value {
		font-size: 24px;
		font-weight: 700;
		color: var(--text-primary);
	}
	.stat-label {
		font-size: 13px;
		color: var(--text-secondary);
	}

	.overview-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 24px;
	}
	.overview-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 20px;
	}
	.overview-panel.wide {
		grid-column: span 2;
	}
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 16px;
	}
	.panel-header h3 {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.btn-link {
		font-size: 13px;
		color: var(--primary);
		background: none;
		border: none;
		cursor: pointer;
	}
	.btn-link:hover {
		text-decoration: underline;
	}

	.activity-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.activity-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px;
		background: var(--bg);
		border-radius: 8px;
	}
	.activity-status {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.activity-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.activity-title {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.activity-time {
		font-size: 12px;
		color: var(--text-muted);
	}
	.activity-badge {
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
	}

	.workbench-overview-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.workbench-overview-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px;
		background: var(--bg);
		border-radius: 8px;
	}
	.wb-status-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.wb-overview-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.wb-overview-name {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.wb-overview-desc {
		font-size: 12px;
		color: var(--text-muted);
	}
	.wb-last-run {
		font-size: 11px;
		color: var(--text-muted);
		white-space: nowrap;
	}

	.chart-placeholder {
		padding: 20px 0;
	}
	.chart-bar-container {
		display: flex;
		align-items: flex-end;
		justify-content: space-around;
		height: 160px;
		padding: 0 20px;
	}
	.chart-bar-wrapper {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		flex: 1;
	}
	.chart-bar {
		width: 32px;
		background: linear-gradient(to top, #2563eb, #60a5fa);
		border-radius: 4px 4px 0 0;
		transition: height 0.3s;
	}
	.chart-label {
		font-size: 11px;
		color: var(--text-muted);
	}
	.chart-legend {
		display: flex;
		align-items: center;
		justify-content: center;
		margin-top: 16px;
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--text-secondary);
	}
	.legend-dot {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.legend-dot.success {
		background: #22c55e;
	}

	.upcoming-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.upcoming-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px;
		background: var(--bg);
		border-radius: 8px;
	}
	.upcoming-icon {
		color: var(--text-muted);
	}
	.upcoming-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.upcoming-name {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.upcoming-cron {
		font-size: 11px;
		font-family: monospace;
		color: var(--text-muted);
	}
	.upcoming-next {
		font-size: 12px;
		color: var(--primary);
		font-weight: 500;
	}

	/* ===== ALL RUNS VIEW ===== */
	.all-runs-content {
		padding: 24px;
	}
	.all-runs-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 20px;
	}
	.all-runs-header .header-left h1 {
		font-size: 24px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.all-runs-header .header-actions {
		display: flex;
		gap: 12px;
		align-items: center;
	}
	.search-box {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
	}
	.search-box svg {
		color: var(--text-muted);
	}
	.search-input {
		border: none;
		background: transparent;
		font-size: 14px;
		outline: none;
		width: 200px;
	}
	.filter-select {
		padding: 8px 12px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 14px;
		cursor: pointer;
	}

	.runs-stats-bar {
		display: flex;
		gap: 24px;
		padding: 16px 20px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		margin-bottom: 20px;
	}
	.runs-stat {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: 0 16px;
		border-right: 1px solid var(--border);
	}
	.runs-stat:last-child {
		border-right: none;
	}
	.runs-stat-value {
		font-size: 20px;
		font-weight: 700;
		color: var(--text-primary);
	}
	.runs-stat-label {
		font-size: 12px;
		color: var(--text-muted);
	}
	.runs-stat.success .runs-stat-value {
		color: #22c55e;
	}
	.runs-stat.failed .runs-stat-value {
		color: #ef4444;
	}
	.runs-stat.running .runs-stat-value {
		color: #3b82f6;
	}

	.runs-table-container {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
	}
	.runs-table {
		width: 100%;
		border-collapse: collapse;
	}
	.runs-table th {
		padding: 12px 16px;
		text-align: left;
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		color: var(--text-muted);
		background: var(--bg);
		border-bottom: 1px solid var(--border);
	}
	.runs-table td {
		padding: 14px 16px;
		border-bottom: 1px solid var(--border);
		font-size: 14px;
		color: var(--text-primary);
	}
	.runs-table tr:last-child td {
		border-bottom: none;
	}
	.runs-table tr.running {
		background: #eff6ff;
	}
	.run-id {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.run-id .mono {
		font-family: monospace;
		font-size: 13px;
	}
	.run-id .trace-id {
		font-size: 11px;
		color: var(--text-muted);
	}
	.version-tag {
		display: inline-block;
		padding: 2px 8px;
		background: var(--bg);
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
	}
	.status-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		border-radius: 16px;
		font-size: 12px;
		font-weight: 500;
		text-transform: uppercase;
	}
	.status-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid rgba(59, 130, 246, 0.3);
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.time-cell {
		font-size: 13px;
		color: var(--text-secondary);
	}
	.duration-cell {
		font-family: monospace;
		font-size: 13px;
	}
	.tasks-cell {
		width: 140px;
	}
	.tasks-progress {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.tasks-count {
		font-size: 12px;
		color: var(--text-secondary);
	}
	.tasks-bar {
		height: 4px;
		background: var(--bg);
		border-radius: 2px;
		overflow: hidden;
	}
	.tasks-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.3s;
	}
	.actions-cell {
		display: flex;
		gap: 4px;
	}
	.icon-btn-sm {
		width: 28px;
		height: 28px;
		border-radius: 6px;
		border: 1px solid var(--border);
		background: var(--surface);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-secondary);
	}
	.icon-btn-sm:hover {
		background: var(--bg);
		color: var(--text-primary);
	}
	.icon-btn-sm.error {
		border-color: #fca5a5;
		color: #ef4444;
	}

	.pagination {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 20px;
		padding: 12px 0;
	}
	.pagination-info {
		font-size: 13px;
		color: var(--text-secondary);
	}
	.pagination-controls {
		display: flex;
		gap: 4px;
	}
	.pagination-btn {
		padding: 8px 12px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 13px;
		cursor: pointer;
	}
	.pagination-btn:hover:not(:disabled) {
		background: var(--bg);
	}
	.pagination-btn.active {
		background: var(--primary);
		color: white;
		border-color: var(--primary);
	}
	.pagination-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.pagination-ellipsis {
		padding: 8px;
		color: var(--text-muted);
	}

	/* ===== SCHEDULES VIEW ===== */
	.schedules-content {
		padding: 24px;
	}
	.schedules-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 24px;
	}
	.schedules-header .header-left h1 {
		font-size: 24px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.schedules-count {
		font-size: 13px;
		color: var(--text-muted);
		margin-top: 4px;
		display: block;
	}

	.schedules-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 20px;
		margin-bottom: 24px;
	}
	.schedule-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
		transition:
			box-shadow 0.15s,
			border-color 0.15s;
	}
	.schedule-card:hover {
		border-color: var(--primary);
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
	}
	.schedule-card.disabled {
		opacity: 0.6;
	}
	.schedule-card-header {
		padding: 16px 20px;
		border-bottom: 1px solid var(--border);
	}
	.schedule-title-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 4px;
	}
	.schedule-card .schedule-name {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.schedule-card .schedule-version {
		font-size: 12px;
		color: var(--text-muted);
	}
	.toggle-switch {
		position: relative;
		display: inline-block;
		width: 40px;
		height: 22px;
	}
	.toggle-switch input {
		opacity: 0;
		width: 0;
		height: 0;
	}
	.toggle-switch .toggle-slider {
		position: absolute;
		cursor: pointer;
		inset: 0;
		background: var(--border);
		border-radius: 22px;
		transition: 0.3s;
	}
	.toggle-switch .toggle-slider::before {
		content: '';
		position: absolute;
		width: 18px;
		height: 18px;
		left: 2px;
		bottom: 2px;
		background: white;
		border-radius: 50%;
		transition: 0.3s;
	}
	.toggle-switch input:checked + .toggle-slider {
		background: #22c55e;
	}
	.toggle-switch input:checked + .toggle-slider::before {
		transform: translateX(18px);
	}
	.schedule-card-body {
		padding: 16px 20px;
	}
	.cron-display {
		margin-bottom: 16px;
	}
	.cron-display .cron-label {
		font-size: 12px;
		color: var(--text-muted);
		display: block;
		margin-bottom: 4px;
	}
	.cron-display .cron-value {
		font-family: monospace;
		font-size: 14px;
		background: var(--bg);
		padding: 8px 12px;
		border-radius: 6px;
		display: block;
	}
	.schedule-timing {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.timing-item {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
	}
	.timing-item svg {
		color: var(--text-muted);
		flex-shrink: 0;
	}
	.timing-label {
		color: var(--text-secondary);
		flex-shrink: 0;
	}
	.timing-value {
		color: var(--text-primary);
		font-weight: 500;
	}
	.schedule-card-footer {
		display: flex;
		gap: 8px;
		padding: 12px 20px;
		background: var(--bg);
		border-top: 1px solid var(--border);
	}
	.btn-ghost {
		padding: 6px 12px;
		background: transparent;
		border: none;
		color: var(--text-muted);
		font-size: 13px;
		cursor: pointer;
		border-radius: 6px;
	}
	.btn-ghost:hover {
		background: var(--surface);
		color: var(--danger);
	}

	.schedule-card.add-card {
		border: 2px dashed var(--border);
		background: transparent;
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 240px;
		cursor: pointer;
	}
	.schedule-card.add-card:hover {
		border-color: var(--primary);
		background: rgba(37, 99, 235, 0.02);
	}
	.add-card-content {
		text-align: center;
	}
	.add-icon {
		color: var(--text-muted);
		margin-bottom: 12px;
	}
	.add-text {
		display: block;
		font-size: 16px;
		font-weight: 500;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.add-hint {
		font-size: 13px;
		color: var(--text-muted);
	}

	.cron-help-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 20px;
	}
	.cron-help-panel h4 {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 16px;
	}
	.cron-examples {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 12px;
	}
	.cron-example {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: var(--bg);
		border-radius: 8px;
	}
	.cron-example code {
		font-family: monospace;
		font-size: 13px;
		background: var(--surface);
		padding: 4px 8px;
		border-radius: 4px;
	}
	.cron-example span {
		font-size: 13px;
		color: var(--text-secondary);
	}

	/* ===== VAULT SETTINGS VIEW ===== */
	.vault-content {
		padding: 24px;
		max-width: 1000px;
	}
	.vault-header {
		margin-bottom: 20px;
	}
	.vault-header h1 {
		font-size: 24px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.vault-subtitle {
		font-size: 14px;
		color: var(--text-secondary);
	}

	.warning-banner {
		display: flex;
		gap: 12px;
		padding: 16px;
		background: #fef3c7;
		border: 1px solid #fbbf24;
		border-radius: 12px;
		margin-bottom: 24px;
	}
	.warning-banner svg {
		color: #f59e0b;
		flex-shrink: 0;
		margin-top: 2px;
	}
	.warning-content strong {
		display: block;
		font-size: 14px;
		font-weight: 600;
		color: #92400e;
		margin-bottom: 2px;
	}
	.warning-content p {
		font-size: 13px;
		color: #92400e;
		margin: 0;
	}

	.secrets-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 20px;
		margin-bottom: 24px;
	}
	.secrets-section {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
	}
	.section-title-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border);
	}
	.section-icon {
		width: 40px;
		height: 40px;
		border-radius: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.section-icon.gmail {
		background: #fee2e2;
		color: #dc2626;
	}
	.section-icon.slack {
		background: #fef3c7;
		color: #d97706;
	}
	.section-icon.gemini {
		background: #dbeafe;
		color: #2563eb;
	}
	.section-icon.custom {
		background: #f3e8ff;
		color: #9333ea;
	}
	.section-title-info h3 {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.secret-status {
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
	}
	.secret-status.connected {
		color: #22c55e;
	}
	.secret-count {
		font-size: 12px;
		color: var(--text-muted);
	}

	.secrets-list {
		padding: 12px 20px;
	}
	.secret-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 0;
		border-bottom: 1px solid var(--border);
	}
	.secret-item:last-child {
		border-bottom: none;
	}
	.secret-key {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
		min-width: 180px;
	}
	.secret-value {
		flex: 1;
		font-size: 13px;
		font-family: monospace;
		color: var(--text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.secret-value.masked {
		letter-spacing: 2px;
	}
	.btn-icon {
		width: 28px;
		height: 28px;
		border-radius: 6px;
		border: none;
		background: transparent;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-muted);
	}
	.btn-icon:hover {
		background: var(--bg);
		color: var(--text-primary);
	}

	.secrets-section .section-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 20px;
		background: var(--bg);
		border-top: 1px solid var(--border);
	}
	.last-updated {
		font-size: 12px;
		color: var(--text-muted);
	}

	.vault-settings-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 20px;
	}
	.vault-settings-panel h3 {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 16px;
	}
	.settings-list {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.setting-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		background: var(--bg);
		border-radius: 8px;
	}
	.setting-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.setting-label {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.setting-desc {
		font-size: 12px;
		color: var(--text-muted);
	}

	/* ===== WORKBENCH CELL (All Runs Table) ===== */
	.workbench-cell {
		min-width: 160px;
	}
	.workbench-info-cell {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.wb-cell-name {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.wb-cell-project {
		font-size: 11px;
		color: var(--text-muted);
	}

	/* ===== SCHEDULE META ROW (Schedules Cards) ===== */
	.schedule-meta-row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}
	.schedule-workbench {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.schedule-workbench svg {
		color: var(--primary);
		flex-shrink: 0;
	}
	.schedule-project {
		font-size: 12px;
		color: var(--text-muted);
	}

	/* ===== WORKBENCH EDIT MODAL ===== */
	.modal-wide {
		max-width: 560px;
	}
	.form-static {
		font-size: 14px;
		color: var(--text-primary);
		margin: 0;
		padding: 10px 12px;
		background: var(--bg);
		border-radius: 6px;
	}
	.form-hint {
		font-size: 11px;
		color: var(--text-muted);
		margin-top: 4px;
		display: block;
	}
	.btn-danger-outline {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 8px 14px;
		background: transparent;
		border: 1px solid var(--danger);
		color: var(--danger);
		font-size: 14px;
		font-weight: 500;
		border-radius: 6px;
		cursor: pointer;
	}
	.btn-danger-outline:hover {
		background: #fef2f2;
	}
	.modal-actions-right {
		display: flex;
		gap: 8px;
		margin-left: auto;
	}
	.modal-footer {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 16px 20px;
		border-top: 1px solid var(--border);
	}
</style>
