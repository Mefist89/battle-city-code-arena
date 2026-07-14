<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	import { initLocale, t } from '$lib/i18n';

	let { children } = $props();
	onMount(initLocale);
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>CODETANK ARENA</title>
	<meta name="description" content={$t('home.meta')} />
</svelte:head>
{@render children()}
{#if page.url.pathname !== '/'}
	<LanguageSwitcher />
{/if}
