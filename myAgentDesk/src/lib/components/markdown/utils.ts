/**
 * Markdown Utilities
 * Issue #290: Requirements List and Version Management
 *
 * Centralized configuration for markdown rendering and sanitization.
 * Used by MarkdownViewer and MarkdownEditor components.
 */

/**
 * DOMPurify configuration for sanitizing HTML output.
 * Allows safe HTML tags commonly used in Markdown rendering.
 */
export const DOMPURIFY_CONFIG = {
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
	] as string[],
	ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'target', 'rel'] as string[],
	ALLOW_DATA_ATTR: false
};

/**
 * Marked configuration for GFM (GitHub Flavored Markdown) support.
 */
export const MARKED_OPTIONS = {
	gfm: true,
	breaks: true
} as const;
