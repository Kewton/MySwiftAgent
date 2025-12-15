# myAgentDesk デザインシステム

## 概要

本ドキュメントは myAgentDesk MVP のデザインシステムを定義します。

- **ライトモード**: Pattern A: Professional Blue（ビジネス向けの信頼感と清潔感）
- **ダークモード**: Pattern B: Dark Mode（開発者向けの目の疲労軽減）

ユーザーはシステム設定または手動でテーマを切り替えることができます。

---

## 1. カラーパレット

### 1.1 プライマリカラー（ライトモード）

| 名前 | HEX | RGB | 用途 |
|------|-----|-----|------|
| Primary | `#2563eb` | rgb(37, 99, 235) | メインアクション、アクティブ状態 |
| Primary Light | `#3b82f6` | rgb(59, 130, 246) | ホバー状態 |
| Primary Dark | `#1d4ed8` | rgb(29, 78, 216) | プレス状態 |

### 1.2 グレースケール

| 名前 | HEX | 用途 |
|------|-----|------|
| Gray 50 | `#f9fafb` | ページ背景 |
| Gray 100 | `#f3f4f6` | セクション背景、ホバー状態 |
| Gray 200 | `#e5e7eb` | ボーダー、区切り線 |
| Gray 300 | `#d1d5db` | 無効状態のボーダー |
| Gray 400 | `#9ca3af` | プレースホルダー、アイコン（muted） |
| Gray 500 | `#6b7280` | セカンダリテキスト |
| Gray 600 | `#4b5563` | ラベル |
| Gray 700 | `#374151` | 見出し |
| Gray 800 | `#1f2937` | 本文テキスト |
| Gray 900 | `#111827` | 強調テキスト |

### 1.3 セマンティックカラー

| 名前 | HEX | 背景色 | 用途 |
|------|-----|--------|------|
| Success | `#22c55e` | `#f0fdf4` | 成功、完了、アクティブ |
| Warning | `#f59e0b` | `#fffbeb` | 警告、ドラフト、注意 |
| Error | `#ef4444` | `#fef2f2` | エラー、失敗 |
| Info | `#3b82f6` | `#eff6ff` | 情報、進行中 |

### 1.4 サーフェス（ライトモード）

| 名前 | HEX | 用途 |
|------|-----|------|
| Background | `#f9fafb` | アプリ全体の背景 |
| Surface | `#ffffff` | カード、パネル、モーダル |
| Border | `#e5e7eb` | 標準のボーダー |

---

### 1.5 ダークモード カラーパレット

ダークモードは Pattern B: Dark Mode を採用。Indigo系アクセントカラーで視認性を確保。

#### 1.5.1 アクセントカラー（ダークモード）

| 名前 | HEX | RGB | 用途 |
|------|-----|-----|------|
| Accent | `#6366f1` | rgb(99, 102, 241) | メインアクション、アクティブ状態 |
| Accent Light | `#818cf8` | rgb(129, 140, 248) | ホバー状態、アイコンハイライト |
| Accent Dark | `#4f46e5` | rgb(79, 70, 229) | プレス状態 |

#### 1.5.2 ダークグレースケール

| 名前 | HEX | 用途 |
|------|-----|------|
| Dark 50 | `#fafafa` | 強調テキスト（白に近い） |
| Dark 100 | `#f4f4f5` | プライマリテキスト |
| Dark 200 | `#e4e4e7` | セカンダリテキスト |
| Dark 300 | `#d4d4d8` | 補助テキスト |
| Dark 400 | `#a1a1aa` | Mutedテキスト、プレースホルダー |
| Dark 500 | `#71717a` | 非アクティブアイコン |
| Dark 600 | `#52525b` | ボーダー（明るめ） |
| Dark 700 | `#3f3f46` | ボーダー（標準） |
| Dark 800 | `#27272a` | サーフェス（カード、パネル） |
| Dark 850 | `#1f1f23` | 入力フィールド背景 |
| Dark 900 | `#18181b` | サイドバー、ヘッダー背景 |
| Dark 950 | `#09090b` | アプリ全体の背景 |

#### 1.5.3 セマンティックカラー（ダークモード）

| 名前 | テキスト色 | 背景色 | 用途 |
|------|-----------|--------|------|
| Success | `#4ade80` | `#14532d` | 成功、完了、アクティブ |
| Warning | `#fbbf24` | `#713f12` | 警告、ドラフト、注意 |
| Error | `#f87171` | `#7f1d1d` | エラー、失敗 |
| Info | `#60a5fa` | `#1e3a5f` | 情報、進行中 |

#### 1.5.4 サーフェス（ダークモード）

| 名前 | HEX | 用途 |
|------|-----|------|
| Background | `#09090b` | アプリ全体の背景 |
| Surface | `#18181b` | サイドバー、ヘッダー |
| Surface Elevated | `#27272a` | カード、パネル、モーダル |
| Border | `#3f3f46` | 標準のボーダー |

---

## 2. タイポグラフィ

### 2.1 フォントファミリー

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             'Helvetica Neue', Arial, sans-serif;
```

### 2.2 フォントサイズスケール

| 名前 | サイズ | 行高 | 用途 |
|------|--------|------|------|
| xs | 11px | 1.4 | バッジ、キャプション |
| sm | 12px | 1.5 | メタ情報、補助テキスト |
| base | 14px | 1.5 | 本文、ナビゲーション |
| md | 15px | 1.5 | ロゴ、強調テキスト |
| lg | 16px | 1.5 | セクション見出し |
| xl | 18px | 1.4 | ページ見出し |

### 2.3 フォントウェイト

| 名前 | 値 | 用途 |
|------|-----|------|
| Normal | 400 | 本文 |
| Medium | 500 | ナビゲーション、ラベル |
| Semibold | 600 | 見出し、ボタン |
| Bold | 700 | 強調見出し |

---

## 3. スペーシング

### 3.1 基本単位

基本単位: **4px**

| 名前 | 値 | 用途 |
|------|-----|------|
| space-1 | 4px | アイコンとテキストの間隔 |
| space-2 | 8px | 小さな要素の内側余白 |
| space-3 | 12px | カード内のセクション間 |
| space-4 | 16px | カードの内側余白 |
| space-5 | 20px | セクション間の余白 |
| space-6 | 24px | メインコンテンツの余白 |
| space-8 | 32px | 大きなセクション間 |

### 3.2 レイアウト寸法

| 要素 | 値 |
|------|-----|
| Header高さ | 56px |
| Sidebar幅 | 240px |
| Action Bar高さ | 64px |
| カード間隔 | 16px |
| コンテンツ最大幅 | 1280px |

---

## 4. 角丸（Border Radius）

| 名前 | 値 | 用途 |
|------|-----|------|
| sm | 4px | バッジ、チェックボックス |
| md | 6px | ボタン、入力フィールド |
| lg | 8px | カード、パネル |
| xl | 12px | モーダル、ドロップダウン |
| full | 9999px | アバター、ピル型バッジ |

---

## 5. シャドウ

| 名前 | 値 | 用途 |
|------|-----|------|
| sm | `0 1px 2px rgba(0,0,0,0.05)` | カードホバー |
| md | `0 4px 6px -1px rgba(0,0,0,0.1)` | ドロップダウン |
| lg | `0 10px 15px -3px rgba(0,0,0,0.1)` | モーダル |

---

## 6. コンポーネント仕様

### 6.1 ボタン

#### Primary Button
```css
background: #2563eb;
color: #ffffff;
padding: 8px 16px;
border-radius: 6px;
font-size: 13px;
font-weight: 600;

/* Hover */
background: #1d4ed8;

/* Disabled */
background: #93c5fd;
cursor: not-allowed;
```

#### Secondary Button
```css
background: #ffffff;
color: #374151;
border: 1px solid #e5e7eb;
padding: 8px 16px;
border-radius: 6px;

/* Hover */
background: #f9fafb;
border-color: #d1d5db;
```

#### Ghost Button
```css
background: transparent;
color: #6b7280;
padding: 8px 16px;
border-radius: 6px;

/* Hover */
background: #f3f4f6;
color: #374151;
```

### 6.2 ステータスバッジ

```css
/* 共通 */
display: inline-flex;
align-items: center;
gap: 6px;
padding: 4px 10px;
border-radius: 6px;
font-size: 12px;
font-weight: 500;

/* Success */
background: #f0fdf4;
color: #15803d;

/* Warning */
background: #fffbeb;
color: #b45309;

/* Error */
background: #fef2f2;
color: #b91c1c;

/* Info */
background: #eff6ff;
color: #1d4ed8;

/* Neutral */
background: #f3f4f6;
color: #4b5563;
```

### 6.3 カード

```css
background: #ffffff;
border: 1px solid #e5e7eb;
border-radius: 8px;
padding: 16px;
transition: all 0.2s ease;

/* Hover */
border-color: #d1d5db;
box-shadow: 0 1px 2px rgba(0,0,0,0.05);
```

### 6.4 ナビゲーションアイテム

```css
/* Default */
display: flex;
align-items: center;
gap: 12px;
padding: 10px 12px;
border-radius: 8px;
font-size: 14px;
color: #4b5563;

/* Hover */
background: #f3f4f6;
color: #111827;

/* Active */
background: #2563eb;
color: #ffffff;
```

### 6.5 タブ

```css
/* Default */
padding: 14px 20px;
font-size: 14px;
color: #6b7280;
border-bottom: 2px solid transparent;

/* Hover */
color: #374151;

/* Active */
color: #2563eb;
border-bottom-color: #2563eb;
font-weight: 500;
```

### 6.6 入力フィールド

```css
background: #ffffff;
border: 1px solid #e5e7eb;
border-radius: 6px;
padding: 8px 12px;
font-size: 14px;
color: #1f2937;

/* Focus */
border-color: #2563eb;
outline: none;
box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);

/* Placeholder */
color: #9ca3af;
```

---

## 7. アイコン

### 7.1 アイコンライブラリ

**Lucide Icons** を採用（軽量・一貫性・SvelteKit対応）

```bash
npm install lucide-svelte
```

### 7.2 アイコンサイズ

| 名前 | サイズ | 用途 |
|------|--------|------|
| xs | 12px | バッジ内 |
| sm | 14px | ボタン内 |
| md | 16px | ナビゲーション |
| lg | 20px | ヘッダー |
| xl | 24px | 空状態 |

### 7.3 アイコン一覧（主要）

| アイコン | 名前 | 用途 |
|---------|------|------|
| LayoutDashboard | Dashboard | ダッシュボード |
| FileText | Workbench | ワークベンチ |
| Calendar | Schedule | スケジュール |
| History | History | 履歴 |
| Settings | Settings | 設定 |
| Play | Run | 実行 |
| Eye | View | 表示 |
| Edit | Edit | 編集 |
| Plus | Add | 追加 |
| Search | Search | 検索 |
| Bell | Notification | 通知 |
| ChevronRight | Navigate | 遷移 |
| Check | Complete | 完了 |

---

## 8. レイアウト構成

### 8.1 全体構造

```
+----------------------------------------------------------+
|                        Header (56px)                      |
+------------+---------------------------------------------+
|            |              Tab Navigation                  |
|  Sidebar   +---------------------------------------------+
|  (240px)   |                                             |
|            |              Content Area                    |
|            |                                             |
|            +---------------------------------------------+
|            |              Action Bar (64px)              |
+------------+---------------------------------------------+
```

### 8.2 レスポンシブブレークポイント

| 名前 | 幅 | 挙動 |
|------|-----|------|
| sm | < 640px | モバイル：Sidebar非表示、ハンバーガーメニュー |
| md | 640px - 1024px | タブレット：Sidebar折りたたみ（アイコンのみ） |
| lg | > 1024px | デスクトップ：フル表示 |

---

## 9. アニメーション

### 9.1 トランジション

```css
/* 標準 */
transition: all 0.2s ease;

/* 高速（ホバー） */
transition: all 0.15s ease;

/* 遅延（モーダル） */
transition: all 0.3s ease;
```

### 9.2 イージング

| 名前 | 値 | 用途 |
|------|-----|------|
| ease | `ease` | 標準 |
| ease-in | `ease-in` | 退出 |
| ease-out | `ease-out` | 進入 |
| ease-in-out | `ease-in-out` | 変形 |

---

## 10. アクセシビリティ

### 10.1 カラーコントラスト

すべてのテキストはWCAG 2.1 AA基準を満たす:
- 通常テキスト: 4.5:1 以上
- 大きなテキスト: 3:1 以上

### 10.2 フォーカス状態

```css
/* フォーカスリング */
outline: 2px solid #2563eb;
outline-offset: 2px;
```

### 10.3 キーボードナビゲーション

- Tab: フォーカス移動
- Enter/Space: アクション実行
- Escape: モーダル/ドロップダウン閉じる
- Arrow Keys: リスト内移動

---

## 11. CSS変数定義

SvelteKit での実装用CSS変数。テーマ切り替えに対応した構成。

### 11.1 共通変数（テーマ非依存）

```css
:root {
  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;

  /* Layout */
  --header-height: 56px;
  --sidebar-width: 240px;
  --action-bar-height: 64px;

  /* Transition */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.2s ease;
  --transition-slow: 0.3s ease;
}
```

### 11.2 ライトモード変数

```css
:root,
[data-theme="light"] {
  /* Primary */
  --color-primary: #2563eb;
  --color-primary-light: #3b82f6;
  --color-primary-dark: #1d4ed8;

  /* Gray Scale */
  --color-gray-50: #f9fafb;
  --color-gray-100: #f3f4f6;
  --color-gray-200: #e5e7eb;
  --color-gray-300: #d1d5db;
  --color-gray-400: #9ca3af;
  --color-gray-500: #6b7280;
  --color-gray-600: #4b5563;
  --color-gray-700: #374151;
  --color-gray-800: #1f2937;
  --color-gray-900: #111827;

  /* Semantic */
  --color-success: #22c55e;
  --color-success-bg: #f0fdf4;
  --color-warning: #f59e0b;
  --color-warning-bg: #fffbeb;
  --color-error: #ef4444;
  --color-error-bg: #fef2f2;
  --color-info: #3b82f6;
  --color-info-bg: #eff6ff;

  /* Surface */
  --color-background: #f9fafb;
  --color-surface: #ffffff;
  --color-surface-elevated: #ffffff;
  --color-border: #e5e7eb;

  /* Text */
  --color-text-primary: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-muted: #9ca3af;

  /* Shadow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1);

  /* Focus Ring */
  --color-focus-ring: rgba(37, 99, 235, 0.4);
}
```

### 11.3 ダークモード変数

```css
[data-theme="dark"] {
  /* Primary (Accent) */
  --color-primary: #6366f1;
  --color-primary-light: #818cf8;
  --color-primary-dark: #4f46e5;

  /* Dark Gray Scale */
  --color-gray-50: #fafafa;
  --color-gray-100: #f4f4f5;
  --color-gray-200: #e4e4e7;
  --color-gray-300: #d4d4d8;
  --color-gray-400: #a1a1aa;
  --color-gray-500: #71717a;
  --color-gray-600: #52525b;
  --color-gray-700: #3f3f46;
  --color-gray-800: #27272a;
  --color-gray-850: #1f1f23;
  --color-gray-900: #18181b;
  --color-gray-950: #09090b;

  /* Semantic */
  --color-success: #4ade80;
  --color-success-bg: #14532d;
  --color-warning: #fbbf24;
  --color-warning-bg: #713f12;
  --color-error: #f87171;
  --color-error-bg: #7f1d1d;
  --color-info: #60a5fa;
  --color-info-bg: #1e3a5f;

  /* Surface */
  --color-background: #09090b;
  --color-surface: #18181b;
  --color-surface-elevated: #27272a;
  --color-border: #3f3f46;

  /* Text */
  --color-text-primary: #f4f4f5;
  --color-text-secondary: #a1a1aa;
  --color-text-muted: #71717a;

  /* Shadow (darker for dark mode) */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.5);

  /* Focus Ring */
  --color-focus-ring: rgba(99, 102, 241, 0.4);
}

/* システム設定に従う場合 */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* ダークモード変数をここにも定義（上記と同じ） */
    --color-primary: #6366f1;
    --color-primary-light: #818cf8;
    --color-primary-dark: #4f46e5;
    --color-background: #09090b;
    --color-surface: #18181b;
    --color-surface-elevated: #27272a;
    --color-border: #3f3f46;
    --color-text-primary: #f4f4f5;
    --color-text-secondary: #a1a1aa;
    --color-text-muted: #71717a;
    --color-success: #4ade80;
    --color-success-bg: #14532d;
    --color-warning: #fbbf24;
    --color-warning-bg: #713f12;
    --color-error: #f87171;
    --color-error-bg: #7f1d1d;
    --color-info: #60a5fa;
    --color-info-bg: #1e3a5f;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.4);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.5);
    --color-focus-ring: rgba(99, 102, 241, 0.4);
  }
}
```

### 11.4 テーマ切り替え実装例（SvelteKit）

```typescript
// src/lib/stores/theme.ts
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

type Theme = 'light' | 'dark' | 'system';

function createThemeStore() {
  const stored = browser ? localStorage.getItem('theme') as Theme : 'system';
  const { subscribe, set } = writable<Theme>(stored || 'system');

  return {
    subscribe,
    set: (value: Theme) => {
      if (browser) {
        localStorage.setItem('theme', value);
        applyTheme(value);
      }
      set(value);
    },
  };
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === 'system') {
    root.removeAttribute('data-theme');
  } else {
    root.setAttribute('data-theme', theme);
  }
}

export const theme = createThemeStore();
```

```svelte
<!-- src/lib/components/ui/ThemeToggle.svelte -->
<script lang="ts">
  import { theme } from '$lib/stores/theme';
  import { Sun, Moon, Monitor } from 'lucide-svelte';
</script>

<div class="theme-toggle">
  <button
    class:active={$theme === 'light'}
    on:click={() => theme.set('light')}
    aria-label="ライトモード"
  >
    <Sun size={16} />
  </button>
  <button
    class:active={$theme === 'dark'}
    on:click={() => theme.set('dark')}
    aria-label="ダークモード"
  >
    <Moon size={16} />
  </button>
  <button
    class:active={$theme === 'system'}
    on:click={() => theme.set('system')}
    aria-label="システム設定に従う"
  >
    <Monitor size={16} />
  </button>
</div>
```

---

## 12. ファイル構成（実装参考）

```
src/
├── lib/
│   ├── styles/
│   │   ├── variables.css    # CSS変数定義
│   │   ├── reset.css        # リセットCSS
│   │   └── global.css       # グローバルスタイル
│   └── components/
│       ├── ui/
│       │   ├── Button.svelte
│       │   ├── Badge.svelte
│       │   ├── Card.svelte
│       │   ├── Input.svelte
│       │   └── Tabs.svelte
│       └── layout/
│           ├── Header.svelte
│           ├── Sidebar.svelte
│           └── ActionBar.svelte
└── routes/
    └── +layout.svelte       # ルートレイアウト
```

---

## 参照

- ワイヤーフレーム（ライト）: `wireframe-pattern-a-professional-blue.html`
- ワイヤーフレーム（ダーク）: `wireframe-pattern-b-dark-mode.html`
- E-R図: `er-diagram.md`
- 画面遷移図: `screen-transition.md`
- 要件定義: `requirements.md`
