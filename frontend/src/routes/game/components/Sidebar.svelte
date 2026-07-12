<script lang="ts">
	const COMMANDS = [
		{ insert: 'move()', label: 'move()', desc: 'Forward 1 unit', icon: '↑', color: '#ffb778' },
		{ insert: "rotate('RIGHT')", label: "rotate('RIGHT')", desc: 'Turn 90° right', icon: '↻', color: '#ffb778' },
		{ insert: "rotate('LEFT')", label: "rotate('LEFT')", desc: 'Turn 90° left', icon: '↺', color: '#ffb778' },
		{ insert: 'scan()', label: 'scan()', desc: 'Detect enemies', icon: '◎', color: '#b8c3ff' },
		{ insert: 'fire()', label: 'fire()', desc: 'Shoot cannon', icon: '⊕', color: '#ffb4ab' },
		{
			insert: 'if scan():\n    fire()',
			label: 'if',
			desc: 'Run when condition is true',
			icon: '?',
			color: '#72ff70'
		},
		{
			insert: 'while scan():\n    fire()',
			label: 'while',
			desc: 'Repeat while condition is true',
			icon: '∞',
			color: '#72ff70'
		},
		{
			insert: 'for i in range(3):\n    move()',
			label: 'for',
			desc: 'Repeat a fixed number',
			icon: '#',
			color: '#72ff70'
		}
	] as const;

	let { onInsertCommand }: { onInsertCommand: (cmd: string) => void } = $props();
</script>

<aside class="flex w-48 shrink-0 flex-col border-r-2 border-outline-variant bg-surface-container-low">
	<div class="border-b-2 border-outline-variant px-3 py-2 text-xs font-bold tracking-widest text-on-surface-variant uppercase">
		API COMMANDS
	</div>
	<div class="flex flex-col gap-0.5 overflow-y-auto p-2">
		{#each COMMANDS as cmd}
			<button
				onclick={() => onInsertCommand(cmd.insert)}
				title="Insert at cursor"
				class="group flex items-center gap-2 border-2 border-transparent p-2 text-left transition-all hover:border-outline-variant hover:bg-surface-container"
			>
				<span
					class="flex h-7 w-7 shrink-0 items-center justify-center border text-base font-bold"
					style="color:{cmd.color}; border-color:{cmd.color}40; background:{cmd.color}12;"
				>
					{cmd.icon}
				</span>
				<div>
					<div class="text-xs font-bold" style="color:{cmd.color};">{cmd.label}</div>
					<div class="text-[10px] text-on-surface-variant">{cmd.desc}</div>
				</div>
			</button>
		{/each}
	</div>
	<div class="mt-auto border-t-2 border-outline-variant p-3">
		<div class="mb-1 text-[10px] tracking-widest text-on-surface-variant uppercase">Loop syntax</div>
		<pre class="text-[10px] leading-relaxed text-secondary-fixed/70">for i in range(3):
    move()
    rotate('RIGHT')</pre>
	</div>
</aside>
