<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { t } from '$lib/i18n';
	import { GameAudio } from '$lib/game/audio';
	import { SvelteSet } from 'svelte/reactivity';
	import Sidebar from '../game/components/Sidebar.svelte';
	import Editor from '../game/components/Editor.svelte';
	import Terminal from '../game/components/Terminal.svelte';
	import ChallengeArena from './ChallengeArena.svelte';
	import type { LogLevel, LogEntry } from '../game/types';

	type Direction = 'UP' | 'RIGHT' | 'DOWN' | 'LEFT';
	type Action = 'move' | 'rotate' | 'rotate_left' | 'rotate_right' | 'fire' | 'scan';
	type Fighter = { x: number; y: number; direction: Direction; hp: number };
	type ReplayFrame = {
		player: Fighter;
		ai: Fighter;
		walls: Array<{ x: number; y: number }>;
		events: Array<{
			kind: string;
			slot: 'PLAYER' | 'AI';
			path?: Array<{ x: number; y: number }>;
			hit?: boolean | 'PLAYER' | 'AI';
			collision?: boolean;
			target_hp?: number;
			wall?: { x: number; y: number; destroyed: boolean };
		}>;
	};
	type BattleResult = {
		winner: 'PLAYER' | 'AI' | 'draw';
		playerHp: number;
		aiHp: number;
		shots: number;
		hits: number;
		wallsDestroyed: number;
		commandsUsed: number;
		commandSummary: string;
	};

	const BATTLE_DURATION = 30;
	const TICK_MS = 420;
	const CHALLENGE_SETTINGS_KEY = 'codetank-challenge-settings';
	const challengeAudio = new GameAudio();
	let soundVolume = $state(0.7);
	let soundMuted = $state(false);
	let animationSpeed = $state(1);
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
	let code = $state(`# Your strategy runs once when battle starts
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
			msg: $t('challenge.arenaReady'),
			level: 'ok'
		},
		{
			time: new Date().toLocaleTimeString(),
			msg: $t('challenge.codingNotice'),
			level: 'info'
		}
	]);

	let walls = $state(new SvelteSet<string>(INITIAL_WALLS));

	let countdownTimer: ReturnType<typeof setInterval> | null = null;
	let disposed = false;
	let simulationId = 0;
	let simulationController: AbortController | null = null;

	let editor: ReturnType<typeof Editor> | null = $state(null);
	let arena: ReturnType<typeof ChallengeArena> | null = $state(null);
	let cursorInfo = $state('Ln 1, Col 1');

	function key(x: number, y: number) {
		return `${x},${y}`;
	}

	function parseCode(source: string): Action[] {
		const result: Action[] = [];
		for (const raw of source.split('\n')) {
			const line = raw.trim();
			if (!line || line.startsWith('#')) continue;
			const match = line.match(/^(move|fire|scan)\s*\(\s*\)\s*$/);
			if (match) result.push(match[1] as Action);
			else if (/^rotate\s*\(\s*['"]LEFT['"]\s*\)\s*$/i.test(line)) result.push('rotate_left');
			else if (/^rotate\s*\(\s*['"]RIGHT['"]\s*\)\s*$/i.test(line)) result.push('rotate_right');
			else if (/^rotate\s*\(\s*\)\s*$/.test(line)) result.push('rotate');
		}
		return result.slice(0, 40);
	}

	function addLog(msg: string, level: LogLevel = 'info') {
		logs = [...logs, { time: new Date().toLocaleTimeString(), msg, level }].slice(-250);
	}

	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
	let replayTicks: ReplayFrame[] = [];
	let replayWinner = '';
	let replayTickMs = $state(TICK_MS);
	let battleResult = $state<BattleResult | null>(null);

	function calculateBattleResult(): BattleResult {
		const lastFrame = replayTicks[replayTicks.length - 1];
		const playerEvents = replayTicks.flatMap((frame) =>
			frame.events.filter((event) => event.slot === 'PLAYER')
		);
		const commandCounts: Record<string, number> = {};
		for (const event of playerEvents) {
			commandCounts[event.kind] = (commandCounts[event.kind] ?? 0) + 1;
		}

		return {
			winner: replayWinner === 'PLAYER' || replayWinner === 'AI' ? replayWinner : 'draw',
			playerHp: lastFrame?.player.hp ?? player.hp,
			aiHp: lastFrame?.ai.hp ?? ai.hp,
			shots: playerEvents.filter((event) => event.kind === 'fire').length,
			hits: playerEvents.filter(
				(event) => event.kind === 'fire' && (event.hit === true || event.hit === 'AI')
			).length,
			wallsDestroyed: playerEvents.filter((event) => event.kind === 'fire' && event.wall?.destroyed)
				.length,
			commandsUsed: playerEvents.length,
			commandSummary:
				Object.entries(commandCounts)
					.map(([command, count]) => `${command}() ×${count}`)
					.join(' · ') || '—'
		};
	}

	function finishBattle() {
		if (phase === 'finished') return;
		phase = 'finished';
		isRunning = false;
		// Remove every unfinished projectile before showing the result. Apply
		// the authoritative final frame so a delayed impact cannot leave stale HP.
		arena?.resetEffects();
		const finalFrame = replayTicks[replayTicks.length - 1];
		if (finalFrame) {
			player = { ...finalFrame.player };
			ai = { ...finalFrame.ai };
			walls = new SvelteSet(finalFrame.walls.map((wall) => key(wall.x, wall.y)));
		}
		battleResult = calculateBattleResult();
		if (replayWinner === 'draw') addLog($t('challenge.drawResult'), 'warn');
		else if (replayWinner === 'PLAYER') addLog($t('challenge.victoryResult'), 'ok');
		else addLog($t('challenge.defeatResult'), 'error');
	}

	async function battleTick() {
		if (battleTime >= replayTicks.length) {
			finishBattle();
			return;
		}
		const frame = replayTicks[battleTime];
		const previousPlayer = player;
		const previousAi = ai;
		const previousWalls = new SvelteSet(walls);
		const frameWalls = new SvelteSet(frame.walls.map((wall) => key(wall.x, wall.y)));
		const playerDamaged = frame.player.hp < previousPlayer.hp;
		const aiDamaged = frame.ai.hp < previousAi.hp;
		const wallDestroyed = frameWalls.size < previousWalls.size;

		player = { ...frame.player, hp: playerDamaged ? previousPlayer.hp : frame.player.hp };
		ai = { ...frame.ai, hp: aiDamaged ? previousAi.hp : frame.ai.hp };
		walls = wallDestroyed ? previousWalls : frameWalls;
		if (frame.events.some((event) => event.kind === 'move')) challengeAudio.play('move');
		const animations: Promise<void>[] = [];

		for (const event of frame.events) {
			if (event.kind === 'fire') {
				challengeAudio.play('fire');
				const path = event.path ?? [];
				if (event.collision) {
					const collisionAnimation = arena?.animateShot(
						event.slot,
						path,
						event.slot === 'PLAYER' ? 'collision' : 'none',
						() => undefined
					);
					if (collisionAnimation) animations.push(collisionAnimation);
					if (event.slot === 'PLAYER') {
						challengeAudio.play('impact');
						addLog($t('challenge.bulletsCollided'), 'info');
					}
					continue;
				}
				const last = path[path.length - 1];
				const hitTank = event.hit === true || event.hit === 'PLAYER' || event.hit === 'AI';
				const impact = hitTank ? 'tank' : event.wall?.destroyed ? 'wall' : 'none';
				const onImpact = () => {
					if (event.slot === 'PLAYER' && hitTank && aiDamaged)
						ai = { ...ai, hp: Math.min(ai.hp, frame.ai.hp) };
					if (event.slot === 'AI' && hitTank && playerDamaged)
						player = { ...player, hp: Math.min(player.hp, frame.player.hp) };
					if (event.wall?.destroyed)
						walls = new SvelteSet([...walls].filter((wall) => frameWalls.has(wall)));
					if (hitTank) {
						const targetHp = event.slot === 'PLAYER' ? frame.ai.hp : frame.player.hp;
						challengeAudio.play(targetHp <= 0 ? 'explosion' : 'impact');
					} else if (event.wall?.destroyed) challengeAudio.play('impact');

					if (!path.length) return;
					if (event.wall?.destroyed) {
						addLog(
							$t('challenge.wallDestroyed', { slot: event.slot, x: last.x, y: last.y }),
							'info'
						);
					} else if (hitTank) {
						addLog(
							$t('challenge.tankHit', {
								slot: event.slot,
								hp: event.slot === 'PLAYER' ? ai.hp : player.hp
							}),
							'warn'
						);
					}
				};
				if (arena) animations.push(arena.animateShot(event.slot, path, impact, onImpact));
				else onImpact();
			} else if (event.kind === 'scan' && event.slot === 'PLAYER') {
				addLog(event.hit ? $t('challenge.enemyVisible') : $t('challenge.noTarget'), 'info');
			}
		}

		await Promise.all(animations);
		battleTime++;
	}

	function waitForReplayFrame(delayMs: number, signal: AbortSignal) {
		return new Promise<void>((resolve) => {
			if (delayMs <= 0 || signal.aborted) {
				resolve();
				return;
			}
			let timer: ReturnType<typeof setTimeout> | null = null;
			const complete = () => {
				if (timer !== null) clearTimeout(timer);
				signal.removeEventListener('abort', complete);
				resolve();
			};
			timer = setTimeout(complete, delayMs);
			signal.addEventListener('abort', complete, { once: true });
		});
	}

	async function playReplay(currentSimulation: number, controller: AbortController) {
		while (
			!disposed &&
			currentSimulation === simulationId &&
			phase === 'battle' &&
			battleTime < replayTicks.length
		) {
			const startedAt = performance.now();
			await battleTick();
			if (disposed || currentSimulation !== simulationId || controller.signal.aborted) return;
			const tickDuration = replayTickMs / animationSpeed;
			await waitForReplayFrame(
				Math.max(0, tickDuration - (performance.now() - startedAt)),
				controller.signal
			);
		}
		if (!disposed && currentSimulation === simulationId && !controller.signal.aborted)
			finishBattle();
	}

	async function startBattle() {
		if (phase !== 'prepare') return;
		if (editor) code = editor.getCode();
		const firstIssue = editor?.getErrors()[0];
		if (firstIssue) {
			addLog(`${$t('editor.line')} ${firstIssue.line}: ${firstIssue.message}`, 'error');
			return;
		}
		actions = parseCode(code);
		if (!actions.length) {
			addLog($t('challenge.noCommands'), 'warn');
		}
		if (countdownTimer) clearInterval(countdownTimer);
		phase = 'battle';
		isRunning = true;
		const currentSimulation = ++simulationId;
		simulationController?.abort();
		const controller = new AbortController();
		simulationController = controller;
		addLog($t('challenge.battleStarted', { count: actions.length }), 'ok');

		try {
			const res = await fetch(`${API}/api/challenge/simulate`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ actions, code, difficulty, map_id: mapId }),
				signal: controller.signal
			});
			if (disposed || currentSimulation !== simulationId) return;
			if (!res.ok) {
				const payload = await res.json().catch(() => null);
				throw new Error(payload?.detail ?? `API returned ${res.status}`);
			}
			const data = await res.json();
			if (disposed || currentSimulation !== simulationId) return;
			replayTicks = data.ticks;
			replayWinner = data.winner;
			replayTickMs = data.tick_ms ?? TICK_MS;
			await playReplay(currentSimulation, controller);
		} catch (error) {
			if (
				disposed ||
				currentSimulation !== simulationId ||
				(error instanceof DOMException && error.name === 'AbortError')
			)
				return;
			addLog(
				error instanceof Error ? `Error: ${error.message}` : $t('challenge.requestError'),
				'error'
			);
			phase = 'prepare';
			isRunning = false;
			secondsLeft = 60;
			startCountdown();
		} finally {
			if (currentSimulation === simulationId) simulationController = null;
		}
	}

	function restart() {
		simulationId++;
		simulationController?.abort();
		simulationController = null;
		challengeAudio.stop();
		phase = 'prepare';
		secondsLeft = 60;
		battleTime = 0;
		battleResult = null;
		replayTickMs = TICK_MS;
		player = { x: 1, y: 6, direction: 'UP', hp: 100 };
		ai = { x: 8, y: 1, direction: 'DOWN', hp: 100 };
		walls = new SvelteSet(INITIAL_WALLS);
		arena?.resetEffects();
		addLog($t('challenge.arenaReset'), 'info');
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

	function saveChallengeSettings() {
		challengeAudio.configure(soundVolume, soundMuted);
		localStorage.setItem(
			CHALLENGE_SETTINGS_KEY,
			JSON.stringify({ volume: soundVolume, muted: soundMuted, animationSpeed })
		);
	}

	function toggleSound() {
		soundMuted = !soundMuted;
		saveChallengeSettings();
	}

	function updateChallengeVolume(event: Event) {
		soundVolume = Number((event.currentTarget as HTMLInputElement).value);
		saveChallengeSettings();
	}

	function updateChallengeAnimationSpeed(event: Event) {
		animationSpeed = Number((event.currentTarget as HTMLSelectElement).value);
		saveChallengeSettings();
	}

	onMount(async () => {
		try {
			const saved = JSON.parse(localStorage.getItem(CHALLENGE_SETTINGS_KEY) ?? '{}');
			const savedVolume = Number(saved.volume);
			soundVolume = Number.isFinite(savedVolume) ? Math.min(1, Math.max(0, savedVolume)) : 0.7;
			soundMuted = Boolean(saved.muted);
			animationSpeed = [0.5, 1, 1.5, 2].includes(Number(saved.animationSpeed))
				? Number(saved.animationSpeed)
				: 1;
			challengeAudio.configure(soundVolume, soundMuted);
		} catch {
			// Invalid local settings use defaults.
		}
		startCountdown();
		try {
			const response = await fetch(`${API}/auth/profile`, { credentials: 'include' });
			if (!response.ok) return;
			const data = await response.json();
			const savedCode = data.progress?.last_code?.challenge?.code;
			if (typeof savedCode === 'string') editor?.setCode(savedCode);
		} catch {
			// Challenge also remains available without a signed-in profile.
		}
	});

	onDestroy(() => {
		disposed = true;
		simulationId++;
		simulationController?.abort();
		simulationController = null;
		if (countdownTimer) clearInterval(countdownTimer);
		countdownTimer = null;
		challengeAudio.stop();
	});
</script>

<svelte:head>
	<title>{$t('challenge.pageTitle')}</title>
</svelte:head>

<div
	class="flex min-h-screen flex-col bg-surface font-mono text-sm text-on-surface lg:h-screen lg:overflow-hidden"
>
	<div
		class="pixel-shadow-sm fixed top-2 left-1/2 z-[100] -translate-x-1/2 border-2 bg-surface-container-low px-3 py-1"
		class:border-error={phase === 'prepare' && secondsLeft <= 10}
		class:border-secondary-fixed={phase === 'prepare' && secondsLeft > 10}
		class:border-tertiary={phase !== 'prepare'}
	>
		<div class="text-[8px] font-bold tracking-widest text-on-surface-variant uppercase">
			{phase === 'prepare'
				? $t('challenge.codeTime')
				: phase === 'battle'
					? $t('challenge.battleTime')
					: $t('challenge.finished')}
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
					Math.max(0, BATTLE_DURATION - Math.floor((battleTime * replayTickMs) / 1000))
				).padStart(2, '0')}
			{/if}
		</div>
	</div>

	<!-- ── HEADER ─────────────────────────────────────────────────────────── -->
	<header
		class="flex min-h-14 shrink-0 flex-col items-stretch gap-2 border-b-2 border-outline-variant bg-surface px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:px-5"
	>
		<div class="flex items-center gap-4">
			<a href="/" class="text-xl text-on-surface-variant hover:text-primary">←</a>
			<span class="font-bold text-secondary-fixed">
				⌨ {$t('challenge.title')}
			</span>
		</div>
		<div class="flex max-w-full items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
			{#if phase === 'prepare'}
				<select
					bind:value={difficulty}
					class="cursor-pointer border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs font-bold text-on-surface hover:bg-surface-container focus:outline-none"
				>
					<option value="easy">{$t('challenge.level')}: {$t('challenge.easy')}</option>
					<option value="medium">{$t('challenge.level')}: {$t('challenge.medium')}</option>
					<option value="hard">{$t('challenge.level')}: {$t('challenge.hard')}</option>
				</select>
			{:else}
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('challenge.level')} </span>
					<span class="font-bold text-primary">{$t(`challenge.${difficulty}`)}</span>
				</div>
			{/if}
			<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
				<span class="text-on-surface-variant">{$t('challenge.playerHp')} </span>
				<span class:text-error={player.hp <= 25} class="font-bold text-secondary-fixed"
					>{player.hp}</span
				>
			</div>
			<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
				<span class="text-on-surface-variant">{$t('challenge.aiHp')} </span>
				<span class:text-error={ai.hp <= 25} class="font-bold text-error">{ai.hp}</span>
			</div>
			{#if phase === 'prepare'}
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('challenge.time')} </span>
					<span class:text-error={secondsLeft <= 10} class="font-bold text-primary"
						>00:{String(secondsLeft).padStart(2, '0')}</span
					>
				</div>
			{:else}
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('challenge.time')} </span>
					<span class="font-bold text-tertiary"
						>00:{String(
							Math.max(0, BATTLE_DURATION - Math.floor((battleTime * replayTickMs) / 1000))
						).padStart(2, '0')}</span
					>
				</div>
			{/if}
			<div
				class="flex items-center gap-2 border-2 border-outline-variant bg-surface-container-low px-2 py-1 text-xs"
			>
				<button
					onclick={toggleSound}
					class="font-bold text-primary"
					aria-label={soundMuted ? $t('game.soundOn') : $t('game.soundOff')}
					title={soundMuted ? $t('game.soundOn') : $t('game.soundOff')}
				>
					{soundMuted ? '🔇' : '🔊'}
				</button>
				<label class="flex items-center gap-1" title={$t('game.volume')}>
					<span class="sr-only">{$t('game.volume')}</span>
					<input
						type="range"
						min="0"
						max="1"
						step="0.05"
						value={soundVolume}
						oninput={updateChallengeVolume}
						class="w-16 accent-primary"
					/>
				</label>
			</div>
			<label
				class="flex items-center gap-1 border-2 border-outline-variant bg-surface-container-low px-2 py-1 text-xs"
			>
				<span class="text-on-surface-variant">{$t('game.animationSpeed')}</span>
				<select
					value={animationSpeed}
					onchange={updateChallengeAnimationSpeed}
					disabled={phase === 'battle'}
					class="bg-black px-1 font-bold text-primary outline-none disabled:opacity-50"
				>
					<option value={0.5}>0.5×</option>
					<option value={1}>1×</option>
					<option value={1.5}>1.5×</option>
					<option value={2}>2×</option>
				</select>
			</label>
			{#if phase === 'finished'}
				<button
					onclick={restart}
					class="pixel-btn border-2 border-outline-variant bg-surface px-3 py-1 text-xs hover:bg-surface-bright"
				>
					↺ {$t('challenge.restart')}
				</button>
			{/if}
		</div>
	</header>

	<!-- ── BODY ──────────────────────────────────────────────────────────── -->
	<div class="flex flex-1 flex-col overflow-visible lg:flex-row lg:overflow-hidden">
		<!-- ── COMMANDS SIDEBAR ──────────────────────────────────────────────── -->
		<Sidebar onInsertCommand={handleInsertCommand} />

		<!-- ── MAIN ─────────────────────────────────────────────────────────── -->
		<main class="flex min-w-0 flex-1 flex-col overflow-visible lg:flex-row lg:overflow-hidden">
			<!-- ══ CODE EDITOR ═════════════════════════════════════════════════ -->
			<section class="flex min-h-[520px] min-w-0 flex-1 flex-col border-r-2 border-outline-variant">
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
					<Editor bind:this={editor} bind:code bind:cursorInfo mode="challenge" />
				</div>

				<!-- Toolbar -->
				<div
					class="flex min-h-14 shrink-0 flex-wrap items-center justify-between gap-2 border-t-2 border-outline-variant bg-surface px-3 py-2 sm:px-4"
				>
					<div class="flex items-center gap-3">
						<button
							onclick={() => {
								if (editor && phase === 'prepare') editor.clearCode();
							}}
							class="pixel-btn border-2 border-outline-variant px-3 py-1.5 text-xs text-error hover:bg-error/10"
							disabled={phase !== 'prepare'}
						>
							🗑 {$t('challenge.clear')}
						</button>
						<span class="hidden text-xs text-on-surface-variant sm:inline"
							>{$t('challenge.runOnce')}</span
						>
					</div>
					<button
						onclick={startBattle}
						disabled={phase !== 'prepare'}
						class="pixel-btn border-2 border-secondary-fixed bg-secondary-fixed px-8 py-2 font-bold text-on-secondary uppercase disabled:opacity-40"
					>
						{#if phase === 'prepare'}
							{$t('challenge.ready')}
						{:else if phase === 'battle'}
							<span class="inline-block animate-spin">⟳</span>&nbsp;{$t('challenge.battle')}
						{:else}
							{$t('challenge.finished')}
						{/if}
					</button>
				</div>
			</section>

			<!-- ══ RIGHT PANEL ════════════════════════════════════════════════ -->
			<section class="flex w-full min-w-0 flex-col lg:w-[680px] lg:shrink-0">
				<ChallengeArena bind:this={arena} {player} {ai} {walls} {animationSpeed} />
				<Terminal {logs} {isRunning} />
			</section>
		</main>
	</div>

	{#if phase === 'finished' && battleResult}
		<div
			class="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
			role="presentation"
		>
			<div
				class="pixel-shadow w-full max-w-2xl border-4 border-outline bg-surface-container-lowest"
				role="dialog"
				aria-modal="true"
				aria-labelledby="battle-result-title"
				tabindex="-1"
			>
				<div
					class="border-b-2 border-outline-variant px-5 py-3 text-xs tracking-[0.25em] text-on-surface-variant uppercase"
				>
					{$t('challenge.resultProtocol')}
				</div>
				<div class="p-5 sm:p-7">
					<h2
						id="battle-result-title"
						class="mb-2 text-center text-4xl font-bold uppercase sm:text-5xl"
						class:text-secondary-fixed={battleResult.winner === 'PLAYER'}
						class:text-error={battleResult.winner === 'AI'}
						class:text-primary={battleResult.winner === 'draw'}
					>
						{battleResult.winner === 'PLAYER'
							? $t('challenge.resultVictory')
							: battleResult.winner === 'AI'
								? $t('challenge.resultDefeat')
								: $t('challenge.resultDraw')}
					</h2>
					<p class="mb-6 text-center text-xs text-on-surface-variant uppercase">
						{$t('challenge.resultMapLevel', {
							map: mapId,
							level: $t(`challenge.${difficulty}`)
						})}
					</p>

					<div class="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
						<div class="border-2 border-outline-variant bg-surface p-3">
							<div class="text-[10px] text-on-surface-variant uppercase">
								{$t('challenge.resultPlayerHp')}
							</div>
							<div class="text-2xl font-bold text-secondary-fixed">{battleResult.playerHp}</div>
						</div>
						<div class="border-2 border-outline-variant bg-surface p-3">
							<div class="text-[10px] text-on-surface-variant uppercase">
								{$t('challenge.resultAiHp')}
							</div>
							<div class="text-2xl font-bold text-error">{battleResult.aiHp}</div>
						</div>
						<div class="border-2 border-outline-variant bg-surface p-3">
							<div class="text-[10px] text-on-surface-variant uppercase">
								{$t('challenge.resultShots')}
							</div>
							<div class="text-2xl font-bold text-primary">{battleResult.shots}</div>
						</div>
						<div class="border-2 border-outline-variant bg-surface p-3">
							<div class="text-[10px] text-on-surface-variant uppercase">
								{$t('challenge.resultHits')}
							</div>
							<div class="text-2xl font-bold text-tertiary">{battleResult.hits}</div>
						</div>
						<div class="border-2 border-outline-variant bg-surface p-3">
							<div class="text-[10px] text-on-surface-variant uppercase">
								{$t('challenge.resultWalls')}
							</div>
							<div class="text-2xl font-bold text-tertiary">{battleResult.wallsDestroyed}</div>
						</div>
						<div class="border-2 border-outline-variant bg-surface p-3">
							<div class="text-[10px] text-on-surface-variant uppercase">
								{$t('challenge.resultCommands')}
							</div>
							<div class="text-2xl font-bold text-primary">{battleResult.commandsUsed}</div>
						</div>
					</div>

					<div class="mb-6 border-2 border-outline-variant bg-black p-3">
						<div class="mb-1 text-[10px] tracking-wider text-on-surface-variant uppercase">
							{$t('challenge.resultCommandList')}
						</div>
						<div class="text-xs break-words text-secondary-fixed">
							{battleResult.commandSummary}
						</div>
					</div>

					<div class="grid gap-3 sm:grid-cols-2">
						<button
							onclick={restart}
							class="pixel-btn border-2 border-secondary-fixed bg-secondary-fixed px-5 py-3 font-bold text-on-secondary uppercase"
						>
							↻ {$t('challenge.resultReplay')}
						</button>
						<a
							href="/challenge-maps"
							class="pixel-btn border-2 border-primary px-5 py-3 text-center font-bold text-primary uppercase hover:bg-primary/10"
						>
							{$t('challenge.resultChooseMap')}
						</a>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
