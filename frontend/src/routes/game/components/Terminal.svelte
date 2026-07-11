<script lang="ts">
	import type { LogEntry } from '../types';

	let { logs, isRunning }: { logs: LogEntry[]; isRunning: boolean } = $props();

	let logsEl: HTMLDivElement | null = $state(null);

	// Automatically scroll to bottom when logs change
	$effect(() => {
		if (logs && logsEl) {
			logsEl.scrollTop = logsEl.scrollHeight;
		}
	});

	function now() {
		return new Date().toLocaleTimeString('ru-RU', { hour12: false });
	}
</script>

<div class="flex h-32 shrink-0 flex-col bg-surface-container-low">
	<div
		class="flex shrink-0 items-center justify-between border-b-2 border-outline-variant bg-surface px-4 py-2 text-xs font-bold text-secondary-fixed"
	>
		<span>⬛ SYSTEM OUTPUT</span>
		<div
			class="h-2 w-2"
			class:animate-pulse={isRunning}
			class:bg-secondary-fixed={isRunning}
			class:bg-outline-variant={!isRunning}
		></div>
	</div>
	<div bind:this={logsEl} class="flex-1 overflow-auto p-4 leading-relaxed">
		{#each logs as log}
			<div class="flex gap-2 text-xs">
				<span class="shrink-0 text-on-surface-variant opacity-60">[{log.time}]</span>
				<span
					class:text-secondary-fixed={log.level === 'ok'}
					class:text-on-surface={log.level === 'info'}
					class:text-primary={log.level === 'cmd'}
					class:text-error={log.level === 'error'}
					class:text-tertiary={log.level === 'warn'}>{log.msg}</span
				>
			</div>
		{/each}
		<div class="mt-1 flex items-center gap-1 text-xs">
			<span class="text-on-surface-variant opacity-60">[{now()}]</span>
			<span class="inline-block h-4 w-2 animate-pulse bg-on-surface"></span>
		</div>
	</div>
</div>
