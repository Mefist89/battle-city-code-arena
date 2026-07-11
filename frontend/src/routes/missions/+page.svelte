<script lang="ts">
	const missions = [
		{
			id: 1,
			title: 'Прямой маршрут',
			difficulty: 'Легко',
			objective: 'Доведи танк из A (1,6) в B (1,2).',
			hint: 'Используй move() и цикл range().',
			commands: 4,
			color: 'text-secondary-fixed',
			border: 'border-secondary-fixed'
		},
		{
			id: 2,
			title: 'Первый поворот',
			difficulty: 'Средне',
			objective: 'Доведи танк из A (1,6) в B (5,2).',
			hint: 'Сначала двигайся вверх, затем поверни направо.',
			commands: 9,
			color: 'text-tertiary',
			border: 'border-tertiary'
		},
		{
			id: 3,
			title: 'Маршрут командира',
			difficulty: 'Сложно',
			objective: 'Доведи танк из A (1,6) в B (8,1).',
			hint: 'Составь маршрут из двух циклов и одного поворота.',
			commands: 13,
			color: 'text-primary',
			border: 'border-primary'
		},
		{
			id: 4,
			title: 'Первый бой',
			difficulty: 'Бой',
			objective: 'Уничтожь красный танк и займи точку B (7,1).',
			hint: 'Используй scan(), поворот и два точных выстрела.',
			commands: 15,
			color: 'text-error',
			border: 'border-error'
		},
		{
			id: 5,
			title: 'Огневой коридор',
			difficulty: 'Тяжело',
			objective: 'Разрушь кирпичное укрытие, уничтожь врага и достигни B (8,2).',
			hint: 'Сталь не разрушается — ищи линию огня через кирпич.',
			commands: 18,
			color: 'text-tertiary',
			border: 'border-tertiary'
		},
		{
			id: 6,
			title: 'Стальная крепость',
			difficulty: 'Командир',
			objective: 'Победи усиленный танк с 150 HP и захвати B (8,1).',
			hint: 'Потребуется три попадания. Используй стены как укрытие.',
			commands: 22,
			color: 'text-primary',
			border: 'border-primary'
		}
	];
</script>

<svelte:head><title>Миссии — CodeCommand</title></svelte:head>

<div class="min-h-screen bg-surface text-on-surface">
	<header class="border-b-4 border-outline-variant bg-surface-container-low">
		<div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
			<a href="/" class="text-xl font-bold text-primary">← CODECOMMAND</a>
			<span class="text-sm tracking-widest text-secondary-fixed uppercase">Mission control</span>
		</div>
	</header>
	<main class="mx-auto max-w-6xl px-6 py-12">
		<div class="mb-10 max-w-3xl">
			<p class="mb-3 text-sm font-bold tracking-widest text-tertiary uppercase">Учебная кампания</p>
			<h1 class="mb-5 text-4xl font-bold text-primary uppercase md:text-6xl">Путь танкиста</h1>
			<p class="text-lg text-on-surface-variant">
				Напиши программу управления танком. В первых миссиях достигни точки B, а в боевых — сначала
				уничтожь противника.
			</p>
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
							>{mission.difficulty}</span
						>
					</div>
					<h2 class="mb-3 text-2xl font-bold uppercase">{mission.title}</h2>
					<p class="mb-5 text-sm text-on-surface-variant">{mission.objective}</p>
					<div
						class="mb-6 border-l-4 border-outline-variant bg-surface p-3 text-xs text-on-surface-variant"
					>
						&gt; {mission.hint}
					</div>
					<div class="mt-auto">
						<p class="mb-4 text-xs text-outline">Ориентир: {mission.commands} команд</p>
						<a
							href={`/game?mission=${mission.id}`}
							class="pixel-btn block bg-primary-container px-5 py-3 text-center font-bold text-on-primary-container uppercase"
							>Запустить миссию</a
						>
					</div>
				</article>
			{/each}
		</div>
	</main>
</div>
