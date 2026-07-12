<script lang="ts">
	import { page } from '$app/state';
	import type { LogLevel, TankState, EnemyState, WallState, LogEntry } from './types';
	import Sidebar from './components/Sidebar.svelte';
	import Editor from './components/Editor.svelte';
	import Terminal from './components/Terminal.svelte';
	import Arena from './components/Arena.svelte';

	let isRunning = $state(false);
	let sessionId = $state('');
	let cursorInfo = $state('Ln 1, Col 1');
	let code = $state('');

	import { onMount, onDestroy } from 'svelte';
	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

	const missionId = Math.min(9, Math.max(1, Number(page.url.searchParams.get('mission')) || 1));
	let mission = $state<any>(null);
	let missionLoadError = $state('');
	let enemyStates = $state<EnemyState[]>([]);

	async function loadMission() {
		missionLoadError = '';
		try {
			const res = await fetch(`${API}/api/missions`);
			if (!res.ok) throw new Error(`API returned ${res.status}`);
			const allMissions = await res.json();
			mission = allMissions[missionId];
			if (!mission) throw new Error('Mission not found');
			enemyStates = (mission.enemies ?? [mission.enemy]).map(
				(enemy: { x: number; y: number; skin?: string }, index: number) => ({
					...enemy,
					direction: 'DOWN' as const,
					hp: enemy.skin === 'heavy' || missionId === 6 || (missionId === 8 && index === 1) ? 150 : 100,
					alive: true
				})
			);
		} catch (e) {
			console.error('Failed to load missions', e);
			missionLoadError = 'Не удалось загрузить миссию. Проверьте подключение к серверу.';
		}
	}

	onMount(loadMission);
	const INITIAL_TANK: TankState = { x: 1, y: 6, direction: 'UP', hp: 100, score: 0 };
	const MAX_REPEAT = 100;

	let missionCompleted = $state(false);
	let battleSecondsLeft = $state(30);
	let battleTimer: ReturnType<typeof setInterval> | null = null;
	let tankState = $state<TankState>({ ...INITIAL_TANK });
	let logs = $state<LogEntry[]>([
		{ time: now(), msg: 'System ready. Write Python and press EXECUTE.', level: 'ok' }
	]);

	let arena = $state<ReturnType<typeof Arena> | null>(null);
	let editor = $state<ReturnType<typeof Editor> | null>(null);

	function now() {
		return new Date().toLocaleTimeString('ru-RU', { hour12: false });
	}

	function delay(ms: number) {
		return new Promise((r) => setTimeout(r, ms));
	}

	function addLog(msg: string, level: LogLevel) {
		logs = [...logs, { time: now(), msg, level }];
	}

	function stopBattleTimer() {
		if (battleTimer) clearInterval(battleTimer);
		battleTimer = null;
	}

	onDestroy(stopBattleTimer);

	async function executeCode() {
		if (isRunning || !editor) return;
		const src = editor.getCode();
		if (!src.trim()) return;

		isRunning = true;
		missionCompleted = false;
		battleSecondsLeft = 30;
		try {
			const resetResponse = await fetch(`${API}/api/game/reset?mission_id=${missionId}`, {
				method: 'POST',
				headers: sessionId ? { 'X-Session-Id': sessionId } : {}
			});
			if (!resetResponse.ok) throw new Error(`API reset returned ${resetResponse.status}`);
			const resetData = await resetResponse.json();
			if (resetData.session_id) sessionId = resetData.session_id;

			addLog(`─── Sending code to Python Backend ───`, 'info');

			const runResponse = await fetch(`${API}/api/game/run`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(sessionId ? { 'X-Session-Id': sessionId } : {})
				},
				body: JSON.stringify({ code: src })
			});

			if (!runResponse.ok) throw new Error(`API returned ${runResponse.status}`);
			const data = await runResponse.json();
			if (data.session_id) sessionId = data.session_id;

			if (data.error) {
				addLog(data.error, 'error');
				return;
			}

			// Restore scene before playback
			if (arena) {
				arena.restoreMissionScene(mission);
				arena.setTankPos(INITIAL_TANK.x, INITIAL_TANK.y);
				await arena.setTankDir('UP');
			}
			tankState = { ...INITIAL_TANK };

			const ticks = data.ticks || [];
			addLog(`Backend simulation complete. Playing ${ticks.length} steps.`, 'ok');
			const battleDeadline = Date.now() + 30_000;
			stopBattleTimer();
			battleTimer = setInterval(() => {
				battleSecondsLeft = Math.max(0, Math.ceil((battleDeadline - Date.now()) / 1000));
			}, 200);

			for (const tick of ticks) {
				if (Date.now() >= battleDeadline) {
					battleSecondsLeft = 0;
					addLog('TIME LIMIT: 30 seconds. Battle stopped.', 'warn');
					break;
				}
				addLog(`${tick.command}() → ${tick.log}`, 'cmd');

				const previousPlayerHp = tankState.hp;
				const previousEnemies = enemyStates;
				tankState = tick.state;
				enemyStates = (tick.enemies ?? [tick.enemy]) as EnemyState[];
				const enemyHitIndexes = enemyStates
					.map((enemy, index) => (enemy.hp < (previousEnemies[index]?.hp ?? enemy.hp) ? index : -1))
					.filter((index) => index >= 0);
				arena?.setTankAlive(tankState.hp > 0);
				if (tankState.hp < previousPlayerHp) arena?.flashPlayerHit();

				const objectiveComplete =
					tankState.x === mission.goal.x &&
					tankState.y === mission.goal.y &&
					(!mission.combat || !(tick.enemies ?? [tick.enemy]).some((enemy: EnemyState) => enemy.alive));

				if (!missionCompleted && objectiveComplete) {
					missionCompleted = true;
					addLog(`MISSION ${missionId} COMPLETE! Цель выполнена.`, 'ok');
				}

				if (arena) {
					await arena.setTankDir(tankState.direction);
					let playerShot: Promise<void> | undefined;
					if (tick.command === 'move' && tick.ok) {
						await arena.animateTankMove(tankState.x, tankState.y, 300);
					} else if (tick.command === 'fire') {
						playerShot = arena.animateTankFire(tankState.direction);
					} else {
						arena.setTankPos(tankState.x, tankState.y);
					}
					const enemyPlayback = arena.syncBattleState(
						tick.enemy as EnemyState,
						tick.walls as WallState[],
						tick.enemy_action,
						(tick.enemies ?? [tick.enemy]) as EnemyState[],
						(tick.enemy_actions ?? [tick.enemy_action]) as string[],
						enemyHitIndexes
					);
					await Promise.all([enemyPlayback, ...(playerShot ? [playerShot] : [])]);
				}

				for (const event of tick.events as string[]) {
					addLog(
						event,
						event.includes('DESTROYED') ? 'error' : event.includes('hit') ? 'warn' : 'info'
					);
				}

				await delay(100); // Wait briefly before next tick

				if (tankState.hp <= 0 || missionCompleted) break;
			}

			addLog(
				tankState.hp > 0
					? `─── Done. Score: ${tankState.score} ───`
					: '─── Program stopped: tank destroyed ───',
				tankState.hp > 0 ? 'ok' : 'error'
			);
		} catch {
			addLog('ERROR: backend not reachable', 'error');
		} finally {
			stopBattleTimer();
			isRunning = false;
		}
	}

	async function resetGame() {
		try {
			const response = await fetch(`${API}/api/game/reset?mission_id=${missionId}`, {
				method: 'POST',
				headers: sessionId ? { 'X-Session-Id': sessionId } : {}
			});
			if (!response.ok) throw new Error(`API returned ${response.status}`);
			const data = await response.json();
			if (data.session_id) sessionId = data.session_id;
			tankState = { ...INITIAL_TANK };
			enemyStates = (mission.enemies ?? [mission.enemy]).map(
				(enemy: { x: number; y: number; skin?: string }, index: number) => ({
					...enemy,
					direction: 'DOWN' as const,
					hp: enemy.skin === 'heavy' || missionId === 6 || (missionId === 8 && index === 1) ? 150 : 100,
					alive: true
				})
			);
			missionCompleted = false;
			battleSecondsLeft = 30;
			stopBattleTimer();
			if (arena) {
				arena.restoreMissionScene(mission);
				arena.setTankPos(INITIAL_TANK.x, INITIAL_TANK.y);
				await arena.setTankDir('UP');
			}
			addLog('Game reset.', 'info');
		} catch {
			addLog('ERROR: backend not reachable', 'error');
		}
	}

	function handleInsertCommand(cmd: string) {
		if (editor) editor.insertAtCursor(cmd);
	}
</script>

<svelte:head>
	<title>Single-Player — Battle City: Code Arena</title>
</svelte:head>

<div class="flex h-screen flex-col overflow-hidden bg-surface font-mono text-sm text-on-surface">
	{#if mission}
		<!-- ── HEADER ─────────────────────────────────────────────────────────── -->
		<header
			class="flex h-14 shrink-0 items-center justify-between border-b-2 border-outline-variant bg-surface px-5"
		>
			<div class="flex items-center gap-4">
				<a href="/" class="text-xl text-on-surface-variant hover:text-primary">←</a>
				<span class="font-bold text-secondary-fixed">
					⌨ BATTLE CODE <span class="ml-1 border border-secondary-fixed px-1 text-xs">V3.0</span>
				</span>
				<span class="hidden text-xs tracking-widest text-on-surface-variant uppercase md:block">
					// MISSION 0{missionId}: {mission.title}
				</span>
			</div>
			<div class="flex items-center gap-2">
				<div
					class="border-2 bg-surface-container-low px-3 py-1 text-xs"
					class:border-error={isRunning && battleSecondsLeft <= 10}
					class:border-secondary-fixed={!isRunning || battleSecondsLeft > 10}
				>
					<span class="text-on-surface-variant">TIME </span>
					<span class:text-error={isRunning && battleSecondsLeft <= 10} class="font-bold text-secondary-fixed">
						00:{String(battleSecondsLeft).padStart(2, '0')}
					</span>
				</div>
				<div class="border-2 border-secondary-fixed bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">TARGET </span>
					<span class="font-bold text-secondary-fixed">({mission.goal.x},{mission.goal.y})</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">POS </span>
					<span class="font-bold text-secondary-fixed">({tankState.x},{tankState.y})</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">DIR </span>
					<span class="font-bold text-tertiary">{tankState.direction}</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">SCORE </span>
					<span class="font-bold text-primary">{tankState.score}</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">PLAYER HP </span>
					<span class:text-error={tankState.hp <= 25} class="font-bold text-secondary-fixed"
						>{tankState.hp}</span
					>
				</div>
				<div class="border-2 border-error bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">ENEMY HP </span>
					<span class="font-bold text-error">
						{enemyStates.length ? enemyStates.map((enemy) => enemy.hp).join('/') : '—'}
					</span>
				</div>
				<button
					onclick={resetGame}
					class="pixel-btn border-2 border-outline-variant bg-surface px-3 py-1 text-xs hover:bg-surface-bright"
				>
					↺ RESET
				</button>
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
							main.py
						</div>
						<div class="ml-auto flex items-center gap-4 px-4 text-on-surface-variant">
							<span>{cursorInfo}</span>
							<span class="text-outline">Python 3</span>
						</div>
					</div>

					<Editor bind:this={editor} bind:code bind:cursorInfo />

					<!-- Toolbar -->
					<div
						class="flex h-14 shrink-0 items-center justify-between border-t-2 border-outline-variant bg-surface px-4"
					>
						<div class="flex items-center gap-3">
							<button
								onclick={() => {
									if (editor) editor.clearCode();
								}}
								class="pixel-btn border-2 border-outline-variant px-3 py-1.5 text-xs text-error hover:bg-error/10"
							>
								🗑 CLEAR
							</button>
							<span class="text-xs text-on-surface-variant"
								>UTF-8 · Tab = 4 spaces · Ctrl+Z undo</span
							>
						</div>
						<button
							onclick={executeCode}
							disabled={isRunning}
							class="pixel-btn border-2 border-secondary-fixed bg-secondary-fixed px-8 py-2 font-bold text-on-secondary uppercase disabled:opacity-40"
						>
							{#if isRunning}
								<span class="inline-block animate-spin">⟳</span>&nbsp;RUNNING...
							{:else}
								▶&nbsp;EXECUTE CODE
							{/if}
						</button>
					</div>
				</section>

				<!-- ══ RIGHT PANEL ════════════════════════════════════════════════ -->
				<section class="flex w-[680px] shrink-0 flex-col">
					<Arena bind:this={arena} {mission} initialTankState={INITIAL_TANK} />
					<Terminal {logs} {isRunning} />
				</section>
			</main>
		</div>
	{:else if missionLoadError}
		<div class="flex flex-1 flex-col items-center justify-center gap-5 text-center">
			<div class="text-xl tracking-wider text-error">{missionLoadError}</div>
			<button
				onclick={loadMission}
				class="pixel-btn border-2 border-secondary-fixed px-6 py-2 font-bold text-secondary-fixed uppercase"
			>
				Повторить
			</button>
		</div>
	{:else}
		<div class="flex flex-1 items-center justify-center">
			<div class="animate-pulse text-2xl tracking-widest text-secondary-fixed">
				LOADING MISSION...
			</div>
		</div>
	{/if}
</div>
