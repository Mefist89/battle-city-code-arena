<script lang="ts">
	const maps = [
		{
			id: 1,
			title: 'Классическая арена',
			difficulty: 'Баланс',
			description: 'Симметричные укрепления и центральный квадрат для честного первого боя.',
			walls: ['3,1', '3,2', '3,5', '3,6', '6,1', '6,2', '6,5', '6,6', '4,3', '5,3', '4,4', '5,4'],
			color: 'border-secondary-fixed text-secondary-fixed'
		},
		{
			id: 2,
			title: 'Два коридора',
			difficulty: 'Тактика',
			description: 'Длинные линии огня и узкие проходы для точных выстрелов и засад.',
			walls: ['2,1', '2,2', '2,3', '7,4', '7,5', '7,6', '4,2', '5,2', '4,5', '5,5'],
			color: 'border-tertiary text-tertiary'
		},
		{
			id: 3,
			title: 'Разбитая крепость',
			difficulty: 'Сложная',
			description: 'Разрозненные укрытия требуют постоянно менять маршрут и направление атаки.',
			walls: ['3,1', '4,1', '5,2', '6,2', '2,4', '3,4', '6,5', '7,5', '4,6', '5,6'],
			color: 'border-error text-error'
		}
	];
</script>

<svelte:head><title>Карты Player vs Player — CodeCommand</title></svelte:head>

<div class="min-h-screen bg-surface text-on-surface">
	<header class="border-b-4 border-outline-variant bg-surface-container-low">
		<div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
			<a href="/" class="text-xl font-bold text-primary">← CODECOMMAND</a>
			<span class="text-sm tracking-widest text-error uppercase">Player vs Player</span>
		</div>
	</header>
	<main class="mx-auto max-w-6xl px-6 py-12">
		<p class="mb-3 text-sm font-bold tracking-widest text-tertiary uppercase">Выбор поля боя</p>
		<h1 class="mb-4 text-4xl font-bold text-primary uppercase md:text-6xl">Выбери PvP-карту</h1>
		<p class="mb-10 max-w-3xl text-on-surface-variant">
			Карта сохраняется в комнате. Оба игрока увидят одинаковые стены и будут сражаться на выбранной
			арене.
		</p>
		<div class="grid gap-7 md:grid-cols-3">
			{#each maps as map}
				<article
					class={`pixel-shadow flex flex-col border-4 bg-surface-container-low p-5 ${map.color}`}
				>
					<div
						class="mb-5 grid aspect-[10/8] grid-cols-10 overflow-hidden border-2 border-outline-variant bg-[#0a1118]"
					>
						{#each Array(80).keys() as index}
							{@const x = index % 10}
							{@const y = Math.floor(index / 10)}
							<div class="relative border border-[#242838]">
								{#if map.walls.includes(`${x},${y}`)}<div
										class="absolute inset-[2px] bg-tertiary"
									></div>{/if}
							</div>
						{/each}
					</div>
					<div class="mb-3 flex items-center justify-between">
						<span class="text-3xl font-bold">0{map.id}</span>
						<span class="border px-2 py-1 text-[10px] font-bold uppercase">{map.difficulty}</span>
					</div>
					<h2 class="mb-2 text-xl font-bold text-on-surface uppercase">{map.title}</h2>
					<p class="mb-6 text-sm text-on-surface-variant">{map.description}</p>
					<a
						href={`/pvp?map=${map.id}`}
						class="pixel-btn mt-auto block bg-primary-container px-5 py-3 text-center font-bold text-on-primary-container uppercase"
						>Создать или войти</a
					>
				</article>
			{/each}
		</div>
	</main>
</div>
