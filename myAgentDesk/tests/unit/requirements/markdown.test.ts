/**
 * Markdown Utility Tests
 * Issue #290: Requirements List and Version Management
 *
 * Tests for Markdown rendering and XSS protection.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { diff_match_patch } from 'diff-match-patch';

// Configure marked for GFM support (same as MarkdownViewer)
marked.setOptions({
	gfm: true,
	breaks: true
});

describe('Markdown Rendering', () => {
	it('should render basic markdown to HTML', async () => {
		const markdown = '# Hello World';
		const html = await marked.parse(markdown);

		expect(html).toContain('<h1>');
		expect(html).toContain('Hello World');
	});

	it('should render GFM tables', async () => {
		const markdown = `
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
`;
		const html = await marked.parse(markdown);

		expect(html).toContain('<table>');
		expect(html).toContain('<th>');
		expect(html).toContain('<td>');
	});

	it('should render GFM task lists', async () => {
		const markdown = `
- [x] Completed task
- [ ] Incomplete task
`;
		const html = await marked.parse(markdown);

		expect(html).toContain('<li>');
		expect(html).toContain('Completed task');
		expect(html).toContain('Incomplete task');
	});

	it('should render code blocks', async () => {
		const markdown = '```javascript\nconst x = 1;\n```';
		const html = await marked.parse(markdown);

		expect(html).toContain('<pre>');
		expect(html).toContain('<code');
		expect(html).toContain('const x = 1;');
	});

	it('should render inline code', async () => {
		const markdown = 'Use `const` for constants';
		const html = await marked.parse(markdown);

		expect(html).toContain('<code>');
		expect(html).toContain('const');
	});

	it('should render links', async () => {
		const markdown = '[Click here](https://example.com)';
		const html = await marked.parse(markdown);

		expect(html).toContain('<a');
		expect(html).toContain('href="https://example.com"');
		expect(html).toContain('Click here');
	});

	it('should render line breaks with breaks option', async () => {
		const markdown = 'Line 1\nLine 2';
		const html = await marked.parse(markdown);

		expect(html).toContain('<br');
	});
});

describe('XSS Protection (DOMPurify)', () => {
	const sanitize = (html: string) =>
		DOMPurify.sanitize(html, {
			ALLOWED_TAGS: [
				'h1',
				'h2',
				'h3',
				'h4',
				'h5',
				'h6',
				'p',
				'br',
				'strong',
				'em',
				'u',
				's',
				'del',
				'ins',
				'code',
				'pre',
				'blockquote',
				'ul',
				'ol',
				'li',
				'a',
				'img',
				'table',
				'thead',
				'tbody',
				'tr',
				'th',
				'td',
				'hr',
				'div',
				'span'
			],
			ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'target', 'rel'],
			ALLOW_DATA_ATTR: false
		});

	it('should remove script tags', () => {
		const malicious = '<script>alert("XSS")</script>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('<script');
		expect(clean).not.toContain('alert');
	});

	it('should remove onclick handlers', () => {
		const malicious = '<button onclick="alert(1)">Click me</button>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('onclick');
	});

	it('should remove javascript: URLs', () => {
		const malicious = '<a href="javascript:alert(1)">Click me</a>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('javascript:');
	});

	it('should remove onerror handlers', () => {
		const malicious = '<img src="x" onerror="alert(1)">';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('onerror');
	});

	it('should remove data: URLs by default', () => {
		const malicious = '<a href="data:text/html,<script>alert(1)</script>">Click</a>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('data:');
	});

	it('should remove style tags', () => {
		const malicious = '<style>body{display:none}</style>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('<style');
	});

	it('should allow safe HTML elements', () => {
		const safe = '<h1>Title</h1><p>Paragraph</p><strong>Bold</strong>';
		const clean = sanitize(safe);

		expect(clean).toContain('<h1>');
		expect(clean).toContain('<p>');
		expect(clean).toContain('<strong>');
	});

	it('should allow safe links', () => {
		const safe = '<a href="https://example.com" target="_blank">Link</a>';
		const clean = sanitize(safe);

		expect(clean).toContain('href="https://example.com"');
		expect(clean).toContain('target="_blank"');
	});

	it('should allow images with safe src', () => {
		const safe = '<img src="https://example.com/image.png" alt="Image">';
		const clean = sanitize(safe);

		expect(clean).toContain('src="https://example.com/image.png"');
		expect(clean).toContain('alt="Image"');
	});

	it('should handle nested XSS attempts', () => {
		const malicious = '<div><p onclick="alert(1)">Text<script>evil()</script></p></div>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('onclick');
		expect(clean).not.toContain('<script');
		expect(clean).toContain('<div>');
		expect(clean).toContain('<p>');
		expect(clean).toContain('Text');
	});

	it('should remove SVG with embedded scripts', () => {
		const malicious = '<svg onload="alert(1)"><script>evil()</script></svg>';
		const clean = sanitize(malicious);

		expect(clean).not.toContain('<svg');
		expect(clean).not.toContain('onload');
		expect(clean).not.toContain('<script');
	});
});

describe('Diff Computation', () => {
	let dmp: InstanceType<typeof diff_match_patch>;

	beforeEach(() => {
		dmp = new diff_match_patch();
	});

	it('should identify identical text as equal', () => {
		const text1 = 'Hello World';
		const text2 = 'Hello World';

		const diffs = dmp.diff_main(text1, text2);

		expect(diffs).toHaveLength(1);
		expect(diffs[0][0]).toBe(0); // DIFF_EQUAL
		expect(diffs[0][1]).toBe('Hello World');
	});

	it('should identify insertions', () => {
		const text1 = 'Hello';
		const text2 = 'Hello World';

		const diffs = dmp.diff_main(text1, text2);
		dmp.diff_cleanupSemantic(diffs);

		const hasInsertion = diffs.some((diff) => diff[0] === 1 && diff[1].includes('World'));
		expect(hasInsertion).toBe(true);
	});

	it('should identify deletions', () => {
		const text1 = 'Hello World';
		const text2 = 'Hello';

		const diffs = dmp.diff_main(text1, text2);
		dmp.diff_cleanupSemantic(diffs);

		const hasDeletion = diffs.some((diff) => diff[0] === -1 && diff[1].includes('World'));
		expect(hasDeletion).toBe(true);
	});

	it('should identify replacements as deletion + insertion', () => {
		const text1 = 'Hello World';
		const text2 = 'Hello Universe';

		const diffs = dmp.diff_main(text1, text2);
		dmp.diff_cleanupSemantic(diffs);

		const hasDeletion = diffs.some((diff) => diff[0] === -1);
		const hasInsertion = diffs.some((diff) => diff[0] === 1);

		expect(hasDeletion).toBe(true);
		expect(hasInsertion).toBe(true);
	});

	it('should handle multiline text', () => {
		const text1 = 'Line 1\nLine 2\nLine 3';
		const text2 = 'Line 1\nModified Line 2\nLine 3';

		const diffs = dmp.diff_main(text1, text2);
		dmp.diff_cleanupSemantic(diffs);

		// Should have equal parts for common text
		const hasEqual = diffs.some((diff) => diff[0] === 0);
		expect(hasEqual).toBe(true);
	});

	it('should handle completely different text', () => {
		const text1 = 'AAAA';
		const text2 = 'BBBB';

		const diffs = dmp.diff_main(text1, text2);

		const hasDeletion = diffs.some((diff) => diff[0] === -1);
		const hasInsertion = diffs.some((diff) => diff[0] === 1);

		expect(hasDeletion).toBe(true);
		expect(hasInsertion).toBe(true);
	});

	it('should handle empty strings', () => {
		const text1 = '';
		const text2 = 'New content';

		const diffs = dmp.diff_main(text1, text2);

		expect(diffs).toHaveLength(1);
		expect(diffs[0][0]).toBe(1); // DIFF_INSERT
		expect(diffs[0][1]).toBe('New content');
	});

	it('should clean up semantic diffs for readability', () => {
		const text1 = 'The quick brown fox';
		const text2 = 'The slow brown fox';

		const diffs = dmp.diff_main(text1, text2);
		const diffsBeforeCleanup = [...diffs];

		dmp.diff_cleanupSemantic(diffs);

		// Cleanup should consolidate small changes
		// The diff should show "quick" vs "slow" as a single change
		expect(diffs.length).toBeLessThanOrEqual(diffsBeforeCleanup.length);
	});
});
