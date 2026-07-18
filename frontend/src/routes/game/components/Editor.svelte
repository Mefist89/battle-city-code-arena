<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { basicSetup } from 'codemirror';
	import { Compartment, EditorState } from '@codemirror/state';
	import { EditorView, keymap } from '@codemirror/view';
	import { indentWithTab } from '@codemirror/commands';
	import { acceptCompletion, autocompletion } from '@codemirror/autocomplete';
	import { python } from '@codemirror/lang-python';
	import { syntaxTree } from '@codemirror/language';
	import { lintGutter, linter, type Diagnostic } from '@codemirror/lint';
	import { oneDark } from '@codemirror/theme-one-dark';
	import { t } from '$lib/i18n';
	import { SvelteMap } from 'svelte/reactivity';
	import {
		formatStrategy,
		STRATEGY_EXAMPLES,
		validateStrategy,
		type StrategyIssue
	} from '$lib/editor/strategyTools';

	interface Props {
		code?: string;
		cursorInfo?: string;
		mode?: 'mission' | 'challenge' | 'pvp' | 'tutorial';
		readOnly?: boolean;
	}

	type SavedStrategy = { id: string; name: string; code: string; updatedAt: string };

	let {
		code = $bindable(''),
		// eslint-disable-next-line no-useless-assignment
		cursorInfo = $bindable('Ln 1, Col 1'),
		mode = 'mission',
		readOnly = false
	}: Props = $props();
	let editorDiv: HTMLDivElement | null = $state(null);
	let cmView: EditorView | null = null;
	let issues = $state<StrategyIssue[]>([]);
	let savedStrategies = $state<SavedStrategy[]>([]);
	let selectedStrategyId = $state('');
	let strategyName = $state('');
	let selectedExample = $state<'if' | 'for' | 'while' | 'scan'>('if');
	const editable = new Compartment();
	const storageKey = $derived(`codetank-strategies-${mode}`);
	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

	const retroTheme = EditorView.theme(
		{
			'&': {
				height: '100%',
				width: '100%',
				fontSize: '13px',
				fontFamily: "'Space Mono', monospace",
				backgroundColor: '#1c1b1b'
			},
			'.cm-content': { padding: '14px 0', caretColor: '#72ff70' },
			'.cm-cursor': { borderLeftColor: '#72ff70', borderLeftWidth: '2px' },
			'&.cm-focused': { outline: 'none' },
			'.cm-gutters': {
				backgroundColor: '#131313',
				color: '#696c7d',
				borderRight: '2px solid #434656'
			},
			'.cm-activeLine, .cm-activeLineGutter': { backgroundColor: '#20201f' },
			'.cm-scroller': { fontFamily: "'Space Mono', monospace", lineHeight: '1.7' },
			'.cm-tooltip': { border: '2px solid #434656', borderRadius: '0' },
			'.cm-tooltip-autocomplete > ul > li[aria-selected]': {
				backgroundColor: '#2e5bff',
				color: '#efefff'
			},
			'.cm-diagnostic-error': { borderLeftColor: '#ffb4ab' },
			'.cm-lintRange-error': { backgroundImage: 'none', borderBottom: '2px solid #ff5449' }
		},
		{ dark: true }
	);

	const commandCompletion = autocompletion({
		override: [
			(context) => {
				const word = context.matchBefore(/\w*/);
				if (!word || (word.from === word.to && !context.explicit)) return null;
				return {
					from: word.from,
					options: [
						{ label: 'move', type: 'function', detail: '()', apply: 'move()' },
						{
							label: 'rotate LEFT',
							type: 'function',
							detail: "('LEFT')",
							apply: "rotate('LEFT')"
						},
						{
							label: 'rotate RIGHT',
							type: 'function',
							detail: "('RIGHT')",
							apply: "rotate('RIGHT')"
						},
						{ label: 'scan', type: 'function', detail: '()', apply: 'scan()' },
						{ label: 'fire', type: 'function', detail: '()', apply: 'fire()' },
						{
							label: 'if scan',
							type: 'keyword',
							apply: "if scan():\n    fire()\nelse:\n    rotate('RIGHT')"
						},
						{
							label: 'for range',
							type: 'keyword',
							apply: 'for i in range(3):\n    move()'
						},
						{
							label: 'while scan',
							type: 'keyword',
							apply: 'while scan():\n    fire()'
						}
					]
				};
			}
		]
	});

	function diagnostics(state: EditorState): Diagnostic[] {
		const found: Diagnostic[] = validateStrategy(state.doc.toString()).map((issue) => {
			const line = state.doc.line(Math.min(issue.line, state.doc.lines));
			return {
				from: line.from,
				to: Math.min(state.doc.length, Math.max(line.from + 1, line.to)),
				severity: 'error' as const,
				message: issue.message
			};
		});
		syntaxTree(state).iterate({
			enter(node) {
				if (!node.type.isError) return;
				const position = Math.min(node.from, state.doc.length);
				const line = state.doc.lineAt(position);
				found.push({
					from: position,
					to: Math.min(state.doc.length, Math.max(node.to, position + 1)),
					severity: 'error',
					message: `Python syntax error on line ${line.number}`
				});
			}
		});
		return found;
	}

	function refreshIssues(state: EditorState) {
		const unique = new SvelteMap<string, StrategyIssue>();
		for (const item of diagnostics(state)) {
			const line = state.doc.lineAt(Math.min(item.from, state.doc.length)).number;
			unique.set(`${line}:${item.message}`, { line, message: item.message });
		}
		issues = [...unique.values()].sort((left, right) => left.line - right.line);
	}

	onMount(() => {
		try {
			const saved = JSON.parse(localStorage.getItem(storageKey) ?? '[]');
			if (Array.isArray(saved)) savedStrategies = saved.slice(0, 8);
		} catch {
			savedStrategies = [];
		}
		if (!editorDiv) return;
		const defaultDoc = [
			'# CODETANK ARENA — Level 01',
			'# Available commands:',
			"# move(), rotate('LEFT'), rotate('RIGHT'), scan(), fire()",
			'# Loops: for i in range(N): ...',
			'',
			''
		].join('\n');
		const startDoc = code.trim() ? code : defaultDoc;
		code = startDoc;
		const state = EditorState.create({
			doc: startDoc,
			extensions: [
				basicSetup,
				python(),
				oneDark,
				retroTheme,
				lintGutter(),
				linter((view) => diagnostics(view.state), { delay: 180 }),
				commandCompletion,
				keymap.of([{ key: 'Tab', run: acceptCompletion }, indentWithTab]),
				editable.of(EditorView.editable.of(!readOnly)),
				EditorView.updateListener.of((update) => {
					if (update.docChanged) {
						code = update.state.doc.toString();
						refreshIssues(update.state);
					}
					if (update.selectionSet) {
						const position = update.state.selection.main.head;
						const line = update.state.doc.lineAt(position);
						cursorInfo = `Ln ${line.number}, Col ${position - line.from + 1}`;
					}
				})
			]
		});
		cmView = new EditorView({ state, parent: editorDiv });
		refreshIssues(state);
		void loadRemoteStrategies();
	});

	$effect(() => {
		const locked = readOnly;
		if (cmView) {
			cmView.dispatch({ effects: editable.reconfigure(EditorView.editable.of(!locked)) });
		}
	});

	onDestroy(() => {
		cmView?.destroy();
		cmView = null;
	});

	export function insertAtCursor(text: string) {
		if (!cmView || readOnly) return;
		const range = cmView.state.selection.main;
		cmView.dispatch({
			changes: { from: range.from, to: range.to, insert: text },
			selection: { anchor: range.from + text.length }
		});
		cmView.focus();
	}

	export function clearCode() {
		if (!cmView || readOnly) return;
		cmView.dispatch({ changes: { from: 0, to: cmView.state.doc.length, insert: '' } });
	}

	export function setCode(nextCode: string) {
		if (!nextCode.trim()) return;
		code = nextCode;
		if (!cmView) return;
		cmView.dispatch({ changes: { from: 0, to: cmView.state.doc.length, insert: nextCode } });
	}

	export function getCode() {
		return cmView?.state.doc.toString() ?? code;
	}

	export function getErrors() {
		return issues;
	}

	function formatCode() {
		if (!readOnly) setCode(formatStrategy(getCode()));
	}

	function insertExample() {
		const example = STRATEGY_EXAMPLES.find((item) => item.id === selectedExample);
		if (example) insertAtCursor(`${example.code}\n`);
	}

	function persistStrategies(next: SavedStrategy[]) {
		savedStrategies = next.slice(0, 8);
		localStorage.setItem(storageKey, JSON.stringify(savedStrategies));
	}

	async function loadRemoteStrategies() {
		if (mode === 'tutorial') return;
		try {
			const response = await fetch(`${API}/auth/profile`, { credentials: 'include' });
			if (!response.ok) return;
			const profile = await response.json();
			const remote = profile.progress?.strategies?.[mode];
			if (!Array.isArray(remote)) return;
			const normalized = remote.slice(0, 8).map((item: Record<string, string>) => ({
				id: item.id,
				name: item.name,
				code: item.code,
				updatedAt: item.updated_at
			}));
			if (!normalized.length && savedStrategies.length) return;
			savedStrategies = normalized;
			localStorage.setItem(storageKey, JSON.stringify(normalized));
		} catch {
			// Local strategy cartridges remain available while offline.
		}
	}

	async function saveStrategy() {
		const currentCode = getCode();
		if (!currentCode.trim()) return;
		const name = strategyName.trim() || `${$t('editor.strategy')} ${savedStrategies.length + 1}`;
		const existing = savedStrategies.find((item) => item.name.toLowerCase() === name.toLowerCase());
		const saved: SavedStrategy = {
			id: existing?.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
			name,
			code: currentCode,
			updatedAt: new Date().toISOString()
		};
		persistStrategies([saved, ...savedStrategies.filter((item) => item.id !== saved.id)]);
		selectedStrategyId = saved.id;
		strategyName = '';
		if (mode === 'tutorial') return;
		try {
			const response = await fetch(`${API}/auth/strategies`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					...(new RegExp('^[a-f0-9]{12}$').test(saved.id) ? { id: saved.id } : {}),
					mode,
					name: saved.name,
					code: saved.code
				})
			});
			if (!response.ok) return;
			const payload = await response.json();
			const remote = payload.strategy;
			const synced = {
				id: remote.id,
				name: remote.name,
				code: remote.code,
				updatedAt: remote.updated_at
			};
			persistStrategies([synced, ...savedStrategies.filter((item) => item.id !== saved.id)]);
			selectedStrategyId = synced.id;
		} catch {
			// The locally saved copy can be synchronized on a later save.
		}
	}

	function loadStrategy() {
		const saved = savedStrategies.find((item) => item.id === selectedStrategyId);
		if (saved && !readOnly) setCode(saved.code);
	}

	async function deleteStrategy() {
		if (!selectedStrategyId) return;
		const deletingId = selectedStrategyId;
		persistStrategies(savedStrategies.filter((item) => item.id !== selectedStrategyId));
		selectedStrategyId = '';
		if (mode === 'tutorial' || !new RegExp('^[a-f0-9]{12}$').test(deletingId)) return;
		try {
			await fetch(`${API}/auth/strategies/${deletingId}`, {
				method: 'DELETE',
				credentials: 'include'
			});
		} catch {
			// The local delete remains useful if the server is temporarily offline.
		}
	}
</script>

<div class="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-[#131313]">
	<div
		class="strategy-rack flex flex-wrap items-center gap-2 border-b-2 border-outline-variant bg-surface-container-low px-2 py-2 text-[10px]"
	>
		<button type="button" onclick={formatCode} disabled={readOnly} class="tool-btn"
			>{$t('editor.format')}</button
		>
		<select
			bind:value={selectedExample}
			disabled={readOnly}
			aria-label={$t('editor.examples')}
			class="tool-select"
		>
			{#each STRATEGY_EXAMPLES as example}<option value={example.id}
					>{example.id.toUpperCase()}</option
				>{/each}
		</select>
		<button type="button" onclick={insertExample} disabled={readOnly} class="tool-btn"
			>+ {$t('editor.example')}</button
		>
		<span class="hidden h-5 w-px bg-outline-variant sm:block"></span>
		<input
			bind:value={strategyName}
			disabled={readOnly}
			maxlength="24"
			placeholder={$t('editor.strategyName')}
			class="tool-input"
		/>
		<button
			type="button"
			onclick={saveStrategy}
			disabled={readOnly || (savedStrategies.length >= 8 && !strategyName.trim())}
			class="tool-btn tool-save">{$t('editor.save')}</button
		>
		<select
			bind:value={selectedStrategyId}
			aria-label={$t('editor.savedStrategies')}
			class="tool-select min-w-32"
		>
			<option value="">{$t('editor.savedStrategies')} ({savedStrategies.length}/8)</option>
			{#each savedStrategies as strategy}<option value={strategy.id}>{strategy.name}</option>{/each}
		</select>
		<button
			type="button"
			onclick={loadStrategy}
			disabled={!selectedStrategyId || readOnly}
			class="tool-btn">{$t('editor.load')}</button
		>
		<button
			type="button"
			onclick={deleteStrategy}
			disabled={!selectedStrategyId}
			aria-label="Delete strategy"
			class="tool-btn tool-delete">×</button
		>
	</div>
	<div bind:this={editorDiv} class="min-h-0 min-w-0 flex-1 overflow-hidden"></div>
	<div
		class:error-active={issues.length > 0}
		class="flex min-h-7 items-center border-t-2 border-outline-variant bg-black px-3 py-1 text-[10px] text-secondary-fixed"
	>
		{#if issues.length}
			<span class="mr-2 text-error">● {$t('editor.line')} {issues[0].line}</span>
			<span class="truncate text-error">{issues[0].message}</span>
			{#if issues.length > 1}<span class="ml-auto shrink-0 text-error">+{issues.length - 1}</span
				>{/if}
		{:else}
			<span>● {$t('editor.codeReady')}</span>
		{/if}
	</div>
</div>

<style>
	.tool-btn,
	.tool-select,
	.tool-input {
		min-height: 28px;
		border: 1px solid #434656;
		background: #1c1b1b;
		padding: 4px 8px;
		color: #c6c5d8;
		font-family: 'Space Mono', monospace;
		text-transform: uppercase;
	}
	.tool-btn:hover:not(:disabled),
	.tool-select:focus,
	.tool-input:focus {
		border-color: #b9c3ff;
		color: #b9c3ff;
		outline: none;
	}
	.tool-btn:disabled {
		opacity: 0.35;
	}
	.tool-save {
		border-color: #72ff70;
		color: #72ff70;
	}
	.tool-delete {
		border-color: #ffb4ab;
		color: #ffb4ab;
	}
	.tool-input {
		width: 132px;
		text-transform: none;
	}
	.error-active {
		border-top-color: #ffb4ab;
	}
	@media (max-width: 640px) {
		.strategy-rack {
			max-height: 102px;
			overflow-y: auto;
		}
		.tool-input {
			width: 110px;
		}
	}
</style>
