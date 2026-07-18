<script lang="ts">
	import { page } from '$app/state';
	import { t } from '$lib/i18n';
	import type { LogLevel, TankState, EnemyState, WallState, LogEntry } from './types';
	import Sidebar from './components/Sidebar.svelte';
	import Editor from './components/Editor.svelte';
	import Terminal from './components/Terminal.svelte';
	import Arena from './components/Arena.svelte';
	import { GameAudio } from '$lib/game/audio';

	let isRunning = $state(false);
	let sessionId = $state('');
	let cursorInfo = $state('Ln 1, Col 1');
	let code = $state('');

	import { onMount, onDestroy } from 'svelte';
	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
	const MISSION_SETTINGS_KEY = 'codetank-mission-settings';
	const missionAudio = new GameAudio();
	let soundVolume = $state(0.7);
	let soundMuted = $state(false);
	let animationSpeed = $state(1);

	const missionId = Math.min(9, Math.max(1, Number(page.url.searchParams.get('mission')) || 1));
	let mission = $state<{
		title: string;
		combat: boolean;
		goal: { x: number; y: number };
		enemy: { x: number; y: number; skin?: string };
		enemies?: Array<{ x: number; y: number; skin?: string }>;
		walls: WallState[];
	} | null>(null);
	let missionLoadError = $state('');
	let enemyStates = $state<EnemyState[]>([]);

	async function loadMission() {
		missionLoadError = '';
		try {
			const res = await fetch(`${API}/api/missions`);
			if (!res.ok) throw new Error(`API returned ${res.status}`);
			const allMissions = await res.json();
			mission = allMissions[missionId];
			if (!mission) throw new Error($t('game.missionNotFound'));
			enemyStates = (mission.enemies ?? [mission.enemy]).map(
				(enemy: { x: number; y: number; skin?: string }, index: number) => ({
					...enemy,
					direction: 'DOWN' as const,
					hp:
						enemy.skin === 'heavy' || missionId === 6 || (missionId === 8 && index === 1)
							? 150
							: 100,
					alive: true
				})
			);
		} catch (e) {
			console.error('Failed to load missions', e);
			missionLoadError = $t('game.loadError');
		}
	}

	onMount(async () => {
		try {
			const savedSettings = JSON.parse(localStorage.getItem(MISSION_SETTINGS_KEY) ?? '{}');
			const savedVolume = Number(savedSettings.volume);
			soundVolume = Number.isFinite(savedVolume) ? Math.min(1, Math.max(0, savedVolume)) : 0.7;
			soundMuted = Boolean(savedSettings.muted);
			animationSpeed = [0.5, 1, 1.5, 2].includes(Number(savedSettings.animationSpeed))
				? Number(savedSettings.animationSpeed)
				: 1;
			missionAudio.configure(soundVolume, soundMuted);
		} catch {
			// Invalid local settings fall back to safe defaults.
		}
		await loadMission();
		try {
			const response = await fetch(`${API}/auth/profile`, { credentials: 'include' });
			if (!response.ok) return;
			const data = await response.json();
			const savedCode = data.progress?.last_code?.mission?.code;
			if (typeof savedCode === 'string') editor?.setCode(savedCode);
		} catch {
			// Loading saved code is optional for anonymous and offline play.
		}
	});

	function saveMissionSettings() {
		missionAudio.configure(soundVolume, soundMuted);
		localStorage.setItem(
			MISSION_SETTINGS_KEY,
			JSON.stringify({ volume: soundVolume, muted: soundMuted, animationSpeed })
		);
	}

	function toggleSound() {
		soundMuted = !soundMuted;
		saveMissionSettings();
	}

	function updateMissionVolume(event: Event) {
		soundVolume = Number((event.currentTarget as HTMLInputElement).value);
		saveMissionSettings();
	}

	function updateMissionAnimationSpeed(event: Event) {
		animationSpeed = Number((event.currentTarget as HTMLSelectElement).value);
		saveMissionSettings();
	}
	const INITIAL_TANK: TankState = { x: 1, y: 6, direction: 'UP', hp: 100, score: 0 };

	let missionCompleted = $state(false);
	let battleSecondsLeft = $state(30);
	let battleTimer: ReturnType<typeof setInterval> | null = null;
	let tankState = $state<TankState>({ ...INITIAL_TANK });
	let logs = $state<LogEntry[]>([{ time: now(), msg: $t('game.systemReady'), level: 'ok' }]);

	let arena = $state<ReturnType<typeof Arena> | null>(null);
	let editor = $state<ReturnType<typeof Editor> | null>(null);
	let disposed = false;
	let executionId = 0;
	let runController: AbortController | null = null;

	function now() {
		return new Date().toLocaleTimeString('ru-RU', { hour12: false });
	}

	function delay(ms: number) {
		return new Promise((r) => setTimeout(r, ms));
	}

	function addLog(msg: string, level: LogLevel) {
		logs = [...logs, { time: now(), msg, level }].slice(-250);
	}

	async function saveMissionProgress() {
		if (!sessionId) return;
		try {
			const response = await fetch(`${API}/auth/progress/missions/${missionId}`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ session_id: sessionId })
			});
			if (response.ok) addLog($t('game.progressSaved'), 'ok');
		} catch {
			// A profile is optional; a network error must not interrupt the mission.
		}
	}

	function stopBattleTimer() {
		if (battleTimer) clearInterval(battleTimer);
		battleTimer = null;
	}

	onDestroy(() => {
		disposed = true;
		executionId++;
		runController?.abort();
		runController = null;
		stopBattleTimer();
		missionAudio.stop();
	});

	async function executeCode() {
		if (isRunning || !editor || !mission) return;
		const src = editor.getCode();
		if (!src.trim()) return;
		const firstIssue = editor.getErrors()[0];
		if (firstIssue) {
			addLog(`${$t('editor.line')} ${firstIssue.line}: ${firstIssue.message}`, 'error');
			return;
		}

		isRunning = true;
		const currentExecution = ++executionId;
		runController?.abort();
		const controller = new AbortController();
		runController = controller;
		missionCompleted = false;
		battleSecondsLeft = 30;
		try {
			const resetResponse = await fetch(`${API}/api/game/reset?mission_id=${missionId}`, {
				method: 'POST',
				headers: sessionId ? { 'X-Session-Id': sessionId } : {},
				signal: controller.signal
			});
			if (disposed || currentExecution !== executionId) return;
			if (!resetResponse.ok) throw new Error(`API reset returned ${resetResponse.status}`);
			const resetData = await resetResponse.json();
			if (resetData.session_id) sessionId = resetData.session_id;

			addLog($t('game.sendingCode'), 'info');

			const runResponse = await fetch(`${API}/api/game/run`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(sessionId ? { 'X-Session-Id': sessionId } : {})
				},
				body: JSON.stringify({ code: src }),
				signal: controller.signal
			});
			if (disposed || currentExecution !== executionId) return;

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
			let previousWallCount = mission.walls.length;
			addLog($t('game.simulationReady', { count: ticks.length }), 'ok');
			const battleDeadline = Date.now() + 30_000;
			stopBattleTimer();
			battleTimer = setInterval(() => {
				battleSecondsLeft = Math.max(0, Math.ceil((battleDeadline - Date.now()) / 1000));
			}, 200);

			for (const tick of ticks) {
				if (disposed || currentExecution !== executionId) return;
				if (Date.now() >= battleDeadline) {
					battleSecondsLeft = 0;
					addLog($t('game.timeLimit'), 'warn');
					break;
				}
				addLog(`${tick.command}() → ${tick.log}`, 'cmd');

				const previousPlayerHp = tankState.hp;
				const previousEnemies = enemyStates;
				const nextTankState = tick.state as TankState;
				const nextEnemyStates = (tick.enemies ?? [tick.enemy]) as EnemyState[];
				tankState = { ...nextTankState, hp: previousPlayerHp };
				enemyStates = nextEnemyStates.map((enemy, index) => ({
					...enemy,
					hp: previousEnemies[index]?.hp ?? enemy.hp,
					alive: previousEnemies[index]?.alive ?? enemy.alive
				}));
				const enemyHitIndexes = nextEnemyStates
					.map((enemy, index) => (enemy.hp < (previousEnemies[index]?.hp ?? enemy.hp) ? index : -1))
					.filter((index) => index >= 0);
				const enemyActions = (tick.enemy_actions ?? [tick.enemy_action]) as string[];
				const wallDestroyed = (tick.walls as WallState[]).length < previousWallCount;
				previousWallCount = (tick.walls as WallState[]).length;

				const objectiveComplete =
					nextTankState.x === mission.goal.x &&
					nextTankState.y === mission.goal.y &&
					(!mission.combat ||
						!(tick.enemies ?? [tick.enemy]).some((enemy: EnemyState) => enemy.alive));

				if (!missionCompleted && objectiveComplete) {
					missionCompleted = true;
					addLog($t('game.missionComplete', { mission: missionId }), 'ok');
					void saveMissionProgress();
				}

				if (arena) {
					await arena.setTankDir(nextTankState.direction);
					let playerShot: Promise<void> | undefined;
					if (tick.command === 'move' && tick.ok) {
						missionAudio.play('move');
						await arena.animateTankMove(nextTankState.x, nextTankState.y, 300);
					} else if (tick.command === 'fire') {
						missionAudio.play('fire');
						playerShot = arena.animateTankFire(nextTankState.direction);
					} else {
						arena.setTankPos(nextTankState.x, nextTankState.y);
					}
					const enemyPlayback = arena.syncBattleState(
						tick.enemy as EnemyState,
						tick.walls as WallState[],
						tick.enemy_action,
						nextEnemyStates,
						enemyActions,
						enemyHitIndexes
					);
					if (enemyActions.includes('move')) missionAudio.play('move');
					for (const action of enemyActions) {
						if (action === 'fire') missionAudio.play('fire');
					}
					await Promise.all([enemyPlayback, ...(playerShot ? [playerShot] : [])]);
					if (disposed || currentExecution !== executionId) return;
				}
				const playerWasHit = nextTankState.hp < previousPlayerHp;
				const tankDestroyed =
					(playerWasHit && nextTankState.hp <= 0) ||
					enemyHitIndexes.some((index) => !nextEnemyStates[index]?.alive);
				if (tankDestroyed) missionAudio.play('explosion');
				else if (playerWasHit || enemyHitIndexes.length > 0 || wallDestroyed)
					missionAudio.play('impact');
				tankState = nextTankState;
				enemyStates = nextEnemyStates;
				if (nextTankState.hp < previousPlayerHp) {
					if (nextTankState.hp > 0) arena?.flashPlayerHit();
					else arena?.setTankAlive(false);
				} else arena?.setTankAlive(nextTankState.hp > 0);

				for (const event of tick.events as string[]) {
					addLog(
						event,
						event.includes('DESTROYED') ? 'error' : event.includes('hit') ? 'warn' : 'info'
					);
				}

				await delay(100 / animationSpeed); // Wait briefly before next tick
				if (disposed || currentExecution !== executionId) return;

				if (tankState.hp <= 0 || missionCompleted) break;
			}

			addLog(
				tankState.hp > 0 ? $t('game.programComplete') : $t('game.programDestroyed'),
				tankState.hp > 0 ? 'ok' : 'error'
			);
		} catch (error) {
			if (
				disposed ||
				currentExecution !== executionId ||
				(error instanceof DOMException && error.name === 'AbortError')
			)
				return;
			addLog(error instanceof Error ? `ERROR: ${error.message}` : $t('game.requestError'), 'error');
		} finally {
			if (currentExecution === executionId) {
				stopBattleTimer();
				isRunning = false;
				runController = null;
			}
		}
	}

	async function resetGame() {
		if (!mission) return;
		executionId++;
		runController?.abort();
		runController = null;
		isRunning = false;
		stopBattleTimer();
		missionAudio.stop();
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
					hp:
						enemy.skin === 'heavy' || missionId === 6 || (missionId === 8 && index === 1)
							? 150
							: 100,
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
			addLog($t('game.gameReset'), 'info');
		} catch (error) {
			addLog(error instanceof Error ? `ERROR: ${error.message}` : $t('game.requestError'), 'error');
		}
	}

	function handleInsertCommand(cmd: string) {
		if (editor) editor.insertAtCursor(cmd);
	}
</script>

<svelte:head>
	<title>{$t('game.pageTitle', { mission: missionId })}</title>
</svelte:head>

<div
	class="flex min-h-screen flex-col bg-surface font-mono text-sm text-on-surface lg:h-screen lg:overflow-hidden"
>
	{#if mission}
		<!-- ── HEADER ─────────────────────────────────────────────────────────── -->
		<header
			class="flex min-h-14 shrink-0 flex-col items-stretch gap-2 border-b-2 border-outline-variant bg-surface px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:px-5"
		>
			<div class="flex items-center gap-4">
				<a href="/" class="text-xl text-on-surface-variant hover:text-primary">←</a>
				<span class="font-bold text-secondary-fixed">
					⌨ {$t('game.header')}
					<span class="ml-1 border border-secondary-fixed px-1 text-xs">V3.0</span>
				</span>
				<span class="hidden text-xs tracking-widest text-on-surface-variant uppercase md:block">
					// MISSION 0{missionId}: {$t(`missions.items.${missionId}.title`)}
				</span>
			</div>
			<div class="flex max-w-full items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
				<div
					class="border-2 bg-surface-container-low px-3 py-1 text-xs"
					class:border-error={isRunning && battleSecondsLeft <= 10}
					class:border-secondary-fixed={!isRunning || battleSecondsLeft > 10}
				>
					<span class="text-on-surface-variant">{$t('game.time')} </span>
					<span
						class:text-error={isRunning && battleSecondsLeft <= 10}
						class="font-bold text-secondary-fixed"
					>
						00:{String(battleSecondsLeft).padStart(2, '0')}
					</span>
				</div>
				<div class="border-2 border-secondary-fixed bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('game.target')} </span>
					<span class="font-bold text-secondary-fixed">({mission.goal.x},{mission.goal.y})</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('game.position')} </span>
					<span class="font-bold text-secondary-fixed">({tankState.x},{tankState.y})</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('game.direction')} </span>
					<span class="font-bold text-tertiary">{tankState.direction}</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('game.score')} </span>
					<span class="font-bold text-primary">{tankState.score}</span>
				</div>
				<div class="border-2 border-outline-variant bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('game.playerHp')} </span>
					<span class:text-error={tankState.hp <= 25} class="font-bold text-secondary-fixed"
						>{tankState.hp}</span
					>
				</div>
				<div class="border-2 border-error bg-surface-container-low px-3 py-1 text-xs">
					<span class="text-on-surface-variant">{$t('game.enemyHp')} </span>
					<span class="font-bold text-error">
						{enemyStates.length ? enemyStates.map((enemy) => enemy.hp).join('/') : '—'}
					</span>
				</div>
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
							oninput={updateMissionVolume}
							class="w-20 accent-primary"
						/>
					</label>
				</div>
				<label
					class="flex items-center gap-1 border-2 border-outline-variant bg-surface-container-low px-2 py-1 text-xs"
				>
					<span class="text-on-surface-variant">{$t('game.animationSpeed')}</span>
					<select
						value={animationSpeed}
						onchange={updateMissionAnimationSpeed}
						class="bg-black px-1 font-bold text-primary outline-none"
					>
						<option value={0.5}>0.5×</option>
						<option value={1}>1×</option>
						<option value={1.5}>1.5×</option>
						<option value={2}>2×</option>
					</select>
				</label>
				<button
					onclick={resetGame}
					class="pixel-btn border-2 border-outline-variant bg-surface px-3 py-1 text-xs hover:bg-surface-bright"
				>
					↺ {$t('game.reset')}
				</button>
			</div>
		</header>

		<!-- ── BODY ──────────────────────────────────────────────────────────── -->
		<div class="flex flex-1 flex-col overflow-visible lg:flex-row lg:overflow-hidden">
			<!-- ── COMMANDS SIDEBAR ──────────────────────────────────────────────── -->
			<Sidebar onInsertCommand={handleInsertCommand} />

			<!-- ── MAIN ─────────────────────────────────────────────────────────── -->
			<main class="flex min-w-0 flex-1 flex-col overflow-visible lg:flex-row lg:overflow-hidden">
				<!-- ══ CODE EDITOR ═════════════════════════════════════════════════ -->
				<section
					class="flex min-h-[520px] min-w-0 flex-1 flex-col border-r-2 border-outline-variant"
				>
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
						class="flex min-h-14 shrink-0 flex-wrap items-center justify-between gap-2 border-t-2 border-outline-variant bg-surface px-3 py-2 sm:px-4"
					>
						<div class="flex items-center gap-3">
							<button
								onclick={() => {
									if (editor) editor.clearCode();
								}}
								class="pixel-btn border-2 border-outline-variant px-3 py-1.5 text-xs text-error hover:bg-error/10"
							>
								🗑 {$t('game.clear')}
							</button>
							<span class="hidden text-xs text-on-surface-variant sm:inline"
								>{$t('game.editorHelp')}</span
							>
						</div>
						<button
							onclick={executeCode}
							disabled={isRunning}
							class="pixel-btn border-2 border-secondary-fixed bg-secondary-fixed px-8 py-2 font-bold text-on-secondary uppercase disabled:opacity-40"
						>
							{#if isRunning}
								<span class="inline-block animate-spin">⟳</span>&nbsp;{$t('game.running')}
							{:else}
								▶&nbsp;{$t('game.execute')}
							{/if}
						</button>
					</div>
				</section>

				<!-- ══ RIGHT PANEL ════════════════════════════════════════════════ -->
				<section class="flex w-full min-w-0 flex-col lg:w-[680px] lg:shrink-0">
					<Arena bind:this={arena} {mission} initialTankState={INITIAL_TANK} {animationSpeed} />
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
				{$t('game.retry')}
			</button>
		</div>
	{:else}
		<div class="flex flex-1 items-center justify-center">
			<div class="animate-pulse text-2xl tracking-widest text-secondary-fixed">
				{$t('game.loading')}
			</div>
		</div>
	{/if}
</div>
