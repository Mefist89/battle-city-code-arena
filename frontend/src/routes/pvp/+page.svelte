<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { basicSetup } from 'codemirror';
	import { EditorView } from '@codemirror/view';
	import { EditorState, Compartment } from '@codemirror/state';
	import { python } from '@codemirror/lang-python';
	import { oneDark } from '@codemirror/theme-one-dark';
	import PvPArena from './PvPArena.svelte';

	type Tank = { x: number; y: number; direction: 'UP' | 'RIGHT' | 'DOWN' | 'LEFT'; hp: number };
	type Room = {
		code: string;
		players: Record<string, string>;
		tanks: Record<string, Tank>;
		walls: Array<{ x: number; y: number }>;
		winner: string | null;
		ready: string[];
		phase: 'prepare' | 'battle' | 'finished';
		seconds_left: number;
		map_id: number;
	};
	const mapId = Math.min(3, Math.max(1, Number(page.url.searchParams.get('map')) || 1));
	const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
	const WS = API.replace(/^http/, 'ws');
	let name = $state('Player');
	let joinCode = $state('');
	let room = $state<Room | null>(null);
	let slot = $state('');
	let error = $state('');
	let status = $state('Создай комнату или введи код приглашения.');
	let shotPath = $state<Array<{ x: number; y: number }>>([]);
	let code = $state(`# PvP strategy — repeats for 30 seconds
move()
move()
rotate()
fire()
rotate()
move()
fire()`);
	let socket: WebSocket | null = null;
	let editor: EditorView | null = null;
	const editable = new Compartment();

	async function request(path: string) {
		const response = await fetch(`${API}${path}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name: name.trim() || 'Player', map_id: mapId })
		});
		if (!response.ok) throw new Error((await response.json()).detail ?? 'Request failed');
		return response.json();
	}
	async function createRoom() {
		try {
			error = '';
			const data = await request('/api/rooms');
			connect(data.code, data.slot);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Не удалось создать комнату';
		}
	}
	async function joinRoom() {
		try {
			error = '';
			const code = joinCode.trim().toUpperCase();
			const data = await request(`/api/rooms/${code}/join`);
			connect(data.code, data.slot);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Не удалось войти';
		}
	}
	let reconnectAttempts = 0;
	function connect(code: string, playerSlot: string) {
		slot = playerSlot;
		socket = new WebSocket(`${WS}/ws/rooms/${code}/${playerSlot}`);
		socket.onopen = () => {
			reconnectAttempts = 0;
			status =
				playerSlot === '1'
					? 'Комната создана. Отправь код второму игроку.'
					: 'Подключено. Бой начинается!';
		};
		socket.onmessage = (message) => {
			const data = JSON.parse(message.data);
			room = data.room;
			const paths =
				data.event?.actions?.flatMap(
					(event: { path?: Array<{ x: number; y: number }> }) => event.path ?? []
				) ?? [];
			if (paths.length) {
				shotPath = paths;
				setTimeout(() => (shotPath = []), 180);
			}
			if (room?.phase === 'prepare' && room.players['2']) status = 'Напиши код и нажми «Готово».';
			if (room?.phase === 'battle') status = `Бой идёт — ${room.seconds_left} сек.`;
			if (room?.winner)
				status = room.winner === 'draw' ? 'НИЧЬЯ' : room.winner === slot ? 'ПОБЕДА!' : 'ПОРАЖЕНИЕ';
		};
		socket.onclose = () => {
			if (!room?.winner && reconnectAttempts < 5) {
				status = `Переподключение... (Попытка ${reconnectAttempts + 1}/5)`;
				reconnectAttempts++;
				setTimeout(() => connect(code, playerSlot), 3000);
			} else if (!room?.winner) {
				status = 'Соединение потеряно навсегда.';
			}
		};
	}
	function parseCode() {
		return code
			.split('\n')
			.map((line) => line.trim())
			.map((line) => {
				if (/^rotate\s*\(\s*['"]LEFT['"]\s*\)$/i.test(line)) return 'left';
				if (/^rotate\s*\(\s*(['"]RIGHT['"])?\s*\)$/i.test(line)) return 'right';
				if (/^(move|fire|scan)\s*\(\s*\)$/.test(line)) return line.slice(0, line.indexOf('('));
				return '';
			})
			.filter(Boolean)
			.slice(0, 40);
	}
	function ready() {
		if (socket?.readyState !== WebSocket.OPEN || !room?.players['2'] || room.ready.includes(slot))
			return;
		socket.send(JSON.stringify({ type: 'ready', actions: parseCode() }));
		editor?.dispatch({ effects: editable.reconfigure(EditorView.editable.of(false)) });
		status = 'Готово. Ожидание программы соперника...';
	}
	function mountEditor(node: HTMLDivElement) {
		editor = new EditorView({
			parent: node,
			state: EditorState.create({
				doc: code,
				extensions: [
					basicSetup,
					python(),
					oneDark,
					EditorView.lineWrapping,
					EditorView.theme(
						{
							'&': { height: '100%', fontSize: '13px' },
							'.cm-scroller': { fontFamily: "'Space Mono', monospace" }
						},
						{ dark: true }
					),
					EditorView.updateListener.of((update) => {
						if (update.docChanged) code = update.state.doc.toString();
					}),
					editable.of(EditorView.editable.of(true))
				]
			})
		});
		return {
			destroy() {
				editor?.destroy();
				editor = null;
			}
		};
	}
	onDestroy(() => {
		socket?.close();
		editor?.destroy();
	});
</script>

<svelte:head>
	<title>PvP Multiplayer — Battle City: Code Arena</title>
</svelte:head>

<div class="min-h-screen bg-surface text-on-surface">
	<header
		class="flex h-16 items-center justify-between border-b-4 border-outline-variant bg-surface-container-low px-6"
	>
		<a href="/" class="font-bold text-primary">← CODECOMMAND</a>
		<h1 class="text-xl font-bold uppercase">Player <span class="text-error">VS</span> Player</h1>
		<div class="text-sm text-secondary-fixed">
			{room ? `ROOM ${room.code} · MAP 0${room.map_id}` : `ONLINE ARENA · MAP 0${mapId}`}
		</div>
	</header>

	{#if !room}
		<main class="mx-auto flex max-w-4xl flex-col items-center px-6 py-16">
			<h2 class="mb-3 text-4xl font-bold text-primary uppercase">PvP Room</h2>
			<p class="mb-10 text-on-surface-variant">
				Создай приватную комнату и отправь шестизначный код другому игроку.
			</p>
			<a href="/pvp-maps" class="mb-7 text-sm font-bold text-tertiary uppercase hover:text-primary">
				Карта 0{mapId} · изменить карту
			</a>
			<div class="grid w-full gap-6 md:grid-cols-2">
				<section class="pixel-shadow border-4 border-secondary-fixed bg-surface-container-low p-7">
					<h3 class="mb-5 text-xl font-bold uppercase">Создать комнату</h3>
					<input
						bind:value={name}
						maxlength="20"
						placeholder="Твоё имя"
						class="mb-5 w-full border-2 border-outline bg-black p-3 outline-none focus:border-primary"
					/>
					<button
						onclick={createRoom}
						class="pixel-btn w-full bg-secondary-fixed p-4 font-bold text-on-secondary uppercase"
						>Создать</button
					>
				</section>
				<section class="pixel-shadow border-4 border-primary bg-surface-container-low p-7">
					<h3 class="mb-5 text-xl font-bold uppercase">Войти по коду</h3>
					<input
						bind:value={joinCode}
						maxlength="6"
						placeholder="ABC123"
						class="mb-5 w-full border-2 border-outline bg-black p-3 text-center text-xl tracking-[0.3em] uppercase outline-none focus:border-primary"
					/>
					<button
						onclick={joinRoom}
						class="pixel-btn w-full bg-primary-container p-4 font-bold uppercase"
						>Подключиться</button
					>
				</section>
			</div>
			{#if error}<p class="mt-7 text-error">{error}</p>{/if}
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
					<div class="text-xs text-tertiary">{room.ready.length}/2 READY</div>
				</div>
				<div use:mountEditor class="h-72 overflow-hidden"></div>
				<div class="flex items-center justify-between border-t-2 border-outline-variant p-4">
					<span class="text-xs text-on-surface-variant"
						>Код повторяется циклически во время 30-секундного боя.</span
					>
					<button
						onclick={ready}
						disabled={!room.players['2'] || room.ready.includes(slot) || room.phase !== 'prepare'}
						class="pixel-btn bg-secondary-fixed px-7 py-3 font-bold text-on-secondary uppercase disabled:opacity-40"
						>{room.ready.includes(slot) ? '✓ Готово' : 'Готово'}</button
					>
				</div>
			</section>
			<div class="flex w-full max-w-[800px] items-center justify-between">
				<div>
					<span class="text-secondary-fixed">{room.players['1']}</span> HP {room.tanks['1'].hp}
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold tracking-[0.25em] text-primary">{room.code}</div>
					<div class="text-xs text-on-surface-variant">{status}</div>
				</div>
				<div>
					HP {room.tanks['2'].hp}
					<span class="text-error">{room.players['2'] ?? 'WAITING...'}</span>
				</div>
			</div>
			<PvPArena {room} {shotPath} />
			<p class="text-sm text-on-surface-variant">
				Оба игрока пишут код. Бой начинается автоматически после готовности двух программ.
			</p>
		</main>
	{/if}
</div>
