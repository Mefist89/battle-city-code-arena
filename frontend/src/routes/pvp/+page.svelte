<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/state';
	import { t } from '$lib/i18n';
	import { projectileDuration } from '$lib/game/combatEffects';
	import { GameAudio } from '$lib/game/audio';
	import PvPArena from './PvPArena.svelte';
	import Editor from '../game/components/Editor.svelte';

	type Tank = { x: number; y: number; direction: 'UP' | 'RIGHT' | 'DOWN' | 'LEFT'; hp: number };
	type Room = {
		code: string;
		players: Record<string, string>;
		tanks: Record<string, Tank>;
		walls: Array<{ x: number; y: number; type: 'brick' | 'steel' }>;
		winner: string | null;
		ready: string[];
		phase: 'prepare' | 'battle' | 'finished';
		seconds_left: number;
		map_id: number;
		private: boolean;
		ratings: Record<string, number>;
		online: string[];
		result_reason?: string | null;
		match_id?: string;
		result_confirmed?: boolean;
		reconnect_grace?: number;
	};
	type OpenRoom = { code: string; map_id: number; host: string; host_rating: number };
	type Leader = { user_id: string; name: string; rating: number; matches: number; wins: number };
	type Match = {
		match_id: string;
		opponent: string;
		result: 'win' | 'loss' | 'draw';
		rating_delta: number;
		rating_after: number;
		map_id: number;
		finished_at: string;
		server_confirmed: boolean;
	};
	type Shot = {
		slot: '1' | '2';
		direction: Tank['direction'];
		path: Array<{ x: number; y: number }>;
		collision?: boolean;
		hit?: '1' | '2';
		wall?: { x: number; y: number; type: 'brick' | 'steel'; destroyed: boolean };
	};
	const mapId = Math.min(3, Math.max(1, Number(page.url.searchParams.get('map')) || 1));
	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
	const WS = API.replace(/^http/, 'ws');
	const PVP_SETTINGS_KEY = 'codetank-pvp-settings';
	const pvpAudio = new GameAudio();
	let soundVolume = $state(0.7);
	let soundMuted = $state(false);
	let animationSpeed = $state(1);
	let name = $state('Player');
	let authenticated = $state(false);
	let joinCode = $state('');
	let privateRoom = $state(false);
	let openRooms = $state<OpenRoom[]>([]);
	let leaderboard = $state<Leader[]>([]);
	let history = $state<Match[]>([]);
	let rating = $state(1000);
	let lobbyLoading = $state(false);
	let room = $state<Room | null>(null);
	let slot = $state('');
	let error = $state('');
	let status = $state($t('pvp.initialStatus'));
	let shots = $state<Shot[]>([]);
	let code = $state(`# PvP strategy — repeats for 30 seconds
move()
move()
rotate()
fire()
rotate()
move()
fire()`);
	let socket: WebSocket | null = null;
	let editor: ReturnType<typeof Editor> | null = $state(null);
	let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	let shotTimer: ReturnType<typeof setTimeout> | null = null;
	let impactRoom: Room | null = null;
	let destroyed = false;

	onMount(async () => {
		try {
			const savedSettings = JSON.parse(localStorage.getItem(PVP_SETTINGS_KEY) ?? '{}');
			const savedVolume = Number(savedSettings.volume);
			soundVolume = Number.isFinite(savedVolume) ? Math.min(1, Math.max(0, savedVolume)) : 0.7;
			soundMuted = Boolean(savedSettings.muted);
			animationSpeed = [0.5, 1, 1.5, 2].includes(Number(savedSettings.animationSpeed))
				? Number(savedSettings.animationSpeed)
				: 1;
			pvpAudio.configure(soundVolume, soundMuted);
			const response = await fetch(`${API}/auth/me`, { credentials: 'include' });
			const data = response.ok ? await response.json() : null;
			if (!data?.authenticated) {
				window.location.replace(`/auth?next=${encodeURIComponent(`/pvp?map=${mapId}`)}`);
				return;
			}
			authenticated = true;
			name = data.user?.name || data.user?.email || 'Player';
			const profileResponse = await fetch(`${API}/auth/profile`, { credentials: 'include' });
			if (profileResponse.ok) {
				const profile = await profileResponse.json();
				const savedCode = profile.progress?.last_code?.pvp?.code;
				if (typeof savedCode === 'string') code = savedCode;
			}
			const currentResponse = await fetch(`${API}/api/rooms/current`, { credentials: 'include' });
			if (currentResponse.ok) {
				const current = await currentResponse.json();
				if (current.room) connect(current.room.code, current.room.slot);
				else await loadLobby();
			}
		} catch {
			window.location.replace(`/auth?next=${encodeURIComponent(`/pvp?map=${mapId}`)}`);
		}
	});

	function savePvpSettings() {
		pvpAudio.configure(soundVolume, soundMuted);
		localStorage.setItem(
			PVP_SETTINGS_KEY,
			JSON.stringify({ volume: soundVolume, muted: soundMuted, animationSpeed })
		);
	}

	function toggleSound() {
		soundMuted = !soundMuted;
		savePvpSettings();
	}

	function updatePvpVolume(event: Event) {
		soundVolume = Number((event.currentTarget as HTMLInputElement).value);
		savePvpSettings();
	}

	function updatePvpAnimationSpeed(event: Event) {
		animationSpeed = Number((event.currentTarget as HTMLSelectElement).value);
		savePvpSettings();
	}

	async function loadLobby() {
		if (!authenticated) return;
		lobbyLoading = true;
		try {
			const [roomsResponse, leadersResponse, historyResponse] = await Promise.all([
				fetch(`${API}/api/rooms`, { credentials: 'include' }),
				fetch(`${API}/api/pvp/leaderboard`, { credentials: 'include' }),
				fetch(`${API}/api/pvp/history`, { credentials: 'include' })
			]);
			if (roomsResponse.ok) openRooms = (await roomsResponse.json()).rooms ?? [];
			if (leadersResponse.ok) leaderboard = (await leadersResponse.json()).players ?? [];
			if (historyResponse.ok) {
				const data = await historyResponse.json();
				rating = data.rating ?? 1000;
				history = data.history ?? [];
			}
		} finally {
			lobbyLoading = false;
		}
	}

	async function request(path: string) {
		const response = await fetch(`${API}${path}`, {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				name: name.trim() || 'Player',
				map_id: mapId,
				private: privateRoom
			})
		});
		if (!response.ok) throw new Error((await response.json()).detail ?? $t('pvp.requestFailed'));
		return response.json();
	}
	async function createRoom() {
		if (!authenticated) return;
		try {
			error = '';
			const data = await request('/api/rooms');
			connect(data.code, data.slot);
		} catch (e) {
			error = e instanceof Error ? e.message : $t('pvp.createFailed');
		}
	}
	async function joinRoom() {
		if (!authenticated) return;
		try {
			error = '';
			const code = joinCode.trim().toUpperCase();
			const data = await request(`/api/rooms/${code}/join`);
			connect(data.code, data.slot);
		} catch (e) {
			error = e instanceof Error ? e.message : $t('pvp.joinFailed');
		}
	}
	async function joinOpenRoom(code: string) {
		joinCode = code;
		await joinRoom();
	}
	async function leaveRoom() {
		try {
			const response = await fetch(`${API}/api/rooms/current`, {
				method: 'DELETE',
				credentials: 'include'
			});
			if (!response.ok) throw new Error((await response.json()).detail ?? $t('pvp.requestFailed'));
			if (socket) {
				socket.onclose = null;
				socket.close();
				socket = null;
			}
			room = null;
			slot = '';
			await loadLobby();
		} catch (cause) {
			error = cause instanceof Error ? cause.message : $t('pvp.requestFailed');
		}
	}
	let reconnectAttempts = 0;
	function connect(code: string, playerSlot: string) {
		if (destroyed) return;
		slot = playerSlot;
		socket = new WebSocket(`${WS}/ws/rooms/${code}/${playerSlot}`);
		socket.onopen = () => {
			if (destroyed) {
				socket?.close();
				return;
			}
			reconnectAttempts = 0;
			status = playerSlot === '1' ? $t('pvp.roomCreated') : $t('pvp.connected');
		};
		socket.onmessage = (message) => {
			const data = JSON.parse(message.data);
			if (data.type === 'error') {
				status = `CODE ERROR: ${data.detail}`;
				return;
			}
			const incomingRoom = data.room as Room;
			const tickActions = (data.event?.actions ?? []) as Array<Shot & { kind?: string }>;
			const nextShots =
				tickActions.filter(
					(event: Shot & { kind?: string }) => event.kind === 'fire' && event.path?.length
				) ?? [];
			if (tickActions.some((event) => event.kind === 'move')) pvpAudio.play('move');
			nextShots.forEach(() => pvpAudio.play('fire'));
			if (nextShots.length) {
				const previousRoom = room;
				impactRoom = incomingRoom;
				room = previousRoom
					? {
							...incomingRoom,
							tanks: {
								'1': {
									...incomingRoom.tanks['1'],
									hp: previousRoom.tanks['1']?.hp ?? incomingRoom.tanks['1'].hp
								},
								'2': {
									...incomingRoom.tanks['2'],
									hp: previousRoom.tanks['2']?.hp ?? incomingRoom.tanks['2'].hp
								}
							},
							walls:
								incomingRoom.walls.length < previousRoom.walls.length
									? previousRoom.walls
									: incomingRoom.walls
						}
					: incomingRoom;
				shots = nextShots;
				if (shotTimer) clearTimeout(shotTimer);
				const impactDelay =
					Math.max(...nextShots.map((shot: Shot) => projectileDuration(shot.path.length))) /
					animationSpeed;
				shotTimer = setTimeout(() => {
					const destroyedTank = nextShots.some(
						(shot: Shot) => shot.hit && incomingRoom.tanks[shot.hit]?.hp <= 0
					);
					if (destroyedTank) pvpAudio.play('explosion');
					else if (nextShots.some((shot: Shot) => shot.hit || shot.wall || shot.collision))
						pvpAudio.play('impact');
					room = impactRoom ?? incomingRoom;
					impactRoom = null;
					shots = [];
					shotTimer = null;
				}, impactDelay);
			} else if (shotTimer && room) {
				impactRoom = incomingRoom;
				room = {
					...incomingRoom,
					tanks: {
						'1': { ...incomingRoom.tanks['1'], hp: room.tanks['1'].hp },
						'2': { ...incomingRoom.tanks['2'], hp: room.tanks['2'].hp }
					},
					walls: room.walls
				};
			} else room = incomingRoom;
			if (room?.phase === 'prepare' && room.players['2']) status = $t('pvp.writeCode');
			if (room?.phase === 'battle') status = $t('pvp.battleStatus', { seconds: room.seconds_left });
			if (data.event?.kind === 'left' && incomingRoom.phase === 'battle')
				status = $t('pvp.opponentReconnecting', { seconds: incomingRoom.reconnect_grace ?? 20 });
			if (data.event?.kind === 'ready_timeout') status = $t('pvp.readyExpired');
			if (room?.winner)
				status =
					room.winner === 'draw'
						? $t('pvp.draw')
						: room.winner === slot
							? $t('pvp.victory')
							: $t('pvp.defeat');
		};
		socket.onclose = (event) => {
			if (destroyed) return;
			const permanentClose = [4400, 4401, 4403, 4404, 4429].includes(event.code);
			if (!room?.winner && !permanentClose && reconnectAttempts < 10) {
				status = $t('pvp.reconnecting', { attempt: reconnectAttempts + 1 });
				reconnectAttempts++;
				reconnectTimer = setTimeout(
					() => {
						reconnectTimer = null;
						connect(code, playerSlot);
					},
					Math.min(8000, 1000 * 2 ** reconnectAttempts)
				);
			} else if (!room?.winner) {
				if (event.code === 4401) {
					window.location.replace(`/auth?next=${encodeURIComponent(`/pvp?map=${mapId}`)}`);
					return;
				}
				status = $t('pvp.connectionLost');
			}
		};
	}
	function ready() {
		if (socket?.readyState !== WebSocket.OPEN || !room?.players['2'] || room.ready.includes(slot))
			return;
		code = editor?.getCode() ?? code;
		const firstIssue = editor?.getErrors()[0];
		if (firstIssue) {
			status = `${$t('editor.line')} ${firstIssue.line}: ${firstIssue.message}`;
			return;
		}
		if (!code.trim()) {
			status = $t('pvp.emptyStrategy');
			return;
		}
		socket.send(JSON.stringify({ type: 'ready', code }));
		status = $t('pvp.readyWaiting');
	}
	onDestroy(() => {
		destroyed = true;
		if (reconnectTimer) clearTimeout(reconnectTimer);
		reconnectTimer = null;
		if (shotTimer) clearTimeout(shotTimer);
		shotTimer = null;
		impactRoom = null;
		pvpAudio.stop();
		if (socket) {
			socket.onclose = null;
			socket.close();
		}
	});
</script>

<svelte:head>
	<title>{$t('pvp.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-surface text-on-surface">
	<header
		class="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b-4 border-outline-variant bg-surface-container-low px-4 py-2 sm:px-6"
	>
		<a href="/" class="font-bold text-primary">{$t('common.backHome')}</a>
		<h1 class="text-xl font-bold uppercase">{$t('pvp.title')}</h1>
		<div class="text-sm text-secondary-fixed">
			{room
				? $t('pvp.roomLabel', { code: room.code, map: room.map_id })
				: $t('pvp.arenaLabel', { map: mapId })}
		</div>
		<div class="flex items-center gap-2">
			<div
				class="flex items-center gap-2 border-2 border-outline-variant bg-surface-container-lowest px-2 py-1 text-xs"
			>
				<button
					onclick={toggleSound}
					class="font-bold text-primary"
					aria-label={soundMuted ? $t('game.soundOn') : $t('game.soundOff')}
					title={soundMuted ? $t('game.soundOn') : $t('game.soundOff')}
				>
					{soundMuted ? '🔇' : '🔊'}
				</button>
				<label title={$t('game.volume')}>
					<span class="sr-only">{$t('game.volume')}</span>
					<input
						type="range"
						min="0"
						max="1"
						step="0.05"
						value={soundVolume}
						oninput={updatePvpVolume}
						class="w-16 accent-primary"
					/>
				</label>
			</div>
			<label
				class="flex items-center gap-1 border-2 border-outline-variant bg-surface-container-lowest px-2 py-1 text-xs"
			>
				<span class="text-on-surface-variant">{$t('game.animationSpeed')}</span>
				<select
					value={animationSpeed}
					onchange={updatePvpAnimationSpeed}
					class="bg-black px-1 font-bold text-primary outline-none"
				>
					<option value={0.5}>0.5×</option>
					<option value={1}>1×</option>
					<option value={1.5}>1.5×</option>
					<option value={2}>2×</option>
				</select>
			</label>
		</div>
		{#if room && room.phase !== 'battle'}
			<button onclick={leaveRoom} class="text-xs font-bold text-error uppercase"
				>{$t('pvp.leaveRoom')}</button
			>
		{/if}
	</header>

	{#if !room}
		<main class="mx-auto flex max-w-6xl flex-col items-center px-6 py-16">
			<h2 class="mb-3 text-4xl font-bold text-primary uppercase">{$t('pvp.room')}</h2>
			<p class="mb-10 text-on-surface-variant">{$t('pvp.intro')}</p>
			<a href="/pvp-maps" class="mb-7 text-sm font-bold text-tertiary uppercase hover:text-primary">
				{$t('pvp.changeMap', { map: mapId })}
			</a>
			<div class="grid w-full gap-6 md:grid-cols-2">
				<section class="pixel-shadow border-4 border-secondary-fixed bg-surface-container-low p-7">
					<h3 class="mb-5 text-xl font-bold uppercase">{$t('pvp.create')}</h3>
					<input
						bind:value={name}
						readonly
						maxlength="20"
						placeholder={$t('pvp.name')}
						class="mb-5 w-full border-2 border-outline bg-black p-3 outline-none focus:border-primary"
					/>
					<label
						class="mb-5 flex cursor-pointer items-center justify-between border-2 border-outline bg-black p-3 text-sm"
					>
						<span>
							<strong class="block text-primary uppercase">{$t('pvp.privateRoom')}</strong>
							<span class="text-xs text-on-surface-variant">{$t('pvp.privateHint')}</span>
						</span>
						<input bind:checked={privateRoom} type="checkbox" class="h-5 w-5 accent-primary" />
					</label>
					<button
						onclick={createRoom}
						disabled={!authenticated}
						class="pixel-btn w-full bg-secondary-fixed p-4 font-bold text-on-secondary uppercase disabled:opacity-40"
						>{$t('pvp.create')}</button
					>
				</section>
				<section class="pixel-shadow border-4 border-primary bg-surface-container-low p-7">
					<h3 class="mb-5 text-xl font-bold uppercase">{$t('pvp.join')}</h3>
					<input
						bind:value={joinCode}
						maxlength="6"
						placeholder="ABC123"
						class="mb-5 w-full border-2 border-outline bg-black p-3 text-center text-xl tracking-[0.3em] uppercase outline-none focus:border-primary"
					/>
					<button
						onclick={joinRoom}
						disabled={!authenticated}
						class="pixel-btn w-full bg-primary-container p-4 font-bold uppercase disabled:opacity-40"
						>{$t('pvp.connect')}</button
					>
				</section>
			</div>
			{#if error}<p class="mt-7 text-error">{error}</p>{/if}

			<section class="mt-10 grid w-full gap-6 lg:grid-cols-3">
				<div class="border-4 border-primary bg-surface-container-low p-5 lg:col-span-2">
					<div
						class="mb-4 flex items-center justify-between border-b-2 border-outline-variant pb-3"
					>
						<div>
							<p class="text-xs font-bold tracking-widest text-tertiary uppercase">
								{$t('pvp.matchmaking')}
							</p>
							<h3 class="text-xl font-bold uppercase">{$t('pvp.openRooms')}</h3>
						</div>
						<button onclick={loadLobby} class="text-xs font-bold text-primary uppercase"
							>↻ {$t('pvp.refresh')}</button
						>
					</div>
					{#if lobbyLoading}
						<p class="py-8 text-center text-on-surface-variant">{$t('pvp.loadingRooms')}</p>
					{:else if openRooms.length === 0}
						<p class="py-8 text-center text-on-surface-variant">{$t('pvp.noOpenRooms')}</p>
					{:else}
						<div class="grid gap-3 sm:grid-cols-2">
							{#each openRooms as openRoom}
								<button
									onclick={() => joinOpenRoom(openRoom.code)}
									class="flex items-center justify-between border-2 border-outline bg-black p-4 text-left hover:border-primary"
								>
									<span>
										<strong class="block text-secondary-fixed">{openRoom.host}</strong>
										<span class="text-xs text-on-surface-variant"
											>MAP {openRoom.map_id} · ELO {openRoom.host_rating}</span
										>
									</span>
									<span class="font-bold text-primary">{$t('pvp.join')}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>

				<div class="border-4 border-tertiary bg-surface-container-low p-5">
					<p class="text-xs font-bold tracking-widest text-tertiary uppercase">
						{$t('pvp.yourRating')}
					</p>
					<div class="mb-4 text-5xl font-black text-primary">{rating}</div>
					<h3 class="mb-3 border-b-2 border-outline-variant pb-2 font-bold uppercase">
						{$t('pvp.leaderboard')}
					</h3>
					<ol class="space-y-2 text-sm">
						{#each leaderboard.slice(0, 5) as player, index}
							<li class="flex justify-between">
								<span>{index + 1}. {player.name}</span><b>{player.rating}</b>
							</li>
						{/each}
					</ol>
				</div>
			</section>

			<section class="mt-6 w-full border-4 border-outline-variant bg-surface-container-low p-5">
				<h3 class="mb-4 text-xl font-bold uppercase">{$t('pvp.matchHistory')}</h3>
				{#if history.length === 0}
					<p class="text-on-surface-variant">{$t('pvp.noHistory')}</p>
				{:else}
					<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
						{#each history.slice(0, 9) as match}
							<article class="border-2 border-outline bg-black p-3 text-sm">
								<div class="flex items-center justify-between">
									<strong
										class:text-primary={match.result === 'win'}
										class:text-error={match.result === 'loss'}
										class:text-tertiary={match.result === 'draw'}
										>{match.result.toUpperCase()}</strong
									>
									<span class={match.rating_delta >= 0 ? 'text-primary' : 'text-error'}
										>{match.rating_delta >= 0 ? '+' : ''}{match.rating_delta}</span
									>
								</div>
								<p class="mt-1">VS {match.opponent} · MAP {match.map_id}</p>
								<p class="mt-1 text-[10px] text-on-surface-variant">
									✓ {$t('pvp.serverConfirmed')}
								</p>
							</article>
						{/each}
					</div>
				{/if}
			</section>
		</main>
	{:else}
		<main class="mx-auto flex max-w-5xl flex-col items-center gap-5 px-4 py-8">
			<section
				class="w-full max-w-[800px] border-4 border-outline-variant bg-surface-container-low"
			>
				<div class="flex items-center justify-between border-b-2 border-outline-variant px-4 py-3">
					<div>
						<span class="font-bold text-secondary-fixed">main.py</span><span
							class="ml-3 text-xs text-on-surface-variant"
							>move() · rotate('LEFT'|'RIGHT') · fire() · scan()</span
						>
					</div>
					<div class="text-xs text-tertiary">
						{$t('pvp.readyCount', { count: room.ready.length })}
					</div>
				</div>
				<div class="h-96 overflow-hidden">
					<Editor
						bind:this={editor}
						bind:code
						mode="pvp"
						readOnly={room.ready.includes(slot) || room.phase !== 'prepare'}
					/>
				</div>
				<div class="flex items-center justify-between border-t-2 border-outline-variant p-4">
					<span class="text-xs text-on-surface-variant">{$t('pvp.programRepeats')}</span>
					<button
						onclick={ready}
						disabled={!room.players['2'] || room.ready.includes(slot) || room.phase !== 'prepare'}
						class="pixel-btn bg-secondary-fixed px-7 py-3 font-bold text-on-secondary uppercase disabled:opacity-40"
						>{room.ready.includes(slot) ? `✓ ${$t('pvp.ready')}` : $t('pvp.ready')}</button
					>
				</div>
			</section>
			<div class="flex w-full max-w-[800px] items-center justify-between">
				<div>
					<span class="text-secondary-fixed">{room.players['1']}</span> · {room.ratings?.['1'] ??
						1000}
					· HP {room.tanks['1'].hp}
					<span class={room.online?.includes('1') ? 'text-primary' : 'text-error'}> ●</span>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold tracking-[0.25em] text-primary">{room.code}</div>
					<div class="text-xs text-on-surface-variant">{status}</div>
					{#if room.phase === 'finished' && room.result_confirmed}
						<div class="mt-1 text-[10px] font-bold text-primary uppercase">
							✓ {$t('pvp.serverConfirmed')}
						</div>
					{/if}
				</div>
				<div>
					<span class={room.online?.includes('2') ? 'text-primary' : 'text-error'}>● </span>
					HP {room.tanks['2'].hp} · {room.ratings?.['2'] ?? 1000}
					<span class="text-error">{room.players['2'] ?? $t('pvp.waiting')}</span>
				</div>
			</div>
			<PvPArena {room} {shots} {animationSpeed} />
			<p class="text-sm text-on-surface-variant">{$t('pvp.bothPlayers')}</p>
			{#if error}<p class="text-sm font-bold text-error">{error}</p>{/if}
		</main>
	{/if}
</div>
