<script lang="ts">
	import { t } from '$lib/i18n';
	const maps = [
		{
			id: 1,
			title: 'Классическая арена',
			difficulty: 'Средняя',
			description: 'Симметричные укрепления и центральный квадрат.',
			walls: ['3,1', '3,2', '3,5', '3,6', '6,1', '6,2', '6,5', '6,6', '4,3', '5,3', '4,4', '5,4'],
			color: 'border-secondary-fixed text-secondary-fixed'
		},
		{
			id: 2,
			title: 'Два коридора',
			difficulty: 'Тактика',
			description: 'Длинные проходы и позиции для дальних выстрелов.',
			walls: ['2,1', '2,2', '2,3', '7,4', '7,5', '7,6', '4,2', '5,2', '4,5', '5,5'],
			color: 'border-tertiary text-tertiary'
		},
		{
			id: 3,
			title: 'Разбитая крепость',
			difficulty: 'Сложная',
			description: 'Разрозненные укрытия заставляют постоянно менять маршрут.',
			walls: ['3,1', '4,1', '5,2', '6,2', '2,4', '3,4', '6,5', '7,5', '4,6', '5,6'],
			color: 'border-error text-error'
		}
	];
</script>

<svelte:head><title>Карты Arena vs AI — CODETANK ARENA</title></svelte:head>

<div class="min-h-screen bg-surface text-on-surface">
	<header class="border-b-4 border-outline-variant bg-surface-container-low">
		<div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
			<a href="/" class="text-xl font-bold text-primary">{$t('common.backHome')}</a>
			<span class="text-sm tracking-widest text-error uppercase">Arena vs AI</span>
		</div>
	</header>
	<main class="mx-auto max-w-6xl px-6 py-12">
		<p class="mb-3 text-sm font-bold tracking-widest text-tertiary uppercase">
			{$t('maps.eyebrow')}
		</p>
		<h1 class="mb-4 text-4xl font-bold text-primary uppercase md:text-6xl">
			{$t('maps.challengeTitle')}
		</h1>
		<p class="mb-10 max-w-3xl text-on-surface-variant">{$t('maps.challengeIntro')}</p>
		<div class="grid gap-7 md:grid-cols-3">
			{#each maps as map}
				<article
					class={`pixel-shadow flex flex-col border-4 bg-surface-container-low p-5 ${map.color}`}
				>
					<div
						class="mb-5 grid aspect-[10/8] grid-cols-10 overflow-hidden border-2 border-outline-variant bg-[#0a1118]"
					>
						{#each Array(80).keys() as index}{@const x = index % 10}{@const y = Math.floor(
								index / 10
							)}
							<div class="relative border border-[#242838]">
								{#if map.walls.includes(`${x},${y}`)}<div
										class="absolute inset-[2px] bg-tertiary"
									></div>{/if}
							</div>
						{/each}
					</div>
					<div class="mb-3 flex items-center justify-between">
						<span class="text-3xl font-bold">0{map.id}</span><span
							class="border px-2 py-1 text-[10px] font-bold uppercase"
							>{$t(`maps.items.${map.id}.challengeDifficulty`)}</span
						>
					</div>
					<h2 class="mb-2 text-xl font-bold text-on-surface uppercase">
						{$t(`maps.items.${map.id}.title`)}
					</h2>
					<p class="mb-6 text-sm text-on-surface-variant">
						{$t(`maps.items.${map.id}.challengeDescription`)}
					</p>
					<a
						href={`/challenge?map=${map.id}`}
						class="pixel-btn mt-auto block bg-primary-container px-5 py-3 text-center font-bold text-on-primary-container uppercase"
						>{$t('maps.launch')}</a
					>
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
				<a href="/missions" class="text-on-surface-variant hover:text-primary"
					>{$t('common.missions')}</a
				>
				<a href="/challenge-maps" class="text-primary">{$t('common.challenge')}</a>
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
