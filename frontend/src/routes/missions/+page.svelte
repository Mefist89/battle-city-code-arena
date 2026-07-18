<script lang="ts">
	import { t } from '$lib/i18n';
	const missions = [
		{
			id: 1,
			commands: 4,
			color: 'text-secondary-fixed',
			border: 'border-secondary-fixed'
		},
		{
			id: 2,
			commands: 9,
			color: 'text-tertiary',
			border: 'border-tertiary'
		},
		{
			id: 3,
			commands: 13,
			color: 'text-primary',
			border: 'border-primary'
		},
		{
			id: 4,
			commands: 15,
			color: 'text-error',
			border: 'border-error'
		},
		{
			id: 5,
			commands: 18,
			color: 'text-tertiary',
			border: 'border-tertiary'
		},
		{
			id: 6,
			commands: 22,
			color: 'text-primary',
			border: 'border-primary'
		},
		{
			id: 7,
			commands: 26,
			color: 'text-error',
			border: 'border-error'
		},
		{
			id: 8,
			commands: 30,
			color: 'text-tertiary',
			border: 'border-tertiary'
		},
		{
			id: 9,
			commands: 36,
			color: 'text-primary',
			border: 'border-primary'
		}
	];
</script>

<svelte:head><title>{$t('missions.pageTitle')}</title></svelte:head>

<div class="min-h-screen bg-surface text-on-surface">
	<header class="border-b-4 border-outline-variant bg-surface-container-low">
		<div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
			<a href="/" class="text-xl font-bold text-primary">{$t('common.backHome')}</a>
			<span class="text-sm tracking-widest text-secondary-fixed uppercase"
				>{$t('missions.control')}</span
			>
		</div>
	</header>
	<main class="mx-auto max-w-6xl px-6 py-12">
		<div class="mb-10 max-w-3xl">
			<p class="mb-3 text-sm font-bold tracking-widest text-tertiary uppercase">
				{$t('missions.eyebrow')}
			</p>
			<h1 class="mb-5 text-4xl font-bold text-primary uppercase md:text-6xl">
				{$t('missions.title')}
			</h1>
			<p class="text-lg text-on-surface-variant">{$t('missions.intro')}</p>
		</div>
		<div class="grid gap-6 md:grid-cols-3">
			{#each missions as mission}
				<article
					class="pixel-shadow flex flex-col border-4 bg-surface-container-low p-6 {mission.border}"
				>
					<div class="mb-6 flex items-center justify-between">
						<span class="text-4xl font-bold {mission.color}">0{mission.id}</span>
						<span
							class="border-2 px-3 py-1 text-xs font-bold uppercase {mission.border} {mission.color}"
							>{$t(`missions.items.${mission.id}.difficulty`)}</span
						>
					</div>
					<h2 class="mb-3 text-2xl font-bold uppercase">
						{$t(`missions.items.${mission.id}.title`)}
					</h2>
					<p class="mb-5 text-sm text-on-surface-variant">
						{$t(`missions.items.${mission.id}.objective`)}
					</p>
					<div
						class="mb-6 border-l-4 border-outline-variant bg-surface p-3 text-xs text-on-surface-variant"
					>
						&gt; {$t(`missions.items.${mission.id}.hint`)}
					</div>
					<div class="mt-auto">
						<p class="mb-4 text-xs text-outline">
							{$t('missions.estimate', { count: mission.commands })}
						</p>
						<a
							href={`/game?mission=${mission.id}`}
							class="pixel-btn block bg-primary-container px-5 py-3 text-center font-bold text-on-primary-container uppercase"
							>{$t('missions.launch')}</a
						>
					</div>
				</article>
			{/each}
		</div>
	</main>

	<footer class="mt-14 border-t-4 border-outline-variant bg-surface-container-low">
		<div
			class="mx-auto flex max-w-[1280px] flex-col items-center justify-between gap-6 px-5 py-8 md:flex-row lg:px-8"
		>
			<a href="/" class="flex items-center gap-3" aria-label="CODETANK ARENA — Home">
				<span
					class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden border-2 border-outline-variant bg-black"
				>
					<img
						src="/assets/codetank-logo-mark-transparent.png"
						alt=""
						class="h-full w-full scale-[1.45] object-cover"
					/>
				</span>
				<span class="font-black text-primary uppercase">CODETANK ARENA</span>
			</a>
			<nav class="flex flex-wrap justify-center gap-5 text-xs uppercase" aria-label="Footer">
				<a href="/" class="text-on-surface-variant hover:text-primary">{$t('common.home')}</a>
				<a href="/missions" class="text-primary">{$t('common.missions')}</a>
				<a href="/challenge-maps" class="text-on-surface-variant hover:text-primary"
					>{$t('common.challenge')}</a
				>
				<a href="/pvp-maps" class="text-on-surface-variant hover:text-primary">{$t('common.pvp')}</a
				>
				<a href="/instruction" class="text-on-surface-variant hover:text-primary"
					>{$t('common.instruction')}</a
				>
			</nav>
			<div class="text-center text-[10px] font-bold text-tertiary uppercase md:text-right">
				{$t('common.copyright')}
			</div>
		</div>
	</footer>
</div>
