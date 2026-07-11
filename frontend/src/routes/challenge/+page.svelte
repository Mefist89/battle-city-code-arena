<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { SvelteSet } from 'svelte/reactivity';
	import Sidebar from '../game/components/Sidebar.svelte';
	import Editor from '../game/components/Editor.svelte';
	import Terminal from '../game/components/Terminal.svelte';
	import ChallengeArena from './ChallengeArena.svelte';
	import type { LogLevel, LogEntry } from '../game/types';

	type Direction = 'UP' | 'RIGHT' | 'DOWN' | 'LEFT';
	type Action = 'move' | 'rotate' | 'fire' | 'scan';
	type Fighter = { x: number; y: number; direction: Direction; hp: number };
	type Bullet = {
		id: number;
		x: number;
		y: number;
		owner: 'PLAYER' | 'AI';
		direction: Direction;
	};

	const BATTLE_DURATION = 30;
	const TICK_MS = 420;
	const MAPS = {
		1: ['3,1', '3,2', '3,5', '3,6', '6,1', '6,2', '6,5', '6,6', '4,3', '5,3', '4,4', '5,4'],
		2: ['2,1', '2,2', '2,3', '7,4', '7,5', '7,6', '4,2', '5,2', '4,5', '5,5'],
		3: ['3,1', '4,1', '5,2', '6,2', '2,4', '3,4', '6,5', '7,5', '4,6', '5,6']
	} as const;
	const mapId = Math.min(3, Math.max(1, Number(page.url.searchParams.get('map')) || 1)) as
		| 1
		| 2
		| 3;
	const INITIAL_WALLS = [...MAPS[mapId]];

	let phase = $state<'prepare' | 'battle' | 'finished'>('prepare');
	let difficulty = $state<'easy' | 'medium' | 'hard'>('medium');
	let secondsLeft = $state(60);
	let player = $state<Fighter>({ x: 1, y: 6, direction: 'UP', hp: 100 });
	let ai = $state<Fighter>({ x: 8, y: 1, direction: 'DOWN', hp: 100 });

	$effect(() => {
		if (phase === 'prepare') {
			ai.hp = difficulty === 'easy' ? 50 : difficulty === 'hard' ? 150 : 100;
		}
	});
	let code = $state(`# Your strategy repeats during battle
move()
move()
rotate()
fire()
rotate()
move()
fire()`);
	let actions: Action[] = [];
	let battleTime = $state(0);
	let isRunning = $state(false);
	let logs = $state<LogEntry[]>([
		{
			time: new Date().toLocaleTimeString(),
			msg: 'Arena initialized. AI opponent connected.',
			level: 'ok'
		},
		{
			time: new Date().toLocaleTimeString(),
			msg: 'You have 60 seconds to create your strategy.',
			level: 'info'
		}
	]);

	let shotCells = $state(new SvelteSet<string>());
	let walls = $state(new SvelteSet<string>(INITIAL_WALLS));
	let bullets = $state<Bullet[]>([]);

	let countdownTimer: ReturnType<typeof setInterval> | null = null;
	let battleTimer: ReturnType<typeof setInterval> | null = null;
	let bulletId = 0;

	let editor: ReturnType<typeof Editor> | null = $state(null);
	let cursorInfo = $state('Ln 1, Col 1');

	function key(x: number, y: number) {
		return `${x},${y}`;
	}

	function parseCode(source: string): Action[] {
		const result: Action[] = [];
		for (const raw of source.split('\n')) {
			const line = raw.trim();
			if (!line || line.startsWith('#')) continue;
			const match = line.match(/^(move|rotate|fire|scan)\s*\(\s*\)\s*$/);
			if (match) result.push(match[1] as Action);
		}
		return result.slice(0, 40);
	}

	function addLog(msg: string, level: LogLevel = 'info') {
		logs = [...logs, { time: new Date().toLocaleTimeString(), msg, level }];
	}

	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
	let replayTicks: any[] = [];
	let replayWinner = '';

	function animateFire(
		shooter: Fighter,
		path: Array<{ x: number; y: number }>,
		owner: 'PLAYER' | 'AI'
	) {
		const trail = new SvelteSet<string>();
		path.forEach((p) => trail.add(key(p.x, p.y)));
		shotCells = trail;

		animateBullet(shooter, path, owner);
		setTimeout(() => {
			shotCells = new SvelteSet();
		}, 140);
	}

	function animateBullet(
		shooter: Fighter,
		path: Array<{ x: number; y: number }>,
		owner: 'PLAYER' | 'AI'
	) {
		const id = ++bulletId;
		bullets = [
			...bullets,
			{ id, x: shooter.x, y: shooter.y, owner, direction: shooter.direction }
		];
		if (!path.length) {
			setTimeout(() => {
				bullets = bullets.filter((bullet) => bullet.id !== id);
			}, 80);
			return;
		}
		path.forEach((cell, index) => {
			setTimeout(
				() => {
					bullets = bullets.map((bullet) => (bullet.id === id ? { ...bullet, ...cell } : bullet));
					if (index === path.length - 1)
						setTimeout(() => {
							bullets = bullets.filter((bullet) => bullet.id !== id);
						}, 55);
				},
				(index + 1) * 48
			);
		});
	}

	function finishBattle() {
		phase = 'finished';
		isRunning = false;
		if (battleTimer) clearInterval(battleTimer);
		if (replayWinner === 'draw') addLog('DRAW: Both tanks have equal HP.', 'warn');
		else if (replayWinner === 'PLAYER') addLog('VICTORY: Your strategy destroyed AI!', 'ok');
		else addLog('DEFEAT: Better luck next time.', 'error');
	}

	function battleTick() {
		if (battleTime >= replayTicks.length) {
			finishBattle();
			return;
		}
		const frame = replayTicks[battleTime];

		player = frame.player;
		ai = frame.ai;
		walls = new SvelteSet(frame.walls.map((w: any) => key(w.x, w.y)));

		for (const event of frame.events) {
			if (event.kind === 'fire') {
				animateFire(event.slot === 'PLAYER' ? player : ai, event.path, event.slot);
				if (event.path.length > 0) {
					const last = event.path[event.path.length - 1];
					const hitTank =
						(last.x === player.x && last.y === player.y) || (last.x === ai.x && last.y === ai.y);
					if (!hitTank) {
						addLog(`${event.slot} destroyed brick wall at (${last.x},${last.y})`, 'info');
					} else {
						addLog(
							`${event.slot} HIT! Target HP: ${event.slot === 'PLAYER' ? ai.hp : player.hp}`,
							'warn'
						);
					}
				}
			} else if (event.kind === 'scan' && event.slot === 'PLAYER') {
				addLog(event.hit ? 'Enemy in line of sight' : 'Scanner: no direct target', 'info');
			}
		}

		battleTime++;
	}

	async function startBattle() {
		if (phase !== 'prepare') return;
		if (editor) code = editor.getCode();
		actions = parseCode(code);
		if (!actions.length) {
			actions = ['scan'];
			addLog('No valid commands: scan() fallback enabled', 'warn');
		}
		if (countdownTimer) clearInterval(countdownTimer);
		phase = 'battle';
		isRunning = true;
		addLog(`Battle started. Commands loaded: ${actions.length}`, 'ok');

		try {
			const res = await fetch(`${API}/api/challenge/simulate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ actions, difficulty, map_id: mapId })
			});
			if (!res.ok) throw new Error('API Error');
			const data = await res.json();
			replayTicks = data.ticks;
			replayWinner = data.winner;
			battleTimer = setInterval(battleTick, TICK_MS);
		} catch (err) {
			addLog('Error: backend not reachable', 'error');
			finishBattle();
		}
	}

	function restart() {
		if (battleTimer) clearInterval(battleTimer);
		phase = 'prepare';
		secondsLeft = 60;
		battleTime = 0;
		player = { x: 1, y: 6, direction: 'UP', hp: 100 };
		ai = { x: 8, y: 1, direction: 'DOWN', hp: 100 };
		walls = new SvelteSet(INITIAL_WALLS);
		bullets = [];
		addLog('Arena reset. AI opponent reconnected.', 'info');
		startCountdown();
	}

	function startCountdown() {
		if (countdownTimer) clearInterval(countdownTimer);
		countdownTimer = setInterval(() => {
			secondsLeft--;
			if (secondsLeft <= 0) startBattle();
		}, 1000);
	}

	function handleInsertCommand(cmd: string) {
		if (editor) editor.insertAtCursor(cmd);
	}

	onMount(() => {
		startCountdown();
	});

	onDestroy(() => {
		if (countdownTimer) clearInterval(countdownTimer);
		if (battleTimer) clearInterval(battleTimer);
	});
</script>

<svelte:head>
	<title>Challenge Mode — Battle City: Code Arena</title>
</svelte:head>

<div class="flex h-screen flex-col overflow-hidden bg-surface font-mono text-sm text-on-surface">
	<div
		class="pixel-shadow-sm fixed top-2 left-1/2 z-[100] -translate-x-1/2 border-2 bg-surface-container-low px-3 py-1"
		class:border-error={phase === 'prepare' && secondsLeft <= 10}
		class:border-secondary-fixed={phase === 'prepare' && secondsLeft > 10}
		class:border-tertiary={phase !== 'prepare'}
	>
		<div class="text-[8px] font-bold tracking-widest text-on-surface-variant uppercase">
			{phase === 'prepare' ? 'Время на код' : phase === 'battle' ? 'Время боя' : 'Бой завершён'}
		</div>
		<div
			class="text-center text-lg leading-tight font-bold"
			class:text-error={phase === 'prepare' && secondsLeft <= 10}
			class:text-secondary-fixed={phase === 'prepare' && secondsLeft > 10}
			class:text-tertiary={phase !== 'prepare'}
		>
			{#if phase === 'prepare'}
				00:{String(secondsLeft).padStart(2, '0')}
			{:else}
				00:{String(
					Math.max(0, BATTLE_DURATION - Math.floor((battleTime * TICK_MS) / 1000))
				).padStart(2, '0')}
			{/if}
		</div>
	</div>

	<!-- ── HEADER ─────────────────────────────────────────────────────────── -->
	<header
		class="flex h-14 shrink-0 items-center justify-between border-b-2 border-outline-variant bg-surface px-5"
	>
		<div class="flex items-center gap-4">
			<a href="/" class="text-xl text-on-surface-variant hover:text-primary">←</a>
			<span class="font-bold text-secondary-fixed">
				⌨ CHALLENGE <span class="ml-1 text-error">VS AI</span>
			</span>
		</div>
		<div class="flex items-center gap-2">
			{#if phase === 'prepare'}
				<select
					bind:value={difficulty}
					class="cursor-pointer border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs font-bold text-on-surface hover:bg-surface-container focus:outline-none"
				>
					<option value="easy">LVL: EASY</option>
					<option value="medium">LVL: MEDIUM</option>
					<option value="hard">LVL: HARD</option>
				</select>
			{:else}
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">LVL </span>
					<span class="font-bold text-primary">{difficulty.toUpperCase()}</span>
				</div>
			{/if}
			<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
				<span class="text-on-surface-variant">PLAYER HP </span>
				<span class:text-error={player.hp <= 25} class="font-bold text-secondary-fixed"
					>{player.hp}</span
				>
			</div>
			<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
				<span class="text-on-surface-variant">AI HP </span>
				<span class:text-error={ai.hp <= 25} class="font-bold text-error">{ai.hp}</span>
			</div>
			{#if phase === 'prepare'}
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">TIME </span>
					<span class:text-error={secondsLeft <= 10} class="font-bold text-primary"
						>00:{String(secondsLeft).padStart(2, '0')}</span
					>
				</div>
			{:else}
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">TIME </span>
					<span class="font-bold text-tertiary"
						>00:{String(
							Math.max(0, BATTLE_DURATION - Math.floor((battleTime * TICK_MS) / 1000))
						).padStart(2, '0')}</span
					>
				</div>
			{/if}
			{#if phase === 'finished'}
				<button
					onclick={restart}
					class="pixel-btn border-2 border-outline-variant bg-surface px-3 py-1 text-xs hover:bg-surface-bright"
				>
					↺ RESTART
				</button>
			{/if}
		</div>
	</header>

	<!-- ── BODY ──────────────────────────────────────────────────────────── -->
	<div class="flex flex-1 overflow-hidden">
		<!-- ── COMMANDS SIDEBAR ──────────────────────────────────────────────── -->
		<Sidebar onInsertCommand={handleInsertCommand} />

		<!-- ── MAIN ─────────────────────────────────────────────────────────── -->
		<main class="flex flex-1 overflow-hidden">
			<!-- ══ CODE EDITOR ═════════════════════════════════════════════════ -->
			<section class="flex min-w-0 flex-1 flex-col border-r-2 border-outline-variant">
				<!-- Tab bar -->
				<div
					class="flex h-9 shrink-0 items-center border-b-2 border-outline-variant bg-surface-container-low text-xs"
				>
					<div
						class="flex h-full items-center border-r-2 border-outline-variant bg-surface px-4 font-bold text-secondary-fixed"
					>
						strategy.py
					</div>
					<div class="ml-auto flex items-center gap-4 px-4 text-on-surface-variant">
						<span>{cursorInfo}</span>
						<span class="text-outline">Python 3</span>
					</div>
				</div>

				<!-- Code Editor (Custom component) -->
				<div
					class="relative flex-1 bg-surface-container-lowest"
					class:pointer-events-none={phase !== 'prepare'}
					class:opacity-50={phase !== 'prepare'}
				>
					<Editor bind:this={editor} bind:code bind:cursorInfo />
				</div>

				<!-- Toolbar -->
				<div
					class="flex h-14 shrink-0 items-center justify-between border-t-2 border-outline-variant bg-surface px-4"
				>
					<div class="flex items-center gap-3">
						<button
							onclick={() => {
								if (editor && phase === 'prepare') editor.clearCode();
							}}
							class="pixel-btn border-2 border-outline-variant px-3 py-1.5 text-xs text-error hover:bg-error/10"
							disabled={phase !== 'prepare'}
						>
							🗑 CLEAR
						</button>
						<span class="text-xs text-on-surface-variant">Commands loop during battle</span>
					</div>
					<button
						onclick={startBattle}
						disabled={phase !== 'prepare'}
						class="pixel-btn border-2 border-secondary-fixed bg-secondary-fixed px-8 py-2 font-bold text-on-secondary uppercase disabled:opacity-40"
					>
						{#if phase === 'prepare'}
							✓ ГОТОВО
						{:else if phase === 'battle'}
							<span class="inline-block animate-spin">⟳</span>&nbsp;BATTLE...
						{:else}
							FINISHED
						{/if}
					</button>
				</div>
			</section>

			<!-- ══ RIGHT PANEL ════════════════════════════════════════════════ -->
			<section class="flex w-[680px] shrink-0 flex-col">
				<ChallengeArena {player} {ai} {walls} {bullets} {shotCells} />
				<Terminal {logs} {isRunning} />
			</section>
		</main>
	</div>
</div>
