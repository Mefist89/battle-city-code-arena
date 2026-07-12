<script lang="ts">
	const commands = [
		{
			name: 'move()',
			icon: '↑',
			color: '#ffb778',
			description: 'Перемещает танк на одну клетку вперёд в направлении ствола.',
			details: 'Танк не переместится, если впереди граница карты, стена или другой танк.',
			example: 'move()'
		},
		{
			name: "rotate('LEFT' | 'RIGHT')",
			icon: '↻',
			color: '#ffb778',
			description: 'Поворачивает танк на 90° в выбранную сторону.',
			details:
				"rotate('LEFT') поворачивает налево, rotate('RIGHT') — направо. Старый rotate() работает как поворот вправо.",
			example: "rotate('LEFT')\nrotate('RIGHT')"
		},
		{
			name: 'scan()',
			icon: '◎',
			color: '#b8c3ff',
			description: 'Проверяет, находится ли противник на линии огня.',
			details: 'Сканирование работает по горизонтали и вертикали. Стены перекрывают обзор.',
			example: 'if scan():\n    fire()'
		},
		{
			name: 'fire()',
			icon: '⊕',
			color: '#ffb4ab',
			description: 'Выпускает снаряд в направлении ствола танка.',
			details:
				'Снаряд наносит урон танку. Первый кирпичный блок на пути разрушается и останавливает пулю.',
			example: 'fire()'
		}
	];
</script>

<svelte:head>
	<title>Instruction — Battle City: Code Arena</title>
	<meta name="description" content="Полная инструкция по программированию и управлению танком" />
</svelte:head>

<div class="min-h-screen bg-surface font-mono text-on-surface">
	<header
		class="sticky top-0 z-10 flex h-16 items-center justify-between border-b-4 border-outline-variant bg-surface-container-low px-5 md:px-8"
	>
		<a href="/" class="font-bold text-primary hover:text-secondary-fixed">← CODECOMMAND</a>
		<div class="text-sm font-bold tracking-[0.2em] text-secondary-fixed uppercase">
			Instruction // Manual
		</div>
		<a
			href="/missions"
			class="border-2 border-primary px-3 py-1 text-xs font-bold text-primary hover:bg-primary hover:text-on-primary"
			>НАЧАТЬ</a
		>
	</header>

	<main class="mx-auto max-w-6xl px-5 py-10 md:px-8">
		<section class="mb-12 border-l-4 border-primary pl-5">
			<div class="mb-2 text-xs tracking-[0.3em] text-primary uppercase">
				Battle City Programming Guide
			</div>
			<h1 class="mb-4 text-3xl font-black uppercase md:text-5xl">Управление танком</h1>
			<p class="max-w-3xl leading-7 text-on-surface-variant">
				Вы управляете танком не клавишами, а программой. Команды выполняются сверху вниз. В режиме
				арены готовая последовательность повторяется до завершения боя.
			</p>
		</section>

		<section class="mb-12">
			<h2 class="mb-5 text-xl font-bold text-secondary-fixed uppercase">01 // Основные команды</h2>
			<div class="grid gap-4 md:grid-cols-2">
				{#each commands as command}
					<article class="border-2 border-outline-variant bg-surface-container-low p-5">
						<div class="mb-4 flex items-center gap-3">
							<span
								class="flex h-10 w-10 items-center justify-center border-2 text-xl"
								style="color:{command.color}; border-color:{command.color};">{command.icon}</span
							>
							<code class="text-lg font-bold" style="color:{command.color};">{command.name}</code>
						</div>
						<p class="mb-2">{command.description}</p>
						<p class="mb-4 text-xs leading-5 text-on-surface-variant">{command.details}</p>
						<pre
							class="overflow-x-auto border border-outline-variant bg-surface p-3 text-xs text-primary">{command.example}</pre>
					</article>
				{/each}
			</div>
		</section>

		<section class="mb-12">
			<h2 class="mb-5 text-xl font-bold text-secondary-fixed uppercase">02 // Условия и циклы</h2>
			<div class="grid gap-4 lg:grid-cols-3">
				<article class="border-2 border-outline-variant p-5">
					<h3 class="mb-3 font-bold text-primary">if — условие</h3>
					<p class="mb-4 text-xs leading-5 text-on-surface-variant">
						Выполняет вложенные команды, только когда условие истинно.
					</p>
					<pre class="bg-surface-container-low p-4 text-xs text-secondary-fixed">if scan():
    fire()</pre>
				</article>
				<article class="border-2 border-outline-variant p-5">
					<h3 class="mb-3 font-bold text-primary">for — точный повтор</h3>
					<p class="mb-4 text-xs leading-5 text-on-surface-variant">
						Повторяет вложенный блок указанное количество раз.
					</p>
					<pre class="bg-surface-container-low p-4 text-xs text-secondary-fixed">for i in range(3):
    move()</pre>
				</article>
				<article class="border-2 border-outline-variant p-5">
					<h3 class="mb-3 font-bold text-primary">while — повтор по условию</h3>
					<p class="mb-4 text-xs leading-5 text-on-surface-variant">
						Повторяет блок, пока условие остаётся истинным. Используйте осторожно.
					</p>
					<pre class="bg-surface-container-low p-4 text-xs text-secondary-fixed">while scan():
    fire()</pre>
				</article>
			</div>
		</section>

		<section class="mb-12 grid gap-6 lg:grid-cols-2">
			<div>
				<h2 class="mb-5 text-xl font-bold text-secondary-fixed uppercase">
					03 // Пример стратегии
				</h2>
				<pre
					class="border-2 border-primary bg-surface-container-low p-5 text-sm leading-7 text-primary"># Проверить линию огня
if scan():
    fire()

# Проехать три клетки
for i in range(3):
    move()

# Повернуть направо
rotate('RIGHT')</pre>
			</div>
			<div>
				<h2 class="mb-5 text-xl font-bold text-secondary-fixed uppercase">04 // Правила поля</h2>
				<ul class="space-y-3 text-sm text-on-surface-variant">
					<li class="border-l-2 border-primary pl-3">
						<strong class="text-on-surface">Сетка:</strong> одна команда move() перемещает танк ровно
						на одну клетку.
					</li>
					<li class="border-l-2 border-primary pl-3">
						<strong class="text-on-surface">Кирпич:</strong> разрушается одним попаданием и блокирует
						этот снаряд.
					</li>
					<li class="border-l-2 border-primary pl-3">
						<strong class="text-on-surface">Сталь:</strong> не позволяет танку пройти и не разрушается.
					</li>
					<li class="border-l-2 border-primary pl-3">
						<strong class="text-on-surface">Столкновение:</strong> два танка не могут занимать одну клетку.
					</li>
					<li class="border-l-2 border-primary pl-3">
						<strong class="text-on-surface">Победа:</strong> выполните цель миссии или уничтожьте противника.
					</li>
				</ul>
			</div>
		</section>
	</main>

	<footer class="mt-[62px] w-full border-t-4 border-outline-variant bg-surface-container-low">
		<div
			class="mx-auto flex max-w-[1200px] flex-col items-center justify-between gap-6 p-8 md:flex-row"
		>
			<div class="flex items-center gap-4">
				<div
					class="pixel-border flex h-8 w-8 items-center justify-center bg-primary-container text-base"
				>
					🎮
				</div>
				<span class="text-lg font-bold text-primary uppercase">CodeCommand</span>
			</div>
			<nav class="flex flex-wrap justify-center gap-6 text-sm uppercase">
				<a href="/" class="text-primary underline hover:text-secondary-fixed-dim">HOME</a>
				<a href="/missions" class="text-on-surface-variant hover:text-secondary-fixed-dim"
					>MISSIONS</a
				>
				<a href="/challenge-maps" class="text-on-surface-variant hover:text-secondary-fixed-dim"
					>CHALLENGE VS AI</a
				>
				<a href="/pvp-maps" class="text-on-surface-variant hover:text-secondary-fixed-dim"
					>PVP ROOMS</a
				>
			</nav>
			<div class="text-sm font-bold text-tertiary uppercase">
				© 2026 CODECOMMAND INDUSTRIES.<br />ALL BYTES RESERVED.
			</div>
		</div>
	</footer>
</div>
