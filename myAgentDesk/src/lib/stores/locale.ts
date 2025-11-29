/**
 * Locale Store - 多言語対応
 */

import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

export type Locale = 'ja' | 'en';

const STORAGE_KEY = 'myAgentDesk_locale';

// ブラウザの言語設定から初期ロケールを決定
function getInitialLocale(): Locale {
	if (!browser) return 'ja';

	// localStorageから読み込み
	const stored = localStorage.getItem(STORAGE_KEY);
	if (stored === 'ja' || stored === 'en') {
		return stored;
	}

	// ブラウザの言語設定を確認
	const browserLang = navigator.language.toLowerCase();
	if (browserLang.startsWith('ja')) {
		return 'ja';
	}
	return 'en';
}

// ロケールストア
export const locale = writable<Locale>(getInitialLocale());

// ロケール変更時にlocalStorageに保存
locale.subscribe((value) => {
	if (browser) {
		localStorage.setItem(STORAGE_KEY, value);
	}
});

// 翻訳辞書
const translations = {
	ja: {
		// Header
		'header.title': 'Defining Jobs via Requirement Clarification',
		'header.subtitle': '',
		'header.toggleSidebar': 'サイドバーを切り替え',

		// Sidebar
		'sidebar.newChat': '新しいジョブ',
		'sidebar.noConversations': 'まだ会話がありません。\n上のボタンから開始しましょう！',
		'sidebar.searchJobs': 'ジョブを検索...',
		'sidebar.noSearchResults': '検索結果が見つかりません',
		'sidebar.today': '今日',
		'sidebar.yesterday': '昨日',
		'sidebar.lastSevenDays': '過去7日間',
		'sidebar.older': 'それ以前',
		'sidebar.delete': '削除',
		'sidebar.deleteConfirm': 'この会話を削除しますか？',
		'sidebar.settings': '設定',

		// Settings
		'settings.title': '設定',
		'settings.language': '言語',
		'settings.languageDescription': '表示言語を選択してください',
		'settings.japanese': '日本語',
		'settings.english': 'English',
		'settings.backToChat': 'チャットに戻る',

		// Requirement Card
		'requirement.title': '現在の要求状態',
		'requirement.collapse': '折りたたむ',
		'requirement.expand': '展開',
		'requirement.dataSource': 'データソース',
		'requirement.outputFormat': '出力形式',
		'requirement.processDescription': '処理内容',
		'requirement.schedule': 'スケジュール',
		'requirement.undefined': '未定',
		'requirement.completeness': '完成度',
		'requirement.createJob': 'ジョブを作成',
		'requirement.creatingJob': 'ジョブ作成中...',
		'requirement.readyToCreate': 'ジョブ作成可能（80%以上）',
		'requirement.needsMore': 'ジョブ作成には80%以上の完成度が必要です',

		// Completeness Legend
		'legend.title': '完成度の目安',
		'legend.stage1': '0-25%: データソースのみ',
		'legend.stage2': '25-50%: データソース + 出力形式',
		'legend.stage3': '50-70%: 処理内容の一部が定義済み',
		'legend.stage4': '70-80%: ほぼ完成、詳細を確認中',
		'legend.stage5': '80%以上: すべて定義完了（作成可能）',

		// Chat
		'chat.startTitle': 'チャットを開始しましょう',
		'chat.startDescription':
			'実現したいことを自然な言葉で伝えてください。\nAIが要求を明確化し、ジョブを作成します。',
		'chat.placeholder': '例: 売上データを分析してExcelレポートを作成したい',
		'chat.send': '送信',
		'chat.sending': '送信中...',
		'chat.enterToSend': 'Enter で送信 / Shift + Enter で改行',
		'chat.composing': '（変換中）',

		// Timestamp
		'time.now': '今',
		'time.minutesAgo': '{0}分前',
		'time.hoursAgo': '{0}時間前',
		'time.yesterday': '昨日',
		'time.daysAgo': '{0}日前',

		// Error Messages
		'error.general': 'エラーが発生しました。もう一度お試しください。',
		'error.jobCreation': 'ジョブの作成に失敗しました。',

		// Alert Messages
		'alert.insufficientRequirements': '要求が十分に明確化されていません（現在: {0}%、必要: 80%）',
		'alert.noConversation': '会話が選択されていません',

		// Job Messages
		'job.createSuccess':
			'✅ ジョブを作成しました！\n\n**Job ID:** `{0}`\n**JobMaster ID:** `{1}`\n\nこのジョブはmySchedulerで管理されています。',

		// MLOps
		'mlops.dashboard': 'MLOps ダッシュボード',
		'mlops.chat': 'チャット',
		'mlops.diagnostics': '診断',
		'mlops.prompts': 'プロンプト',
		'mlops.connectionLive': 'ライブ',
		'mlops.connectionOffline': 'オフライン',
		'mlops.modelUsage': 'モデル使用分布',
		'mlops.averageScore': '平均スコア',
		'mlops.totalTurns': '総ターン数',
		'mlops.successRate': '成功率',
		'mlops.avgLatency': '平均レイテンシ',
		'mlops.totalSessions': '総セッション数',
		'mlops.completionRate': '完了率',
		'mlops.feedback': 'フィードバック',
		'mlops.confirm': '決定',
		'mlops.cancel': 'キャンセル',
		'mlops.submit': '送信',
		'mlops.requirementClarity': '要件の明確さ',
		'mlops.interpretationAccuracy': '解釈の正確さ',
		'mlops.responseHelpfulness': '回答の有用性',
		'mlops.overallSatisfaction': '総合満足度',
		'mlops.conversationDiagnostics': '会話診断',
		'mlops.promptManagement': 'プロンプト管理',
		'mlops.errorLoading': 'メトリクスの読み込みエラー',
		'mlops.lastUpdated': '最終更新',
		'mlops.qualityScoreAverage': '品質スコア平均',
		'mlops.conversationTurns': '会話ターン数',
		'mlops.successfulCompletions': '成功完了',
		'mlops.responseTime': '応答時間',
		'mlops.uniqueSessions': 'ユニークセッション',
		'mlops.requirementsCompleted': '要件完了',
		'mlops.requirementClarification': '要件明確化',
		'mlops.rateExperience': '体験を評価',
		'mlops.confirmedRequirements': '確定された要件',
		'mlops.dataSource': 'データソース',
		'mlops.process': '処理',
		'mlops.output': '出力',
		'mlops.schedule': 'スケジュール',
		'mlops.completeness': '完成度',
		'mlops.noActiveConversation': 'アクティブな会話がありません',
		'mlops.startNewConversation': 'ジョブ作成ページから新しい会話を開始してください。',
		'mlops.filterJobId': 'Job IDでフィルター',
		'mlops.filterUserId': 'User IDでフィルター',
		'mlops.applyFilter': 'フィルター適用',
		'mlops.conversationList': '会話一覧',
		'mlops.conversationDetail': '会話詳細',
		'mlops.selectConversation': '左の一覧から会話を選択してください',
		'mlops.promptTemplates': 'プロンプトテンプレート',
		'mlops.versions': 'バージョン',
		'mlops.selectPrompt': '左の一覧からプロンプトを選択してください',
		'mlops.selectVersion': 'バージョンを選択してください',
		'mlops.edit': '編集',
		'mlops.copy': 'コピー',
		'mlops.copied': 'コピーしました！',
		'mlops.active': 'アクティブ',
		'mlops.save': '保存',
		'mlops.preview': 'プレビュー',
		'mlops.selectInterpretation': '解釈を選択',
		'mlops.selectInterpretationDesc':
			'複数の解釈が見つかりました。意図に最も近いものを選択してください。',
		'mlops.noCandidates': '候補がありません',
		'mlops.confirmSelection': '選択を確定',
		'mlops.confirming': '確定中...',
		'mlops.confident': '確信度',
		'mlops.selected': '選択済み',
		'mlops.additionalComments': '追加コメント（任意）',
		'mlops.commentPlaceholder': '追加のフィードバックを入力...',
		'mlops.submitFeedback': 'フィードバックを送信',
		'mlops.submitting': '送信中...',
		'mlops.requirementClarityDesc': '明確化された要件はどの程度明確でしたか？',
		'mlops.interpretationAccuracyDesc': 'AIはあなたの意図をどの程度正確に理解しましたか？',
		'mlops.responseHelpfulnessDesc': 'AIの回答はどの程度役に立ちましたか？',
		'mlops.overallSatisfactionDesc': 'この会話全体の体験'
	},
	en: {
		// Header
		'header.title': 'Defining Jobs via Requirement Clarification',
		'header.subtitle': '',
		'header.toggleSidebar': 'Toggle sidebar',

		// Sidebar
		'sidebar.newChat': 'New Job',
		'sidebar.noConversations': 'No conversations yet.\nStart one with the button above!',
		'sidebar.searchJobs': 'Search jobs...',
		'sidebar.noSearchResults': 'No search results found',
		'sidebar.today': 'Today',
		'sidebar.yesterday': 'Yesterday',
		'sidebar.lastSevenDays': 'Last 7 Days',
		'sidebar.older': 'Older',
		'sidebar.delete': 'Delete',
		'sidebar.deleteConfirm': 'Delete this conversation?',
		'sidebar.settings': 'Settings',

		// Settings
		'settings.title': 'Settings',
		'settings.language': 'Language',
		'settings.languageDescription': 'Select your preferred language',
		'settings.japanese': '日本語',
		'settings.english': 'English',
		'settings.backToChat': 'Back to Chat',

		// Requirement Card
		'requirement.title': 'Current Requirements',
		'requirement.collapse': 'Collapse',
		'requirement.expand': 'Expand',
		'requirement.dataSource': 'Data Source',
		'requirement.outputFormat': 'Output Format',
		'requirement.processDescription': 'Process',
		'requirement.schedule': 'Schedule',
		'requirement.undefined': 'Undefined',
		'requirement.completeness': 'Completeness',
		'requirement.createJob': 'Create Job',
		'requirement.creatingJob': 'Creating Job...',
		'requirement.readyToCreate': 'Ready to create (80%+)',
		'requirement.needsMore': '80% completeness required to create job',

		// Completeness Legend
		'legend.title': 'Completeness Guide',
		'legend.stage1': '0-25%: Data source only',
		'legend.stage2': '25-50%: Data source + Output format',
		'legend.stage3': '50-70%: Partial process definition',
		'legend.stage4': '70-80%: Almost complete, verifying details',
		'legend.stage5': '80%+: All defined (Ready to create)',

		// Chat
		'chat.startTitle': "Let's start chatting",
		'chat.startDescription':
			'Tell us what you want to achieve in natural language.\nAI will clarify requirements and create a job.',
		'chat.placeholder': 'e.g., Analyze sales data and create an Excel report',
		'chat.send': 'Send',
		'chat.sending': 'Sending...',
		'chat.enterToSend': 'Enter to send / Shift + Enter for new line',
		'chat.composing': '(Composing)',

		// Timestamp
		'time.now': 'now',
		'time.minutesAgo': '{0}m ago',
		'time.hoursAgo': '{0}h ago',
		'time.yesterday': 'yesterday',
		'time.daysAgo': '{0}d ago',

		// Error Messages
		'error.general': 'An error occurred. Please try again.',
		'error.jobCreation': 'Failed to create job.',

		// Alert Messages
		'alert.insufficientRequirements':
			'Requirements are not sufficiently clarified (Current: {0}%, Required: 80%)',
		'alert.noConversation': 'No conversation selected',

		// Job Messages
		'job.createSuccess':
			'✅ Job created successfully!\n\n**Job ID:** `{0}`\n**JobMaster ID:** `{1}`\n\nThis job is managed by myScheduler.',

		// MLOps
		'mlops.dashboard': 'MLOps Dashboard',
		'mlops.chat': 'Chat',
		'mlops.diagnostics': 'Diagnostics',
		'mlops.prompts': 'Prompts',
		'mlops.connectionLive': 'Live',
		'mlops.connectionOffline': 'Offline',
		'mlops.modelUsage': 'Model Usage Distribution',
		'mlops.averageScore': 'Average Score',
		'mlops.totalTurns': 'Total Turns',
		'mlops.successRate': 'Success Rate',
		'mlops.avgLatency': 'Avg Latency',
		'mlops.totalSessions': 'Total Sessions',
		'mlops.completionRate': 'Completion Rate',
		'mlops.feedback': 'Feedback',
		'mlops.confirm': 'Confirm',
		'mlops.cancel': 'Cancel',
		'mlops.submit': 'Submit',
		'mlops.requirementClarity': 'Requirement Clarity',
		'mlops.interpretationAccuracy': 'Interpretation Accuracy',
		'mlops.responseHelpfulness': 'Response Helpfulness',
		'mlops.overallSatisfaction': 'Overall Satisfaction',
		'mlops.conversationDiagnostics': 'Conversation Diagnostics',
		'mlops.promptManagement': 'Prompt Management',
		'mlops.errorLoading': 'Error loading metrics',
		'mlops.lastUpdated': 'Last updated',
		'mlops.qualityScoreAverage': 'Quality score average',
		'mlops.conversationTurns': 'Conversation turns',
		'mlops.successfulCompletions': 'Successful completions',
		'mlops.responseTime': 'Response time',
		'mlops.uniqueSessions': 'Unique sessions',
		'mlops.requirementsCompleted': 'Requirements completed',
		'mlops.requirementClarification': 'Requirement Clarification',
		'mlops.rateExperience': 'Rate Experience',
		'mlops.confirmedRequirements': 'Confirmed Requirements',
		'mlops.dataSource': 'Data Source',
		'mlops.process': 'Process',
		'mlops.output': 'Output',
		'mlops.schedule': 'Schedule',
		'mlops.completeness': 'Completeness',
		'mlops.noActiveConversation': 'No active conversation',
		'mlops.startNewConversation': 'Start a new conversation from the job creation page.',
		'mlops.filterJobId': 'Filter by Job ID',
		'mlops.filterUserId': 'Filter by User ID',
		'mlops.applyFilter': 'Apply Filter',
		'mlops.conversationList': 'Conversation List',
		'mlops.conversationDetail': 'Conversation Detail',
		'mlops.selectConversation': 'Select a conversation from the list',
		'mlops.promptTemplates': 'Prompt Templates',
		'mlops.versions': 'Versions',
		'mlops.selectPrompt': 'Select a prompt from the list',
		'mlops.selectVersion': 'Select a version',
		'mlops.edit': 'Edit',
		'mlops.copy': 'Copy',
		'mlops.copied': 'Copied!',
		'mlops.active': 'Active',
		'mlops.save': 'Save',
		'mlops.preview': 'Preview',
		'mlops.selectInterpretation': 'Select an Interpretation',
		'mlops.selectInterpretationDesc':
			'We found multiple ways to interpret your request. Please select the one that best matches your intent.',
		'mlops.noCandidates': 'No candidates available',
		'mlops.confirmSelection': 'Confirm Selection',
		'mlops.confirming': 'Confirming...',
		'mlops.confident': 'confident',
		'mlops.selected': 'Selected',
		'mlops.additionalComments': 'Additional Comments (Optional)',
		'mlops.commentPlaceholder': 'Share any additional feedback...',
		'mlops.submitFeedback': 'Submit Feedback',
		'mlops.submitting': 'Submitting...',
		'mlops.requirementClarityDesc': 'How clear were the clarified requirements?',
		'mlops.interpretationAccuracyDesc': 'How accurately did the AI understand your intent?',
		'mlops.responseHelpfulnessDesc': "How helpful were the AI's responses?",
		'mlops.overallSatisfactionDesc': 'Your overall experience with this conversation'
	}
};

// 翻訳関数（リアクティブストアから現在の言語を取得）
export function t(key: string, ...args: (string | number)[]): string {
	const currentLocale = get(locale);
	let text = translations[currentLocale][key as keyof (typeof translations)['ja']];

	if (!text) {
		console.warn(`Translation key not found: ${key}`);
		return key;
	}

	// プレースホルダー置換 ({0}, {1}, ...)
	args.forEach((arg, index) => {
		text = text.replace(`{${index}}`, String(arg));
	});

	return text;
}
