import { browser } from '$app/environment';
import { writable } from 'svelte/store';

interface LayoutState {
	darkMode: boolean;
	outerSidebarExpanded: boolean;
}

const STORAGE_KEY = 'myAgentDesk_layout';
const DEFAULT_STATE: LayoutState = {
	darkMode: false,
	outerSidebarExpanded: true
};

function prefersDarkMode(): boolean {
	if (!browser) return DEFAULT_STATE.darkMode;

	try {
		return typeof window.matchMedia === 'function'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
			: DEFAULT_STATE.darkMode;
	} catch (error) {
		console.warn('Failed to evaluate color scheme preference:', error);
		return DEFAULT_STATE.darkMode;
	}
}

function readStoredState(): LayoutState {
	if (!browser) return { ...DEFAULT_STATE };

	const state: LayoutState = { ...DEFAULT_STATE };

	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored) {
			const parsed = JSON.parse(stored) as Partial<LayoutState>;
			if (typeof parsed.darkMode === 'boolean') {
				state.darkMode = parsed.darkMode;
			} else {
				state.darkMode = prefersDarkMode();
			}
			if (typeof parsed.outerSidebarExpanded === 'boolean') {
				state.outerSidebarExpanded = parsed.outerSidebarExpanded;
			}
		} else {
			state.darkMode = prefersDarkMode();
		}
	} catch (error) {
		console.warn('Failed to read layout state from localStorage:', error);
		state.darkMode = prefersDarkMode();
	}

	return state;
}

function persistState(state: LayoutState) {
	if (!browser) return;

	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
	} catch (error) {
		console.warn('Failed to persist layout state to localStorage:', error);
	}
}

function applyDarkModeClass(state: LayoutState) {
	if (!browser) return;
	const root = document.documentElement;
	if (state.darkMode) {
		root.classList.add('dark');
	} else {
		root.classList.remove('dark');
	}
}

const layoutStoreInternal = writable<LayoutState>(readStoredState());

if (browser) {
	layoutStoreInternal.subscribe((state) => {
		persistState(state);
		applyDarkModeClass(state);
	});
}

export const layoutStore = layoutStoreInternal;

export function setDarkMode(value: boolean) {
	layoutStoreInternal.update((state) =>
		state.darkMode === value ? state : { ...state, darkMode: value }
	);
}

export function toggleDarkMode() {
	layoutStoreInternal.update((state) => ({ ...state, darkMode: !state.darkMode }));
}

export function setOuterSidebarExpanded(value: boolean) {
	layoutStoreInternal.update((state) =>
		state.outerSidebarExpanded === value ? state : { ...state, outerSidebarExpanded: value }
	);
}

export function toggleOuterSidebar() {
	layoutStoreInternal.update((state) => ({ ...state, outerSidebarExpanded: !state.outerSidebarExpanded }));
}

export type LayoutStore = typeof layoutStore;
