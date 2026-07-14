<script lang="ts">
	import { locale, setLocale, type Locale } from '$lib/i18n';
	let { floating = true }: { floating?: boolean } = $props();

	function choose(value: Locale) {
		setLocale(value);
	}
</script>

<div
	class:fixed={floating}
	class:right-3={floating}
	class:bottom-3={floating}
	class:z-[200]={floating}
	class="flex shrink-0 border-2 border-outline-variant bg-surface-container-high p-1 shadow-[4px_4px_0_#000]"
	aria-label="Language"
>
	{#each ['ru', 'en'] as value}
		<button
			type="button"
			onclick={() => choose(value as Locale)}
			class:bg-primary={$locale === value}
			class:text-on-primary={$locale === value}
			class:text-on-surface-variant={$locale !== value}
			class="px-3 py-2 text-xs font-black uppercase"
			aria-pressed={$locale === value}>{value}</button
		>
	{/each}
</div>
