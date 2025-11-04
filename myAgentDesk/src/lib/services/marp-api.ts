/**
 * Marp Report API Service - expertAgent連携
 */

import { fetchJson } from './http';
import { ServiceError } from './types';

const EXPERTAGENT_API_BASE =
	import.meta.env.VITE_AGENT_API_BASE || 'http://localhost:8104/aiagent-api/v1';

export interface MarpReportRequest {
	job_id: string;
	format: 'html' | 'pdf' | 'png';
}

export interface MarpReportResponse {
	job_id: string;
	markdown: string; // 元のMarkdown
	html: string; // Marp生成済みHTML
	pdf_url: string | null; // PDFダウンロードURL
	png_urls: string[] | null; // 各スライドのPNG URL
	slide_count: number;
}

/**
 * Marpレポートを取得
 *
 * @param jobId - ジョブID
 * @param format - 出力形式 (html | pdf | png)
 * @returns Marpレポート
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function getMarpReport(
	jobId: string,
	format: 'html' | 'pdf' | 'png' = 'html'
): Promise<MarpReportResponse> {
	try {
		return await fetchJson<MarpReportResponse>({
			path: `/marp-report/${jobId}?format=${format}`,
			method: 'GET',
			baseUrl: EXPERTAGENT_API_BASE
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			const detail = (error.originalError as { detail?: string })?.detail || error.message;
			throw new ServiceError(`Failed to get Marp report: ${detail}`, error.statusCode, error);
		}
		throw new ServiceError('Failed to get Marp report', undefined, error);
	}
}

/**
 * Marpレポートのマークダウンを取得
 *
 * @param jobId - ジョブID
 * @returns マークダウンテキスト
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function getMarpMarkdown(jobId: string): Promise<string> {
	try {
		const report = await getMarpReport(jobId, 'html');
		return report.markdown;
	} catch (error) {
		if (error instanceof ServiceError) {
			throw new ServiceError(
				`Failed to get Marp markdown: ${error.message}`,
				error.statusCode,
				error
			);
		}
		throw new ServiceError('Failed to get Marp markdown', undefined, error);
	}
}

/**
 * MarpレポートのPDF URLを取得
 *
 * @param jobId - ジョブID
 * @returns PDF URL
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function getMarpPdfUrl(jobId: string): Promise<string> {
	try {
		const report = await getMarpReport(jobId, 'pdf');
		if (!report.pdf_url) {
			throw new ServiceError('PDF URL not available', 404);
		}
		return report.pdf_url;
	} catch (error) {
		if (error instanceof ServiceError) {
			throw new ServiceError(`Failed to get PDF URL: ${error.message}`, error.statusCode, error);
		}
		throw new ServiceError('Failed to get PDF URL', undefined, error);
	}
}

/**
 * MarpレポートのPNG URLsを取得
 *
 * @param jobId - ジョブID
 * @returns PNG URLs
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function getMarpPngUrls(jobId: string): Promise<string[]> {
	try {
		const report = await getMarpReport(jobId, 'png');
		if (!report.png_urls || report.png_urls.length === 0) {
			throw new ServiceError('PNG URLs not available', 404);
		}
		return report.png_urls;
	} catch (error) {
		if (error instanceof ServiceError) {
			throw new ServiceError(`Failed to get PNG URLs: ${error.message}`, error.statusCode, error);
		}
		throw new ServiceError('Failed to get PNG URLs', undefined, error);
	}
}
