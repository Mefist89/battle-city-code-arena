<script lang="ts">
	import { t } from '$lib/i18n';
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
		},
		{
			id: 7,
			title: 'Двойная угроза',
			difficulty: '2 противника',
			objective: 'Уничтожь два вражеских танка и достигни точки B (8,3).',
			hint: 'Следи за двумя направлениями атаки и используй стены как укрытие.',
			commands: 26,
			color: 'text-error',
			border: 'border-error'
		},
		{
			id: 8,
			title: 'Перекрёстный огонь',
			difficulty: '2 сильных врага',
			objective: 'Победи два танка, атакующих с разных сторон, и захвати B (8,3).',
			hint: "Используй scan(), условия и rotate('LEFT'/'RIGHT').",
			commands: 30,
			color: 'text-tertiary',
			border: 'border-tertiary'
		},
		{
			id: 9,
			title: 'Тройная осада',
			difficulty: '3 противника',
			objective: 'Уничтожь три вражеских танка и достигни последней точки B (8,3).',
			hint: 'Сначала уничтожь ближайшего врага, затем меняй позицию и линию огня.',
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
