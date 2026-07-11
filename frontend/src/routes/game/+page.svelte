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

	import { onMount } from 'svelte';
	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

	const missionId = Math.min(6, Math.max(1, Number(page.url.searchParams.get('mission')) || 1));
	let mission = $state<any>(null);
	let missionLoadError = $state('');

	async function loadMission() {
		missionLoadError = '';
		try {
			const res = await fetch(`${API}/api/missions`);
			if (!res.ok) throw new Error(`API returned ${res.status}`);
			const allMissions = await res.json();
			mission = allMissions[missionId];
			if (!mission) throw new Error('Mission not found');
		} catch (e) {
			console.error('Failed to load missions', e);
			missionLoadError = 'Не удалось загрузить миссию. Проверьте подключение к серверу.';
		}
	}

	onMount(loadMission);
	const INITIAL_TANK: TankState = { x: 1, y: 6, direction: 'UP', hp: 100, score: 0 };
	const MAX_REPEAT = 100;

	let missionCompleted = $state(false);
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

	async function executeCode() {
		if (isRunning || !editor) return;
		const src = editor.getCode();
		if (!src.trim()) return;

		isRunning = true;
		missionCompleted = false;
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

			for (const tick of ticks) {
				addLog(`${tick.command}() → ${tick.log}`, 'cmd');

				tankState = tick.state;

				const objectiveComplete =
					tankState.x === mission.goal.x &&
					tankState.y === mission.goal.y &&
					(!mission.combat || !tick.enemy.alive);

				if (!missionCompleted && objectiveComplete) {
					missionCompleted = true;
					addLog(`MISSION ${missionId} COMPLETE! Цель выполнена.`, 'ok');
				}

				if (arena) {
					await arena.setTankDir(tankState.direction);
					if (tick.command === 'move' && tick.ok) {
						await arena.animateTankMove(tankState.x, tankState.y, 300);
					} else if (tick.command === 'fire') {
						await arena.animateTankFire(tankState.direction);
					} else {
						arena.setTankPos(tankState.x, tankState.y);
					}
					await arena.syncBattleState(
						tick.enemy as EnemyState,
						tick.walls as WallState[],
						tick.enemy_action
					);
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
			missionCompleted = false;
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
					<span class="text-on-surface-variant">HP </span>
					<span class:text-error={tankState.hp <= 25} class="font-bold text-secondary-fixed"
						>{tankState.hp}</span
					>
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
