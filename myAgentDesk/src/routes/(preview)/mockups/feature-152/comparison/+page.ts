import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	return {
		patterns: [
			{
				id: 'pattern-a',
				name: 'パターンA: シンプル',
				description: '必要最小限の機能',
				icon: '🎯',
				scores: {
					ux: 9,
					features: 5,
					performance: 10,
					maintainability: 8
				},
				pros: ['高速読み込み', '使いやすい', 'モバイル最適', 'シンプル'],
				cons: ['機能制限', 'カスタマイズ性低']
			},
			{
				id: 'pattern-b',
				name: 'パターンB: 標準',
				description: '機能と使いやすさのバランス',
				icon: '⚖️',
				scores: {
					ux: 7,
					features: 7,
					performance: 7,
					maintainability: 9
				},
				pros: ['バランスが良い', '保守性高', '拡張性あり', '長期運用向き'],
				cons: ['特徴が薄い', '平凡']
			},
			{
				id: 'pattern-c',
				name: 'パターンC: リッチ',
				description: '全機能を網羅',
				icon: '⚡',
				scores: {
					ux: 5,
					features: 10,
					performance: 5,
					maintainability: 6
				},
				pros: ['全機能搭載', 'カスタマイズ性高', 'プロ向け', '詳細分析可能'],
				cons: ['複雑', '学習コスト高', '重い']
			},
			{
				id: 'pattern-d',
				name: 'パターンD: 革新的',
				description: 'AI・ABテスト搭載',
				icon: '🚀',
				scores: {
					ux: 8,
					features: 10,
					performance: 6,
					maintainability: 7
				},
				pros: ['革新的', '差別化', '最新技術', 'AI推奨機能'],
				cons: ['リスク高', '互換性', '学習曲線']
			}
		],
		featureComparison: [
			{
				name: '複数候補提示 (FR-1)',
				support: {
					'pattern-a': true,
					'pattern-b': true,
					'pattern-c': true,
					'pattern-d': true
				}
			},
			{
				name: 'フィードバック機能 (FR-2)',
				support: {
					'pattern-a': true,
					'pattern-b': true,
					'pattern-c': true,
					'pattern-d': true
				}
			},
			{
				name: '品質メトリクス表示 (FR-3)',
				support: {
					'pattern-a': false,
					'pattern-b': true,
					'pattern-c': true,
					'pattern-d': true
				}
			},
			{
				name: '診断情報取得 (FR-4)',
				support: {
					'pattern-a': false,
					'pattern-b': false,
					'pattern-c': true,
					'pattern-d': true
				}
			},
			{
				name: 'プロンプト管理 (FR-5)',
				support: {
					'pattern-a': false,
					'pattern-b': false,
					'pattern-c': true,
					'pattern-d': true
				}
			},
			{
				name: 'ABテスト機能 (FR-6)',
				support: {
					'pattern-a': false,
					'pattern-b': false,
					'pattern-c': false,
					'pattern-d': true
				}
			},
			{
				name: 'AI推奨システム',
				support: {
					'pattern-a': false,
					'pattern-b': false,
					'pattern-c': false,
					'pattern-d': true
				}
			},
			{
				name: 'リアルタイムダッシュボード',
				support: {
					'pattern-a': false,
					'pattern-b': false,
					'pattern-c': false,
					'pattern-d': true
				}
			}
		]
	};
};
