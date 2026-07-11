<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Battle City: Code Arena</title>
	<meta
		name="description"
		content="Программируйте свой танк на Python в ремейке Battle City. Решайте головоломки, побеждайте AI и сражайтесь с другими игроками в PvP!"
	/>
</svelte:head>
{@render children()}
