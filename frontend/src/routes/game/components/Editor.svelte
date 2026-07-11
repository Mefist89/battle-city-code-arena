<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		EditorView,
		keymap,
		lineNumbers,
		highlightActiveLineGutter,
		highlightSpecialChars,
		drawSelection,
		dropCursor,
		rectangularSelection,
		crosshairCursor,
		highlightActiveLine
	} from '@codemirror/view';
	import { EditorState } from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
	import { python } from '@codemirror/lang-python';
	import {
		autocompletion,
		completionKeymap,
		closeBrackets,
		closeBracketsKeymap,
		acceptCompletion
	} from '@codemirror/autocomplete';
	import { oneDark } from '@codemirror/theme-one-dark';
	import {
		indentOnInput,
		syntaxHighlighting,
		defaultHighlightStyle,
		bracketMatching,
		foldGutter,
		foldKeymap
	} from '@codemirror/language';
	import { lintKeymap } from '@codemirror/lint';
	import { searchKeymap, highlightSelectionMatches } from '@codemirror/search';

	// ── State and Props ────────────────────────────────────────────────────────
	let { code = $bindable(''), cursorInfo = $bindable('Ln 1, Col 1') } = $props();

	let editorDiv: HTMLDivElement | null = $state(null);
	let cmView: EditorView | null = null;

	// ── Custom CodeMirror theme — Retro Pixel ─────────────────────────────────
	const retroTheme = EditorView.theme(
		{
			'&': {
				height: '100%',
				fontSize: '13px',
				fontFamily: "'Space Mono', monospace",
				backgroundColor: '#1c1b1b',
				color: '#e5e2e1'
			},
			'.cm-content': { padding: '16px 0', caretColor: '#72ff70' },
			'.cm-cursor': { borderLeftColor: '#72ff70', borderLeftWidth: '2px' },
			'.cm-focused .cm-cursor': { borderLeftColor: '#72ff70' },
			'&.cm-focused': { outline: 'none' },
			'.cm-gutters': {
				backgroundColor: '#131313',
				color: '#434656',
				border: 'none',
				borderRight: '2px solid #434656',
				minWidth: '3rem'
			},
			'.cm-gutter.cm-lineNumbers .cm-gutterElement': { paddingRight: '12px', paddingLeft: '8px' },
			'.cm-activeLineGutter': { backgroundColor: '#20201f', color: '#8e90a2' },
			'.cm-activeLine': { backgroundColor: '#20201f' },
			'.cm-selectionBackground, ::selection': { backgroundColor: '#2e5bff44' },
			'.cm-focused .cm-selectionBackground': { backgroundColor: '#2e5bff44' },
			'.cm-matchingBracket': {
				color: '#ffb778',
				borderBottom: '2px solid #ffb778',
				backgroundColor: 'transparent'
			},
			'.cm-tooltip': {
				backgroundColor: '#20201f',
				border: '2px solid #434656',
				borderRadius: '0',
				fontFamily: "'Space Mono', monospace",
				fontSize: '12px'
			},
			'.cm-tooltip-autocomplete > ul > li': { padding: '4px 8px' },
			'.cm-tooltip-autocomplete > ul > li[aria-selected]': {
				backgroundColor: '#2e5bff',
				color: '#efefff'
			},
			'.cm-completionIcon': { paddingRight: '6px' },
			'.cm-foldGutter': { width: '12px' },
			'.cm-scroller': { fontFamily: "'Space Mono', monospace", lineHeight: '1.7' },
			'.cm-searchMatch': { backgroundColor: '#ffb77833', outline: '1px solid #ffb778' },
			'.cm-searchMatch.cm-searchMatch-selected': { backgroundColor: '#ffb77866' }
		},
		{ dark: true }
	);

	// ── Python autocomplete hints ─────────────────────────────────────────────
	const tankCommands = autocompletion({
		override: [
			(ctx) => {
				const word = ctx.matchBefore(/\w*/);
				if (!word || (word.from === word.to && !ctx.explicit)) return null;
				return {
					from: word.from,
					options: [
						{
							label: 'move',
							type: 'function',
							info: 'Move tank forward 1 unit',
							detail: '()',
							apply: 'move()'
						},
						{
							label: 'rotate',
							type: 'function',
							info: 'Rotate tank 90° clockwise',
							detail: '()',
							apply: 'rotate()'
						},
						{
							label: 'scan',
							type: 'function',
							info: 'Scan for enemies in range',
							detail: '()',
							apply: 'scan()'
						},
						{
							label: 'fire',
							type: 'function',
							info: 'Fire cannon in tank direction',
							detail: '()',
							apply: 'fire()'
						}
					]
				};
			}
		]
	});

	// ── Init CodeMirror ───────────────────────────────────────────────────────
	onMount(() => {
		if (editorDiv) {
			const startDoc = `# Battle City: Code Arena — Level 01
# Available commands: move(), rotate(), scan(), fire()
# Loops: for i in range(N): ...

`;
			code = startDoc;

			const state = EditorState.create({
				doc: startDoc,
				extensions: [
					lineNumbers(),
					highlightActiveLineGutter(),
					highlightSpecialChars(),
					history(),
					foldGutter(),
					drawSelection(),
					dropCursor(),
					EditorState.allowMultipleSelections.of(true),
					indentOnInput(),
					syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
					bracketMatching(),
					closeBrackets(),
					rectangularSelection(),
					crosshairCursor(),
					highlightActiveLine(),
					highlightSelectionMatches(),
					keymap.of([
						{ key: 'Tab', run: acceptCompletion },
						...closeBracketsKeymap,
						...defaultKeymap,
						...searchKeymap,
						...historyKeymap,
						...foldKeymap,
						...completionKeymap.filter(
							(b: { key?: string }) => b.key !== 'Enter' && b.key !== 'Tab'
						),
						...lintKeymap,
						indentWithTab
					]),
					python(),
					oneDark,
					retroTheme,
					tankCommands,
					EditorView.updateListener.of((update) => {
						if (update.docChanged) {
							code = update.state.doc.toString();
						}
						if (update.selectionSet) {
							const pos = update.state.selection.main.head;
							const line = update.state.doc.lineAt(pos);
							const col = pos - line.from + 1;
							cursorInfo = `Ln ${line.number}, Col ${col}`;
						}
					})
				]
			});

			cmView = new EditorView({ state, parent: editorDiv });
		}
	});

	onDestroy(() => {
		cmView?.destroy();
		cmView = null;
	});

	// ── Public API ────────────────────────────────────────────────────────────
	export function insertAtCursor(text: string) {
		if (!cmView) return;
		const range = cmView.state.selection.main;
		cmView.dispatch({
			changes: { from: range.from, to: range.to, insert: text },
			selection: { anchor: range.from + text.length }
		});
		cmView.focus();
	}

	export function clearCode() {
		if (!cmView) return;
		cmView.dispatch({ changes: { from: 0, to: cmView.state.doc.length, insert: '' } });
	}

	export function getCode() {
		return cmView?.state.doc.toString() ?? '';
	}
</script>

<div bind:this={editorDiv} class="flex-1 overflow-hidden"></div>
