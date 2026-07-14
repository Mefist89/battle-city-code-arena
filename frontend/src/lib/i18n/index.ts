import { browser } from '$app/environment';
import { derived, writable } from 'svelte/store';
import ru from './ru.json';
import en from './en.json';

export type Locale = 'ru' | 'en';
type Params = Record<string, string | number>;

const catalogs = { ru, en } as const;
export const locale = writable<Locale>('ru');

function lookup(catalog: unknown, key: string): string {
	let value: unknown = catalog;
	for (const part of key.split('.')) {
		if (!value || typeof value !== 'object' || !(part in value)) return key;
		value = (value as Record<string, unknown>)[part];
	}
	return typeof value === 'string' ? value : key;
}

export const t = derived(locale, ($locale) => (key: string, params: Params = {}) => {
	let text = lookup(catalogs[$locale], key);
	for (const [name, value] of Object.entries(params)) {
		text = text.replaceAll(`{${name}}`, String(value));
	}
	return text;
});

export function setLocale(value: Locale) {
	locale.set(value);
	if (browser) {
		localStorage.setItem('codetank-locale', value);
		document.documentElement.lang = value;
	}
}

export function initLocale() {
	if (!browser) return;
	const saved = localStorage.getItem('codetank-locale');
	const detected: Locale = navigator.language.toLowerCase().startsWith('ru') ? 'ru' : 'en';
	setLocale(saved === 'ru' || saved === 'en' ? saved : detected);
}
