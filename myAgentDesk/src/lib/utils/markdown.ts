import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import type { Tokens } from 'marked';

let configured = false;

function ensureConfigured() {
	if (configured) return;

	marked.setOptions({
		breaks: true,
		gfm: true
	});

	marked.use({
		renderer: {
			code(token: Tokens.Code): string {
				const lang = (token.lang || '').trim();
				const highlighted =
					lang && hljs.getLanguage(lang)
						? hljs.highlight(token.text, { language: lang }).value
						: hljs.highlightAuto(token.text).value;
				const className = lang ? `hljs language-${lang}` : 'hljs';
				return `<pre><code class="${className}">${highlighted}</code></pre>`;
			}
		}
	});

	configured = true;
}

export function renderMarkdown(text: string): string {
	ensureConfigured();
	const html = marked.parse(text) as string;
	return DOMPurify.sanitize(html);
}
