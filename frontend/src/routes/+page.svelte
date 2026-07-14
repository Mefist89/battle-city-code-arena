<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Application, Assets, Graphics, Sprite } from 'pixi.js';
	import { t } from '$lib/i18n';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
	type MenuUser = { name: string; email: string; picture?: string };
	const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

	let gameContainer = $state<HTMLDivElement | null>(null);
	let previewApp: Application | null = null;
	let backendStatus = $state<'checking' | 'online' | 'offline'>('checking');
	let mobileMenuOpen = $state(false);
	let currentUser = $state<MenuUser | null>(null);

	const navLinks = [
		{ key: 'common.missions', href: '/missions' },
		{ key: 'common.challenge', href: '/challenge-maps' },
		{ key: 'common.pvp', href: '/pvp-maps' },
		{ key: 'common.instruction', href: '/instruction' }
	];

	const modes = [
		{
			index: '01',
			title: 'MISSION MODE',
			tag: '9 LEVELS',
			description: 'От первых перемещений до сражения сразу с тремя автономными танками.',
			href: '/missions',
			color: 'text-secondary-fixed',
			border: 'border-secondary-fixed',
			button: 'bg-secondary-fixed text-on-secondary-fixed'
		},
		{
			index: '02',
			title: 'CHALLENGE VS AI',
			tag: '3 ARENAS',
			description: 'Напиши стратегию за 60 секунд и проверь её против Easy, Medium или Hard AI.',
			href: '/challenge-maps',
			color: 'text-primary',
			border: 'border-primary',
			button: 'bg-primary text-on-primary'
		},
		{
			index: '03',
			title: 'PLAYER VS PLAYER',
			tag: 'REAL TIME',
			description:
				'Создай комнату, поделись кодом приглашения и сразись стратегиями в реальном времени.',
			href: '/pvp-maps',
			color: 'text-error',
			border: 'border-error',
			button: 'bg-error text-on-error'
		}
	];

	const steps = [
		{
			number: '01',
			title: 'WRITE',
			icon: '</>',
			text: 'Собери стратегию из команд, условий и циклов.'
		},
		{
			number: '02',
			title: 'COMPILE',
			icon: '◆',
			text: 'Безопасный интерпретатор проверит код и ограничения.'
		},
		{
			number: '03',
			title: 'DEPLOY',
			icon: '▲',
			text: 'Танк выполнит команды на клеточной арене 10×8.'
		},
		{
			number: '04',
			title: 'ADAPT',
			icon: '◎',
			text: 'Изучи журнал боя, исправь алгоритм и победи.'
		}
	];

	const mechanics = [
		{
			icon: '▦',
			title: 'GRID MOVEMENT',
			text: 'Каждый move() перемещает танк ровно на одну клетку.'
		},
		{
			icon: '◫',
			title: 'BRICK WALLS',
			text: 'Кирпич разрушается одним попаданием и открывает маршрут.'
		},
		{
			icon: '▣',
			title: 'STEEL BLOCKS',
			text: 'Сталь не разрушается: её нужно обходить и использовать как укрытие.'
		},
		{
			icon: '●',
			title: 'PROJECTILES',
			text: 'Пули сталкиваются, исчезают и не проходят сквозь танки.'
		},
		{
			icon: '♥',
			title: 'HP SYSTEM',
			text: 'Попадания уменьшают HP, а повреждённый танк мигает красным.'
		},
		{
			icon: '⌁',
			title: 'LIVE AI',
			text: 'Противники двигаются, ищут линию огня и разрушают кирпичи.'
		}
	];
	const missionPreviews = [
		{
			id: 1,
			goal: '1,2',
			brick: ['4,1', '4,2', '7,4'],
			steel: ['4,3', '7,5'],
			enemies: [{ cell: '8,5', skin: 'red' }]
		},
		{
			id: 2,
			goal: '5,2',
			brick: ['3,4', '4,4', '7,3'],
			steel: ['5,4', '7,2'],
			enemies: [{ cell: '8,1', skin: 'dark' }]
		},
		{
			id: 3,
			goal: '8,1',
			brick: ['4,3', '5,3', '8,4'],
			steel: ['3,3', '6,3', '8,5'],
			enemies: [{ cell: '7,5', skin: 'red' }]
		},
		{
			id: 4,
			goal: '7,1',
			brick: ['3,2', '4,2', '8,5'],
			steel: ['5,4', '6,4'],
			enemies: [{ cell: '7,2', skin: 'red' }]
		},
		{
			id: 5,
			goal: '8,2',
			brick: ['4,2', '4,3', '7,4', '8,4'],
			steel: ['4,4', '6,4'],
			enemies: [{ cell: '6,2', skin: 'dark' }]
		},
		{
			id: 6,
			goal: '8,1',
			brick: ['5,4', '6,4', '6,2'],
			steel: ['3,2', '3,3', '7,4', '8,4'],
			enemies: [{ cell: '8,2', skin: 'red' }]
		},
		{
			id: 7,
			goal: '8,3',
			brick: ['3,2', '5,1', '5,2', '7,5'],
			steel: ['3,3', '6,5'],
			enemies: [
				{ cell: '8,1', skin: 'red' },
				{ cell: '8,6', skin: 'green' }
			]
		},
		{
			id: 8,
			goal: '8,3',
			brick: ['3,3', '4,3', '6,3', '6,4'],
			steel: ['2,3', '6,2', '8,5'],
			enemies: [
				{ cell: '7,1', skin: 'dark' },
				{ cell: '8,6', skin: 'sand' }
			]
		},
		{
			id: 9,
			goal: '8,3',
			brick: ['2,2', '4,2', '5,4', '7,4', '7,6'],
			steel: ['3,2', '6,4', '4,6'],
			enemies: [
				{ cell: '8,1', skin: 'red' },
				{ cell: '8,6', skin: 'green' },
				{ cell: '5,1', skin: 'heavy' }
			]
		}
	];

	const enemyPreviewAsset: Record<string, string> = {
		red: '/assets/kenney-remastered/tank_red.png',
		dark: '/assets/kenney-remastered/tank_dark.png',
		green: '/assets/kenney-remastered/tank_green.png',
		sand: '/assets/kenney-remastered/tank_sand.png',
		heavy: '/assets/kenney-remastered/tank_bigRed.png'
	};

	async function checkBackend() {
		backendStatus = 'checking';
		try {
			const response = await fetch(`${API}/api/missions`);
			backendStatus = response.ok ? 'online' : 'offline';
		} catch {
			backendStatus = 'offline';
		}
	}

	async function loadCurrentUser() {
		try {
			const response = await fetch(`${API}/auth/me`, { credentials: 'include' });
			if (!response.ok) return;
			const data = await response.json();
			currentUser = data.authenticated ? data.user : null;
		} catch {
			currentUser = null;
		}
	}

	onMount(async () => {
		void checkBackend();
		void loadCurrentUser();
		if (!gameContainer) return;

		const app = new Application();
		previewApp = app;
		await app.init({ width: 560, height: 360, backgroundColor: 0x090b0f, antialias: false });
		gameContainer.appendChild(app.canvas);

		const tile = 56;
		const grid = new Graphics();
		grid.setStrokeStyle({ width: 1, color: 0x303541, alpha: 0.9 });
		for (let x = 0; x <= 10; x++) {
			grid.moveTo(x * tile, 0).lineTo(x * tile, 360);
		}
		for (let y = 0; y <= 7; y++) {
			grid.moveTo(0, y * tile).lineTo(560, y * tile);
		}
		grid.stroke();
		app.stage.addChild(grid);

		const [
			blueTexture,
			redTexture,
			brickTexture,
			steelTexture,
			blueBulletTexture,
			redBulletTexture
		] = await Promise.all([
			Assets.load('/assets/kenney-remastered/tank_blue.png'),
			Assets.load('/assets/kenney-remastered/tank_red.png'),
			Assets.load('/assets/kenney/wall-brick.png'),
			Assets.load('/assets/kenney/wall-steel.png'),
			Assets.load('/assets/kenney-remastered/bulletBlue2.png'),
			Assets.load('/assets/kenney-remastered/bulletRed2.png')
		]);

		for (const [x, y, type] of [
			[4, 1, 'brick'],
			[5, 1, 'brick'],
			[4, 2, 'steel'],
			[5, 2, 'steel'],
			[4, 4, 'brick'],
			[5, 4, 'brick'],
			[4, 5, 'steel'],
			[5, 5, 'steel']
		] as Array<[number, number, 'brick' | 'steel']>) {
			const wall = new Sprite(type === 'brick' ? brickTexture : steelTexture);
			wall.anchor.set(0.5);
			wall.width = 48;
			wall.height = 48;
			wall.position.set(x * tile + tile / 2, y * tile + tile / 2);
			app.stage.addChild(wall);
		}

		const blue = new Sprite(blueTexture);
		blue.anchor.set(0.5);
		blue.width = 52;
		blue.scale.y = blue.scale.x;
		blue.rotation = -Math.PI / 2;
		blue.position.set(84, 308);
		app.stage.addChild(blue);

		const red = new Sprite(redTexture);
		red.anchor.set(0.5);
		red.width = 52;
		red.scale.y = red.scale.x;
		red.rotation = Math.PI / 2;
		red.position.set(476, 28);
		app.stage.addChild(red);

		const blueBullet = new Sprite(blueBulletTexture);
		blueBullet.anchor.set(0.5);
		blueBullet.width = 20;
		blueBullet.scale.y = blueBullet.scale.x;
		blueBullet.rotation = Math.PI / 2;
		blueBullet.position.set(116, 308);
		app.stage.addChild(blueBullet);

		const redBullet = new Sprite(redBulletTexture);
		redBullet.anchor.set(0.5);
		redBullet.width = 20;
		redBullet.scale.y = redBullet.scale.x;
		redBullet.rotation = -Math.PI / 2;
		redBullet.position.set(444, 28);
		app.stage.addChild(redBullet);

		let blueBulletDirection = 1;
		let redBulletDirection = -1;
		app.ticker.add((ticker) => {
			blueBullet.x += blueBulletDirection * 2.4 * ticker.deltaTime;
			redBullet.x += redBulletDirection * 2.4 * ticker.deltaTime;

			if (blueBullet.x >= 360) blueBulletDirection = -1;
			if (blueBullet.x <= 116) blueBulletDirection = 1;
			if (redBullet.x <= 200) redBulletDirection = 1;
			if (redBullet.x >= 444) redBulletDirection = -1;

			blueBullet.rotation = blueBulletDirection > 0 ? Math.PI / 2 : -Math.PI / 2;
			redBullet.rotation = redBulletDirection > 0 ? Math.PI / 2 : -Math.PI / 2;
		});
	});

	onDestroy(() => {
		previewApp?.destroy(true, { children: true });
		previewApp = null;
	});
</script>

<svelte:head>
	<title>CODETANK ARENA</title>
	<meta
		name="description"
		content="Программируй танк, разрушай стены и сражайся с AI или другими игроками."
	/>
</svelte:head>

<div class="min-h-screen overflow-hidden bg-surface font-mono text-on-surface">
	<div class="scanlines pointer-events-none fixed inset-0 z-[100] opacity-[0.035]"></div>

	<nav
		class="sticky top-0 z-50 border-b-4 border-outline-variant bg-surface-container-low/95 backdrop-blur"
	>
		<div
			class="mx-auto flex max-w-[1280px] items-center justify-between gap-3 px-3 py-3 sm:gap-5 sm:px-5 sm:py-4 lg:px-8"
		>
			<a href="/" class="flex items-center gap-3" aria-label="CODETANK ARENA — Home">
				<span
					class="pixel-shadow flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden border-2 border-outline-variant bg-black sm:h-11 sm:w-11 xl:h-12 xl:w-12"
				>
					<img
						src="/assets/codetank-logo-mark-transparent.png"
						alt=""
						class="h-full w-full scale-[1.45] object-cover"
					/>
				</span>
				<span
					class="hidden font-black tracking-tight text-primary uppercase sm:inline sm:text-xl xl:text-2xl"
					>CODETANK ARENA</span
				>
			</a>

			<div class="hidden items-center gap-4 lg:flex xl:gap-6">
				{#each navLinks as link}
					<a
						href={link.href}
						class="text-xs font-bold text-on-surface-variant uppercase hover:text-primary xl:text-sm"
						>{$t(link.key)}</a
					>
				{/each}
			</div>

			<div class="hidden items-center gap-3 lg:flex">
				<LanguageSwitcher floating={false} />
				{#if currentUser}
					<a
						href="/profile"
						class="pixel-shadow flex items-center gap-2 border-2 border-secondary-fixed bg-surface-container px-2 py-1.5 hover:bg-surface-container-high"
						aria-label={$t('common.profile')}
					>
						{#if currentUser.picture}<img
								src={currentUser.picture}
								alt=""
								referrerpolicy="no-referrer"
								class="h-7 w-7 border border-secondary-fixed object-cover"
							/>{/if}
						<span
							class="hidden max-w-24 truncate text-xs font-black text-secondary-fixed uppercase xl:inline"
							>{currentUser.name}</span
						>
					</a>
				{:else}
					<a
						href="/auth"
						class="pixel-shadow border-2 border-primary bg-primary px-3 py-2 text-xs font-black text-on-primary uppercase hover:bg-primary-fixed"
						>{$t('common.signIn')}</a
					>
				{/if}
				<button
					type="button"
					onclick={checkBackend}
					class="hidden items-center gap-2 border-2 border-outline-variant bg-surface px-3 py-2 text-[10px] font-bold uppercase xl:flex"
				>
					<span
						class="h-2.5 w-2.5"
						class:animate-pulse={backendStatus === 'checking'}
						class:bg-tertiary={backendStatus === 'checking'}
						class:bg-primary={backendStatus === 'online'}
						class:bg-error={backendStatus === 'offline'}
					></span>
					{backendStatus === 'online'
						? 'System online'
						: backendStatus === 'offline'
							? 'System offline'
							: 'Checking'}
				</button>
			</div>

			<button
				type="button"
				class="pixel-shadow flex h-10 w-12 flex-col items-center justify-center gap-1.5 border-2 border-outline-variant bg-surface text-primary lg:hidden"
				aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
				aria-expanded={mobileMenuOpen}
				aria-controls="mobile-navigation"
				onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
			>
				<span
					class="h-0.5 w-6 bg-current transition-transform"
					class:translate-y-2={mobileMenuOpen}
					class:rotate-45={mobileMenuOpen}
				></span>
				<span class="h-0.5 w-6 bg-current" class:opacity-0={mobileMenuOpen}></span>
				<span
					class="h-0.5 w-6 bg-current transition-transform"
					class:-translate-y-2={mobileMenuOpen}
					class:-rotate-45={mobileMenuOpen}
				></span>
			</button>
		</div>

		{#if mobileMenuOpen}
			<div
				id="mobile-navigation"
				class="border-t-2 border-outline-variant bg-surface-container-low px-3 pb-4 sm:px-5 lg:hidden"
			>
				<div class="mx-auto flex max-w-[1280px] flex-col">
					{#each navLinks as link, index}
						<a
							href={link.href}
							class="flex items-center justify-between border-b-2 border-outline-variant px-2 py-4 text-sm font-bold text-on-surface-variant uppercase hover:bg-surface-container hover:text-primary"
							onclick={() => (mobileMenuOpen = false)}
						>
							<span><span class="mr-3 text-secondary-fixed">0{index + 1}</span>{$t(link.key)}</span>
							<span aria-hidden="true" class="text-primary">→</span>
						</a>
					{/each}
					{#if currentUser}
						<a
							href="/profile"
							class="mt-4 flex items-center gap-3 border-2 border-secondary-fixed bg-surface-container px-4 py-3 text-sm font-black text-secondary-fixed uppercase shadow-[4px_4px_0_#000]"
							onclick={() => (mobileMenuOpen = false)}
						>
							{#if currentUser.picture}<img
									src={currentUser.picture}
									alt=""
									referrerpolicy="no-referrer"
									class="h-9 w-9 border-2 border-secondary-fixed object-cover"
								/>{/if}
							<span class="min-w-0"
								><span class="block truncate">{currentUser.name}</span><span
									class="block text-[9px] text-on-surface-variant">{$t('common.profile')}</span
								></span
							>
						</a>
					{:else}
						<a
							href="/auth"
							class="mt-4 flex items-center justify-center border-2 border-primary bg-primary px-4 py-3 text-sm font-black text-on-primary uppercase shadow-[4px_4px_0_#000]"
							onclick={() => (mobileMenuOpen = false)}>{$t('common.signIn')}</a
						>
					{/if}

					<div class="flex flex-wrap items-center justify-between gap-3 px-2 pt-4">
						<LanguageSwitcher floating={false} />
						<button
							type="button"
							onclick={checkBackend}
							class="flex items-center gap-2 border-2 border-outline-variant bg-surface px-3 py-2 text-[10px] font-bold uppercase"
						>
							<span
								class="h-2.5 w-2.5"
								class:animate-pulse={backendStatus === 'checking'}
								class:bg-tertiary={backendStatus === 'checking'}
								class:bg-primary={backendStatus === 'online'}
								class:bg-error={backendStatus === 'offline'}
							></span>
							{backendStatus === 'online'
								? 'System online'
								: backendStatus === 'offline'
									? 'System offline'
									: 'Checking'}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</nav>

	<main>
		<section class="relative border-b-4 border-outline-variant">
			<div class="grid-bg absolute inset-0 opacity-40"></div>
			<div
				class="relative mx-auto grid max-w-[1280px] items-center gap-10 px-5 py-14 lg:grid-cols-[1fr_0.95fr] lg:px-8 lg:py-24"
			>
				<div>
					<div
						class="mb-5 inline-flex border-2 border-tertiary bg-surface px-3 py-1 text-xs font-bold tracking-[0.22em] text-tertiary uppercase"
					>
						{$t('home.heroEyebrow')}
					</div>
					<h1
						class="mb-6 text-5xl leading-[0.9] font-black tracking-[-0.06em] text-primary uppercase sm:text-7xl xl:text-8xl"
					>
						CODETANK<br /><span class="text-secondary-fixed">ARENA</span>
					</h1>
					<p class="mb-8 max-w-2xl text-base leading-7 text-on-surface-variant sm:text-lg">
						{$t('home.heroText')}
					</p>
					<div class="flex flex-wrap gap-4">
						<a
							href="/missions"
							class="pixel-btn bg-primary px-7 py-4 text-base font-black text-on-primary uppercase"
							>▶ {$t('home.startMission')}</a
						>
						<a
							href="/challenge-maps"
							class="pixel-btn border-2 border-secondary-fixed bg-surface px-7 py-4 text-base font-black text-secondary-fixed uppercase"
							>⚔ {$t('common.challenge')}</a
						>
					</div>
					<div
						class="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-xs text-on-surface-variant uppercase"
					>
						<span><b class="text-primary">✓</b> 9 missions</span>
						<span><b class="text-primary">✓</b> destructible maps</span>
						<span><b class="text-primary">✓</b> real-time PvP</span>
					</div>
				</div>

				<div class="relative mx-auto w-full max-w-[600px]">
					<div class="absolute -inset-3 translate-x-3 translate-y-3 bg-black"></div>
					<div class="relative border-4 border-outline bg-black p-2">
						<div
							class="mb-2 flex items-center justify-between border-b-2 border-outline-variant px-2 pb-2 text-[10px] uppercase"
						>
							<span class="text-primary">● Arena live feed</span>
							<span class="text-on-surface-variant">Map 10×8 // 30 sec</span>
						</div>
						<div
							bind:this={gameContainer}
							class="aspect-[14/9] w-full overflow-hidden [&_canvas]:h-full [&_canvas]:w-full [&_canvas]:object-contain"
						></div>
					</div>
					<div
						class="absolute -right-2 -bottom-4 border-2 border-primary bg-surface px-4 py-2 text-xs font-bold text-primary uppercase"
					>
						[ Live simulation ]
					</div>
				</div>
			</div>
		</section>

		<section class="border-b-4 border-outline-variant bg-surface-container-low">
			<div
				class="mx-auto grid max-w-[1280px] grid-cols-2 divide-x-2 divide-y-2 divide-outline-variant border-x-2 border-outline-variant md:grid-cols-5 md:divide-y-0"
			>
				{#each [['09', 'MISSIONS'], ['03', 'AI MAPS'], ['03', 'DIFFICULTIES'], ['30s', 'BATTLE TIME'], ['∞', 'CODE IDEAS']] as stat}
					<div class="px-4 py-5 text-center">
						<div class="text-2xl font-black text-primary sm:text-3xl">{stat[0]}</div>
						<div class="mt-1 text-[10px] tracking-widest text-on-surface-variant uppercase">
							{stat[1]}
						</div>
					</div>
				{/each}
			</div>
		</section>

		<section class="mx-auto max-w-[1280px] px-5 py-20 lg:px-8">
			<div
				class="mb-10 flex flex-col justify-between gap-4 border-b-4 border-primary pb-5 md:flex-row md:items-end"
			>
				<div>
					<div class="mb-2 text-xs font-bold tracking-[0.25em] text-primary uppercase">
						{$t('home.chooseMode')}
					</div>
					<h2 class="text-3xl font-black uppercase sm:text-5xl">{$t('home.chooseMode')}</h2>
				</div>
				<p class="max-w-md text-sm leading-6 text-on-surface-variant">
					{$t('home.chooseModeText')}
				</p>
			</div>

			<div class="grid gap-6 lg:grid-cols-3">
				{#each modes as mode}
					<article
						class="pixel-shadow group flex min-h-[330px] flex-col border-4 bg-surface-container-low p-6 transition-transform hover:-translate-y-1 {mode.border}"
					>
						<div class="mb-8 flex items-start justify-between">
							<span class="text-5xl font-black {mode.color}">{mode.index}</span>
							<span class="border-2 px-3 py-1 text-[10px] font-bold {mode.border} {mode.color}"
								>{$t(`home.modes.${mode.index}.tag`)}</span
							>
						</div>
						<h3 class="mb-4 text-2xl font-black uppercase">
							{$t(`home.modes.${mode.index}.title`)}
						</h3>
						<p class="mb-8 text-sm leading-6 text-on-surface-variant">
							{$t(`home.modes.${mode.index}.description`)}
						</p>
						<a
							href={mode.href}
							class="pixel-btn mt-auto block px-5 py-3 text-center text-sm font-black uppercase {mode.button}"
							>{$t('home.insertCartridge')}</a
						>
					</article>
				{/each}
			</div>
		</section>

		<section class="border-y-4 border-outline-variant bg-surface-container-highest">
			<div class="mx-auto max-w-[1280px] px-5 py-20 lg:px-8">
				<div class="mb-12 text-center">
					<div class="mb-2 text-xs font-bold tracking-[0.25em] text-secondary-fixed uppercase">
						{$t('home.protocolLabel')}
					</div>
					<h2 class="text-3xl font-black uppercase sm:text-5xl">{$t('home.protocolTitle')}</h2>
				</div>
				<div class="grid gap-4 md:grid-cols-4">
					{#each steps as step, index}
						<div class="relative border-2 border-outline-variant bg-surface p-5">
							{#if index < steps.length - 1}<span
									class="absolute top-8 -right-4 z-10 hidden text-xl text-primary md:block">→</span
								>{/if}
							<div class="mb-6 flex items-center justify-between">
								<span class="text-3xl font-black text-primary">{step.icon}</span><span
									class="text-xs text-outline">STEP {step.number}</span
								>
							</div>
							<h3 class="mb-3 text-xl font-black text-secondary-fixed">
								{$t(`home.steps.${step.number}.title`)}
							</h3>
							<p class="text-xs leading-5 text-on-surface-variant">
								{$t(`home.steps.${step.number}.text`)}
							</p>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<section
			class="mx-auto grid max-w-[1280px] gap-8 px-5 py-20 lg:grid-cols-[1.15fr_0.85fr] lg:px-8"
		>
			<div class="pixel-shadow border-4 border-outline bg-black">
				<div
					class="flex items-center justify-between border-b-4 border-outline bg-surface-container-high px-4 py-3"
				>
					<div class="flex gap-2">
						<span class="h-3 w-3 bg-error"></span><span class="h-3 w-3 bg-tertiary"></span><span
							class="h-3 w-3 bg-primary"
						></span>
					</div>
					<span class="text-[10px] text-on-surface-variant">strategy.py // PYTHON 3</span>
				</div>
				<div class="p-5 text-sm leading-7 sm:p-8">
					<p class="text-outline"># Find target and open fire</p>
					<p>
						<span class="text-error">if</span> <span class="text-secondary-fixed">scan</span>():
					</p>
					<p class="pl-6 text-secondary-fixed">fire()</p>
					<br />
					<p class="text-outline"># Advance through the arena</p>
					<p>
						<span class="text-error">for</span> i <span class="text-error">in</span>
						<span class="text-secondary-fixed">range</span>(3):
					</p>
					<p class="pl-6 text-secondary-fixed">move()</p>
					<p class="text-secondary-fixed">rotate(<span class="text-tertiary">'RIGHT'</span>)</p>
					<p class="mt-6 animate-pulse text-primary">█ CODE READY</p>
				</div>
			</div>

			<div class="flex flex-col justify-center">
				<div class="mb-2 text-xs font-bold tracking-[0.25em] text-tertiary uppercase">
					{$t('home.interfaceLabel')}
				</div>
				<h2 class="mb-5 text-3xl font-black uppercase sm:text-5xl">{$t('home.interfaceTitle')}</h2>
				<p class="mb-7 leading-7 text-on-surface-variant">{$t('home.interfaceText')}</p>
				<div class="grid grid-cols-2 gap-3 text-xs">
					{#each [['↑', 'move()', 'вперёд'], ['↻', "rotate('RIGHT')", 'направо'], ['◎', 'scan()', 'обнаружить'], ['⊕', 'fire()', 'выстрел']] as command}
						<div class="border-2 border-outline-variant bg-surface-container-low p-3">
							<span class="mr-2 text-primary">{command[0]}</span><code class="text-secondary-fixed"
								>{command[1]}</code
							>
							<div class="mt-1 text-[10px] text-outline">{command[2]}</div>
						</div>
					{/each}
				</div>
				<a
					href="/instruction"
					class="mt-7 text-sm font-bold text-primary underline underline-offset-4"
					>{$t('home.fullInstruction')}</a
				>
			</div>
		</section>

		<section class="border-y-4 border-outline-variant bg-surface-container-low">
			<div class="mx-auto max-w-[1280px] px-5 py-20 lg:px-8">
				<div class="mb-10 max-w-3xl">
					<div class="mb-2 text-xs font-bold tracking-[0.25em] text-error uppercase">
						{$t('home.mechanicsLabel')}
					</div>
					<h2 class="mb-4 text-3xl font-black uppercase sm:text-5xl">
						{$t('home.mechanicsTitle')}
					</h2>
					<p class="leading-7 text-on-surface-variant">{$t('home.mechanicsText')}</p>
				</div>
				<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{#each mechanics as mechanic, index}
						<div class="border-2 border-outline-variant bg-surface p-5 hover:border-primary">
							<div class="mb-4 text-3xl text-primary">{mechanic.icon}</div>
							<h3 class="mb-2 font-black text-secondary-fixed">
								{$t(`home.mechanics.${index}.title`)}
							</h3>
							<p class="text-xs leading-5 text-on-surface-variant">
								{$t(`home.mechanics.${index}.text`)}
							</p>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<section class="mx-auto max-w-[1280px] px-5 py-20 lg:px-8">
			<div class="grid items-center gap-10 lg:grid-cols-2">
				<div>
					<div class="mb-2 text-xs font-bold tracking-[0.25em] text-primary uppercase">
						{$t('home.campaignLabel')}
					</div>
					<h2 class="mb-5 text-3xl font-black uppercase sm:text-5xl">
						{$t('home.campaignTitle')}
					</h2>
					<p class="mb-7 leading-7 text-on-surface-variant">{$t('home.campaignText')}</p>
					<a
						href="/missions"
						class="pixel-btn inline-block bg-tertiary px-7 py-4 font-black text-on-tertiary uppercase"
						>{$t('home.viewCampaign')}</a
					>
				</div>
				<div class="grid grid-cols-3 gap-3">
					{#each missionPreviews as mission}
						<a
							href={`/game?mission=${mission.id}`}
							aria-label={`Открыть миссию ${mission.id}`}
							class="group overflow-hidden border-4 border-outline-variant bg-surface-container-low hover:border-primary"
						>
							<div
								class="grid aspect-[10/8] grid-cols-10 overflow-hidden border-b-2 border-outline-variant bg-[#090c12]"
							>
								{#each Array(80).keys() as index}
									{@const cell = `${index % 10},${Math.floor(index / 10)}`}
									{@const enemy = mission.enemies.find((item) => item.cell === cell)}
									<div class="relative min-w-0 border border-[#242838]/70">
										{#if mission.brick.includes(cell)}
											<img
												src="/assets/kenney/wall-brick.png"
												alt=""
												class="absolute inset-0 h-full w-full object-contain p-px"
											/>
										{:else if mission.steel.includes(cell)}
											<img
												src="/assets/kenney/wall-steel.png"
												alt=""
												class="absolute inset-0 h-full w-full object-contain p-px"
											/>
										{:else if cell === '1,6'}
											<img
												src="/assets/kenney-remastered/tank_blue.png"
												alt="Танк игрока"
												class="absolute inset-0 h-full w-full rotate-180 object-contain p-px"
											/>
										{:else if enemy}
											<img
												src={enemyPreviewAsset[enemy.skin]}
												alt="Танк противника"
												class="absolute inset-0 h-full w-full rotate-180 object-contain p-px"
											/>
										{:else if cell === mission.goal}
											<div
												class="absolute inset-[2px] flex items-center justify-center border border-primary bg-primary/15 text-[6px] font-black text-primary sm:text-[8px]"
											>
												B
											</div>
										{/if}
									</div>
								{/each}
							</div>
							<div class="flex items-center justify-between px-3 py-2">
								<span class="text-lg font-black text-primary"
									>{String(mission.id).padStart(2, '0')}</span
								>
								<span class="text-[8px] text-outline group-hover:text-on-surface-variant"
									>{mission.id <= 3 ? 'MOVE' : mission.id <= 6 ? 'COMBAT' : 'SIEGE'}</span
								>
							</div>
						</a>
					{/each}
				</div>
			</div>
		</section>

		<section class="border-t-4 border-outline-variant bg-primary-container">
			<div
				class="mx-auto flex max-w-[1280px] flex-col items-center justify-between gap-8 px-5 py-14 text-center lg:flex-row lg:px-8 lg:text-left"
			>
				<div>
					<div
						class="mb-2 text-xs font-bold tracking-[0.25em] text-on-primary-container/70 uppercase"
					>
						{$t('home.ready')}
					</div>
					<h2 class="text-3xl font-black text-on-primary-container uppercase sm:text-5xl">
						{$t('home.victory')}
					</h2>
				</div>
				<div class="flex flex-wrap justify-center gap-4">
					<a
						href="/missions"
						class="pixel-btn bg-surface px-7 py-4 font-black text-primary uppercase"
						>{$t('home.startCoding')}</a
					><a
						href="/pvp-maps"
						class="pixel-btn border-2 border-surface bg-transparent px-7 py-4 font-black text-on-primary-container uppercase"
						>{$t('home.createPvp')}</a
					>
				</div>
			</div>
		</section>
	</main>

	<footer class="border-t-4 border-outline-variant bg-surface-container-low">
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
			<div class="flex flex-wrap justify-center gap-5 text-xs uppercase">
				<a href="/" class="text-primary">{$t('common.home')}</a><a
					href="/missions"
					class="text-on-surface-variant hover:text-primary">{$t('common.missions')}</a
				><a href="/challenge-maps" class="text-on-surface-variant hover:text-primary"
					>{$t('common.challenge')}</a
				><a href="/pvp-maps" class="text-on-surface-variant hover:text-primary"
					>{$t('common.pvp')}</a
				><a href="/instruction" class="text-on-surface-variant hover:text-primary"
					>{$t('common.instruction')}</a
				>
			</div>
			<div class="text-center text-[10px] font-bold text-tertiary uppercase md:text-right">
				{$t('common.copyright')}
			</div>
		</div>
	</footer>
</div>

<style>
	.scanlines {
		background: repeating-linear-gradient(to bottom, transparent 0, transparent 3px, #fff 4px);
	}
	.grid-bg {
		background-image:
			linear-gradient(rgba(102, 255, 102, 0.07) 1px, transparent 1px),
			linear-gradient(90deg, rgba(102, 255, 102, 0.07) 1px, transparent 1px);
		background-size: 48px 48px;
	}
</style>
