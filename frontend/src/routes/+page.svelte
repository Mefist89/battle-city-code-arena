<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Application, Assets, Sprite, Texture, Rectangle } from 'pixi.js';

	let backendStatus = $state('');
	let gameContainer = $state<HTMLDivElement | null>(null);
	let previewApp: Application | null = null;

	const TANK_SPRITE_URL = '/assets/tanks.png';

	onMount(async () => {
		if (!gameContainer) return;
		const app = new Application();
		previewApp = app;
		await app.init({
			width: 320,
			height: 200,
			backgroundColor: 0x0e0e0e,
			antialias: false
		});
		gameContainer.appendChild(app.canvas);

		const baseTexture = await Assets.load(TANK_SPRITE_URL);
		const tankTexture = new Texture({ source: baseTexture, frame: new Rectangle(0, 0, 16, 16) });
		const tank = new Sprite(tankTexture);
		tank.anchor.set(0.5);
		tank.scale.set(5);
		tank.x = app.screen.width / 2;
		tank.y = app.screen.height / 2;
		app.stage.addChild(tank);
		app.ticker.add((t) => {
			tank.rotation += 0.02 * t.deltaTime;
		});
	});

	onDestroy(() => {
		previewApp?.destroy(true, { children: true });
		previewApp = null;
	});

	async function checkBackend() {
		try {
			const r = await fetch('http://localhost:8000/');
			const d = await r.json();
			backendStatus = d.message;
		} catch {
			backendStatus = 'CONNECTION_FAILED';
		}
	}
</script>

<svelte:head>
	<title>Battle City: Code Arena</title>
</svelte:head>

<!-- ─── TOP NAV ─── -->
<nav
	class="sticky top-0 z-50 w-full border-b-4 border-on-surface bg-surface-container-low"
	style="box-shadow: 4px 4px 0px 0px rgba(184,195,255,0.15);"
>
	<div class="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-4">
		<!-- Logo -->
		<div class="flex items-center gap-4">
			<div
				class="pixel-border flex h-12 w-12 items-center justify-center bg-primary-container text-2xl"
			>
				🎮
			</div>
			<span
				class="text-2xl font-bold tracking-tight text-primary uppercase underline decoration-4 underline-offset-4"
			>
				CodeCommand
			</span>
		</div>

		<!-- Nav links (desktop) -->
		<div class="hidden gap-8 md:flex">
			{#each [{ label: 'Missions', href: '/missions' }, { label: 'Challenge vs AI', href: '/challenge-maps' }, { label: 'PvP Rooms', href: '/pvp' }, { label: 'Academy', href: '#protocol' }] as link, i}
				<a
					href={link.href}
					class="border-b-4 text-lg font-bold tracking-tighter uppercase transition-all hover:translate-x-px hover:translate-y-px"
					class:border-tertiary={i === 0}
					class:text-tertiary={i === 0}
					class:border-transparent={i !== 0}
					class:text-on-surface-variant={i !== 0}
					class:hover:text-primary={i !== 0}
				>
					{link.label}
				</a>
			{/each}
		</div>

		<!-- CTA -->
		<div class="flex items-center gap-3">
			<button
				onclick={checkBackend}
				class="pixel-btn bg-primary-container px-5 py-2 text-sm font-bold text-on-primary-container uppercase"
			>
				START_HACKING
			</button>
			<button
				class="pixel-btn flex h-10 w-10 items-center justify-center bg-surface-variant text-lg text-on-surface"
			>
				👤
			</button>
		</div>
	</div>
</nav>

<!-- ─── MAIN ─── -->
<main class="mx-auto flex max-w-[1200px] flex-col gap-12 px-4 py-12 md:px-12">
	<!-- HERO -->
	<section
		id="missions"
		class="pixel-shadow flex flex-col items-center gap-8 border-4 border-outline bg-surface-container-low p-8 md:flex-row"
	>
		<div class="flex flex-1 flex-col gap-6">
			<h1
				class="text-4xl leading-tight font-bold tracking-tight text-primary uppercase md:text-5xl"
			>
				LEVEL UP<br />YOUR CODING<br />SKILLS!
			</h1>
			<p class="text-lg text-on-surface-variant">
				Master logic, loops, and syntax by commanding your tank in intense 8-bit combat arenas.
			</p>
			<div class="flex flex-wrap gap-4">
				<a
					href="/missions"
					class="pixel-btn bg-tertiary px-8 py-4 text-xl font-bold text-on-tertiary uppercase"
				>
					START MISSION
				</a>
				<button
					class="pixel-btn bg-surface-variant px-8 py-4 text-xl font-bold text-on-surface-variant uppercase"
				>
					VIEW INTEL
				</button>
			</div>
			{#if backendStatus}
				<div
					class="border-2 border-secondary-fixed bg-surface-container p-3 text-sm font-bold"
					class:text-secondary-fixed={backendStatus !== 'CONNECTION_FAILED'}
					class:text-error={backendStatus === 'CONNECTION_FAILED'}
				>
					&gt; {backendStatus}
				</div>
			{/if}
		</div>

		<!-- PixiJS Preview -->
		<div class="flex flex-1 flex-col items-center gap-2">
			<div class="pixel-border pixel-shadow overflow-hidden" bind:this={gameContainer}></div>
			<span class="text-xs tracking-widest text-on-surface-variant uppercase">[ LIVE PREVIEW ]</span
			>
		</div>
	</section>

	<!-- HOW IT WORKS -->
	<section id="protocol" class="flex flex-col gap-8">
		<h2
			class="border-b-4 border-secondary-fixed pb-4 text-center text-3xl font-bold text-secondary-fixed uppercase"
		>
			MISSION PROTOCOL
		</h2>
		<div class="grid grid-cols-1 gap-4 md:grid-cols-4">
			{#each [{ num: '1', label: 'WRITE', icon: '📝', color: 'bg-primary', text: 'text-on-primary', desc: 'Assemble logic blocks to build your command sequence.' }, { num: '2', label: 'RUN', icon: '▶️', color: 'bg-secondary', text: 'text-on-secondary', desc: 'Compile your script and deploy it to the battleground.' }, { num: '3', label: 'EXECUTE', icon: '⚙️', color: 'bg-tertiary', text: 'text-on-tertiary', desc: 'Watch your tank navigate the maze and engage enemies.' }, { num: '4', label: 'WIN', icon: '🏆', color: 'bg-error', text: 'text-on-error', desc: 'Destroy targets, collect loot, and rank up your profile.' }] as step}
				<div
					class="pixel-shadow flex flex-col items-center gap-4 border-4 border-outline bg-surface-container p-6 text-center"
				>
					<div class="pixel-btn flex h-16 w-16 items-center justify-center text-3xl {step.color}">
						{step.icon}
					</div>
					<h3 class="text-xl font-bold text-primary-fixed uppercase">
						{step.num}. {step.label}
					</h3>
					<p class="text-sm text-on-surface-variant">{step.desc}</p>
				</div>
			{/each}
		</div>
	</section>

	<!-- BATTLE SIMULATOR PREVIEW -->
	<section
		id="simulator"
		class="pixel-shadow flex flex-col items-center gap-8 border-4 border-outline bg-surface-container-highest p-8"
	>
		<h2 class="text-3xl font-bold text-primary uppercase">BATTLE SIMULATOR PREVIEW</h2>

		<!-- Fake terminal / game preview -->
		<div class="pixel-shadow w-full max-w-3xl border-4 border-on-surface bg-black">
			<!-- Terminal header -->
			<div
				class="flex items-center gap-2 border-b-4 border-on-surface bg-surface-container-high px-4 py-2"
			>
				<div class="h-3 w-3 border-2 border-black bg-error"></div>
				<div class="h-3 w-3 border-2 border-black bg-tertiary"></div>
				<div class="h-3 w-3 border-2 border-black bg-secondary-fixed"></div>
				<span class="ml-2 text-xs tracking-widest text-on-surface-variant uppercase"
					>ARENA_SIM v0.1.0</span
				>
			</div>
			<!-- Fake code preview -->
			<div class="p-6 font-mono text-sm leading-relaxed">
				<p class="text-secondary-fixed">&gt; loading mission_01.json...</p>
				<p class="text-on-surface-variant">&gt; map loaded: 26x26 tiles</p>
				<p class="text-tertiary">&gt; spawning player tank at (1,1)</p>
				<p class="text-primary">&gt; executing player_script.py...</p>
				<div class="mt-4 border-2 border-outline-variant p-4">
					<p class="text-secondary-fixed">tank.move(<span class="text-tertiary">'UP'</span>)</p>
					<p class="text-secondary-fixed">tank.move(<span class="text-tertiary">'RIGHT'</span>)</p>
					<p class="text-secondary-fixed">tank.fire()</p>
					<p class="text-primary"># &gt;&gt; ENEMY DESTROYED! +100 XP</p>
				</div>
				<p class="mt-4 animate-pulse text-secondary-fixed">▮</p>
			</div>
		</div>

		<a
			href="/game"
			class="pixel-btn inline-block bg-primary px-8 py-4 text-xl font-bold text-on-primary uppercase"
		>
			ENTER ARENA
		</a>
	</section>
</main>

<!-- ─── FOOTER ─── -->
<footer class="mt-12 w-full border-t-4 border-outline-variant bg-surface-container-low">
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
		<div class="flex flex-wrap justify-center gap-6 text-sm uppercase">
			<a href="/game" class="text-primary underline hover:text-secondary-fixed-dim"
				>TERMINAL_ACCESS</a
			>
			<a href="#missions" class="text-on-surface-variant hover:text-secondary-fixed-dim">MISSIONS</a
			>
			<a href="#protocol" class="text-on-surface-variant hover:text-secondary-fixed-dim">PROTOCOL</a
			>
			<button
				type="button"
				onclick={checkBackend}
				class="text-on-surface-variant hover:text-secondary-fixed-dim">SYSTEM_STATUS</button
			>
		</div>
		<div class="text-sm font-bold text-tertiary uppercase">
			© 198X CODECOMMAND INDUSTRIES.<br />ALL BYTES RESERVED.
		</div>
	</div>
</footer>
