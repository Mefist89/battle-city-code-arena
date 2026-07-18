<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { t } from '$lib/i18n';
	import Editor from '../game/components/Editor.svelte';

	type Direction = 'UP' | 'RIGHT' | 'DOWN' | 'LEFT';
	type Action = 'move' | 'rotate_left' | 'rotate_right' | 'scan' | 'fire';
	type Point = { x: number; y: number };
	type Tank = Point & { direction: Direction };
	type Enemy = Point & { alive: boolean };
	type Stats = {
		moves: number;
		rotates: number;
		scans: number;
		scanHits: number;
		loops: number;
		conditions: number;
		walls: number;
		enemies: number;
	};
	type Lesson = {
		id: number;
		icon: string;
		start: Tank;
		enemies: Point[];
		walls: Point[];
		goal?: Point;
		starter: string;
	};
	type Node =
		| { type: 'action'; action: Action }
		| { type: 'for'; count: number; body: Node[] }
		| { type: 'if'; body: Node[]; alternate: Node[] }
		| { type: 'while'; body: Node[] }
		| { type: 'pass' };

	const WIDTH = 8;
	const HEIGHT = 6;
	const ROTATE_LEFT: Record<Direction, Direction> = {
		UP: 'LEFT',
		LEFT: 'DOWN',
		DOWN: 'RIGHT',
		RIGHT: 'UP'
	};
	const ROTATE_RIGHT: Record<Direction, Direction> = {
		UP: 'RIGHT',
		RIGHT: 'DOWN',
		DOWN: 'LEFT',
		LEFT: 'UP'
	};
	const DELTA: Record<Direction, Point> = {
		UP: { x: 0, y: -1 },
		RIGHT: { x: 1, y: 0 },
		DOWN: { x: 0, y: 1 },
		LEFT: { x: -1, y: 0 }
	};
	const ROTATION: Record<Direction, number> = { UP: 0, RIGHT: 90, DOWN: 180, LEFT: -90 };
	const LESSONS: Lesson[] = [
		{
			id: 1,
			icon: '↟',
			start: { x: 1, y: 4, direction: 'UP' },
			enemies: [],
			walls: [],
			goal: { x: 2, y: 2 },
			starter: '# Move to the green target\nmove()'
		},
		{
			id: 2,
			icon: '◎',
			start: { x: 1, y: 3, direction: 'RIGHT' },
			enemies: [{ x: 6, y: 3 }],
			walls: [],
			starter: '# Detect the enemy in front of you\n'
		},
		{
			id: 3,
			icon: '?',
			start: { x: 1, y: 3, direction: 'RIGHT' },
			enemies: [{ x: 6, y: 3 }],
			walls: [],
			starter: 'if scan():\n    # Fire when the enemy is visible\n    pass'
		},
		{
			id: 4,
			icon: '∞',
			start: { x: 2, y: 5, direction: 'UP' },
			enemies: [],
			walls: [],
			goal: { x: 2, y: 1 },
			starter: 'for i in range(4):\n    pass'
		},
		{
			id: 5,
			icon: '▦',
			start: { x: 1, y: 3, direction: 'RIGHT' },
			enemies: [],
			walls: [{ x: 4, y: 3 }],
			starter: '# Destroy the brick wall\n'
		},
		{
			id: 6,
			icon: '⚔',
			start: { x: 1, y: 4, direction: 'RIGHT' },
			enemies: [
				{ x: 6, y: 4 },
				{ x: 1, y: 1 }
			],
			walls: [],
			starter: 'if scan():\n    fire()\n# Find and destroy the second enemy\n'
		}
	];

	let currentLesson = $state(0);
	let lesson = $derived(LESSONS[currentLesson]);
	let code = $state(LESSONS[0].starter);
	let cursorInfo = $state('Ln 1, Col 1');
	let editor: ReturnType<typeof Editor> | null = $state(null);
	let tank = $state<Tank>({ ...LESSONS[0].start });
	let enemies = $state<Enemy[]>([]);
	let walls = $state(new SvelteSet<string>());
	let bullet = $state<Point | null>(null);
	let scanPulse = $state(false);
	let running = $state(false);
	let result = $state<'idle' | 'success' | 'failed'>('idle');
	let message = $state('');
	let logs = $state<string[]>([]);
	let stats = $state<Stats>(emptyStats());
	let completed = $state(new SvelteSet<number>());
	let runToken = 0;

	function emptyStats(): Stats {
		return {
			moves: 0,
			rotates: 0,
			scans: 0,
			scanHits: 0,
			loops: 0,
			conditions: 0,
			walls: 0,
			enemies: 0
		};
	}

	function key(point: Point) {
		return `${point.x},${point.y}`;
	}

	function resetArena() {
		runToken++;
		running = false;
		result = 'idle';
		message = '';
		logs = [];
		stats = emptyStats();
		tank = { ...lesson.start };
		enemies = lesson.enemies.map((enemy) => ({ ...enemy, alive: true }));
		walls = new SvelteSet(lesson.walls.map(key));
		bullet = null;
		scanPulse = false;
	}

	function selectLesson(index: number) {
		currentLesson = index;
		code = LESSONS[index].starter;
		editor?.setCode(code);
		resetArena();
	}

	function indentation(line: string) {
		return line.length - line.trimStart().length;
	}

	function parseProgram(source: string): Node[] {
		const lines = source.replaceAll('\t', '    ').split('\n');
		function parseBlock(start: number, expectedIndent: number): [Node[], number] {
			const nodes: Node[] = [];
			let index = start;
			while (index < lines.length) {
				const raw = lines[index];
				const text = raw.trim();
				if (!text || text.startsWith('#')) {
					index++;
					continue;
				}
				const indent = indentation(raw);
				if (indent < expectedIndent || (indent === expectedIndent && text === 'else:')) break;
				if (indent > expectedIndent) throw new Error(`Unexpected indentation on line ${index + 1}`);

				const simple = text.match(/^(move|fire|scan)\s*\(\s*\)\s*$/);
				if (simple) {
					nodes.push({ type: 'action', action: simple[1] as Action });
					index++;
					continue;
				}
				const rotate = text.match(/^rotate\s*\(\s*(?:['"](LEFT|RIGHT)['"])?\s*\)\s*$/i);
				if (rotate) {
					nodes.push({
						type: 'action',
						action: rotate[1]?.toUpperCase() === 'LEFT' ? 'rotate_left' : 'rotate_right'
					});
					index++;
					continue;
				}
				const loop = text.match(/^for\s+\w+\s+in\s+range\s*\(\s*(\d+)\s*\)\s*:\s*$/);
				if (loop) {
					const [body, next] = parseBlock(index + 1, expectedIndent + 4);
					nodes.push({ type: 'for', count: Math.min(Number(loop[1]), 20), body });
					index = next;
					continue;
				}
				if (/^if\s+scan\s*\(\s*\)\s*:\s*$/.test(text)) {
					const [body, afterBody] = parseBlock(index + 1, expectedIndent + 4);
					let alternate: Node[] = [];
					index = afterBody;
					if (lines[index]?.trim() === 'else:' && indentation(lines[index]) === expectedIndent) {
						[alternate, index] = parseBlock(index + 1, expectedIndent + 4);
					}
					nodes.push({ type: 'if', body, alternate });
					continue;
				}
				if (/^while\s+scan\s*\(\s*\)\s*:\s*$/.test(text)) {
					const [body, next] = parseBlock(index + 1, expectedIndent + 4);
					nodes.push({ type: 'while', body });
					index = next;
					continue;
				}
				if (text === 'pass') {
					nodes.push({ type: 'pass' });
					index++;
					continue;
				}
				throw new Error(`Unsupported command on line ${index + 1}`);
			}
			return [nodes, index];
		}
		return parseBlock(0, 0)[0];
	}

	function inBounds(point: Point) {
		return point.x >= 0 && point.x < WIDTH && point.y >= 0 && point.y < HEIGHT;
	}

	function visibleEnemy() {
		const delta = DELTA[tank.direction];
		let point = { x: tank.x + delta.x, y: tank.y + delta.y };
		while (inBounds(point)) {
			if (walls.has(key(point))) return false;
			if (enemies.some((enemy) => enemy.alive && enemy.x === point.x && enemy.y === point.y))
				return true;
			point = { x: point.x + delta.x, y: point.y + delta.y };
		}
		return false;
	}

	async function wait(ms: number, token: number) {
		await new Promise((resolve) => setTimeout(resolve, ms));
		if (token !== runToken) throw new Error('cancelled');
	}

	async function runAction(action: Action, token: number): Promise<boolean> {
		if (action === 'rotate_left' || action === 'rotate_right') {
			tank.direction =
				action === 'rotate_left' ? ROTATE_LEFT[tank.direction] : ROTATE_RIGHT[tank.direction];
			stats.rotates++;
			logs = [...logs, action === 'rotate_left' ? "rotate('LEFT')" : "rotate('RIGHT')"];
			await wait(180, token);
			return false;
		}
		if (action === 'move') {
			const delta = DELTA[tank.direction];
			const next = { x: tank.x + delta.x, y: tank.y + delta.y };
			const blocked =
				walls.has(key(next)) ||
				enemies.some((enemy) => enemy.alive && enemy.x === next.x && enemy.y === next.y);
			if (inBounds(next) && !blocked) {
				tank.x = next.x;
				tank.y = next.y;
				stats.moves++;
				logs = [...logs, `move() → (${tank.x}, ${tank.y})`];
			} else logs = [...logs, 'move() → BLOCKED'];
			await wait(220, token);
			return false;
		}
		if (action === 'scan') {
			const found = visibleEnemy();
			stats.scans++;
			if (found) stats.scanHits++;
			scanPulse = true;
			logs = [...logs, `scan() → ${found ? 'ENEMY' : 'CLEAR'}`];
			await wait(220, token);
			scanPulse = false;
			return found;
		}

		const delta = DELTA[tank.direction];
		let point = { x: tank.x + delta.x, y: tank.y + delta.y };
		logs = [...logs, 'fire()'];
		while (inBounds(point)) {
			bullet = { ...point };
			await wait(85, token);
			if (walls.has(key(point))) {
				walls.delete(key(point));
				stats.walls++;
				break;
			}
			const enemy = enemies.find((item) => item.alive && item.x === point.x && item.y === point.y);
			if (enemy) {
				enemy.alive = false;
				stats.enemies++;
				break;
			}
			point = { x: point.x + delta.x, y: point.y + delta.y };
		}
		bullet = null;
		return false;
	}

	async function execute(nodes: Node[], token: number) {
		for (const node of nodes) {
			if (node.type === 'action') await runAction(node.action, token);
			else if (node.type === 'for') {
				stats.loops++;
				for (let count = 0; count < node.count; count++) await execute(node.body, token);
			} else if (node.type === 'if') {
				stats.conditions++;
				const found = await runAction('scan', token);
				await execute(found ? node.body : node.alternate, token);
			} else if (node.type === 'while') {
				stats.loops++;
				for (let count = 0; count < 8; count++) {
					if (!(await runAction('scan', token))) break;
					await execute(node.body, token);
				}
			}
		}
	}

	function lessonPassed() {
		if (lesson.id === 1 || lesson.id === 4)
			return tank.x === lesson.goal?.x && tank.y === lesson.goal?.y;
		if (lesson.id === 2) return stats.scans > 0 && stats.scanHits > 0;
		if (lesson.id === 3) return stats.conditions > 0 && stats.enemies > 0;
		if (lesson.id === 5) return stats.walls > 0;
		return stats.enemies >= 2;
	}

	async function runTutorial() {
		if (running || !editor) return;
		const firstIssue = editor.getErrors()[0];
		if (firstIssue) {
			result = 'failed';
			message = `${$t('editor.line')} ${firstIssue.line}: ${firstIssue.message}`;
			return;
		}
		resetArena();
		const token = ++runToken;
		running = true;
		try {
			await execute(parseProgram(editor.getCode()), token);
			if (lessonPassed()) {
				completed.add(lesson.id);
				localStorage.setItem('codetank-tutorial-progress', JSON.stringify([...completed]));
				result = 'success';
				message = $t('tutorial.success');
			} else {
				result = 'failed';
				message = $t(`tutorial.lessons.${lesson.id}.retry`);
			}
		} catch (error) {
			if (error instanceof Error && error.message !== 'cancelled') {
				result = 'failed';
				message = error.message;
			}
		} finally {
			if (token === runToken) running = false;
		}
	}

	function nextLesson() {
		if (currentLesson < LESSONS.length - 1) selectLesson(currentLesson + 1);
	}

	onMount(() => {
		try {
			const saved = JSON.parse(localStorage.getItem('codetank-tutorial-progress') ?? '[]');
			if (Array.isArray(saved)) completed = new SvelteSet(saved);
		} catch {
			completed = new SvelteSet();
		}
		resetArena();
	});

	onDestroy(() => runToken++);
</script>

<svelte:head>
	<title>{$t('tutorial.pageTitle')}</title>
	<meta name="description" content={$t('tutorial.intro')} />
</svelte:head>

<div class="tutorial-shell min-h-screen bg-surface font-mono text-on-surface">
	<header class="border-b-4 border-outline-variant bg-surface-container-low">
		<div class="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-4 py-4 md:px-7">
			<a href="/" class="font-black text-primary uppercase">← CODETANK ARENA</a>
			<div class="text-center">
				<p class="text-[9px] font-bold tracking-[0.28em] text-tertiary uppercase">
					{$t('tutorial.eyebrow')}
				</p>
				<h1 class="text-lg font-black uppercase md:text-2xl">{$t('tutorial.title')}</h1>
			</div>
			<a
				href="/missions"
				class="border-2 border-secondary-fixed px-3 py-2 text-[10px] font-black text-secondary-fixed uppercase hover:bg-secondary-fixed hover:text-black"
				>{$t('tutorial.toMissions')}</a
			>
		</div>
		<div class="mx-auto flex max-w-[1440px] gap-1 px-4 pb-3 md:px-7">
			{#each LESSONS as item}
				<div
					class="h-1 flex-1 bg-outline-variant"
					class:bg-secondary-fixed={completed.has(item.id)}
					class:bg-primary={item.id === lesson.id && !completed.has(item.id)}
				></div>
			{/each}
		</div>
	</header>

	<main
		class="mx-auto grid max-w-[1440px] gap-5 px-4 py-6 lg:grid-cols-[240px_minmax(0,1fr)] lg:px-7"
	>
		<aside class="border-2 border-outline-variant bg-surface-container-low shadow-[6px_6px_0_#000]">
			<div
				class="border-b-2 border-outline-variant px-4 py-3 text-[10px] font-black tracking-widest text-tertiary uppercase"
			>
				{$t('tutorial.courseMap')}
			</div>
			<div class="grid sm:grid-cols-2 lg:grid-cols-1">
				{#each LESSONS as item, index}
					<button
						type="button"
						onclick={() => selectLesson(index)}
						class="lesson-button grid grid-cols-[36px_1fr_auto] items-center gap-3 border-b border-outline-variant px-4 py-4 text-left"
						class:active={index === currentLesson}
					>
						<span class="text-xl text-primary">{item.icon}</span>
						<span
							><b class="block text-xs uppercase">{$t(`tutorial.lessons.${item.id}.title`)}</b
							><small class="text-[9px] text-on-surface-variant"
								>{$t(`tutorial.lessons.${item.id}.skill`)}</small
							></span
						>
						<span class:text-secondary-fixed={completed.has(item.id)}
							>{completed.has(item.id) ? '✓' : String(item.id).padStart(2, '0')}</span
						>
					</button>
				{/each}
			</div>
		</aside>

		<div class="min-w-0 space-y-5">
			<section class="grid gap-5 xl:grid-cols-[minmax(420px,1.15fr)_minmax(280px,0.85fr)]">
				<div
					class="arena-frame border-4 border-outline-variant bg-black p-2 shadow-[8px_8px_0_#000]"
				>
					<div
						class="mb-2 flex items-center justify-between border-b border-outline-variant px-2 pb-2 text-[9px] uppercase"
					>
						<span class="text-secondary-fixed">● {$t('tutorial.liveArena')}</span><span
							class="text-on-surface-variant"
							>8×6 // LESSON {String(lesson.id).padStart(2, '0')}</span
						>
					</div>
					<div
						class="arena-grid relative aspect-[8/6] overflow-hidden border-2 border-outline-variant"
					>
						{#if lesson.goal}<div
								class="goal-cell"
								style={`--x:${lesson.goal.x};--y:${lesson.goal.y}`}
							>
								B
							</div>{/if}
						{#each [...walls] as wall}<img
								class="entity wall"
								style={`--x:${wall.split(',')[0]};--y:${wall.split(',')[1]}`}
								src="/assets/kenney/wall-brick.png"
								alt=""
							/>{/each}
						{#each enemies as enemy}{#if enemy.alive}<img
									class="entity tank"
									style={`--x:${enemy.x};--y:${enemy.y};--rotation:-90deg`}
									src="/assets/kenney-remastered/tank_red.png"
									alt=""
								/>{/if}{/each}
						<div
							class="entity scan-ring"
							class:visible={scanPulse}
							style={`--x:${tank.x};--y:${tank.y}`}
						></div>
						<img
							class="entity tank player"
							style={`--x:${tank.x};--y:${tank.y};--rotation:${ROTATION[tank.direction]}deg`}
							src="/assets/kenney-remastered/tank_blue.png"
							alt={$t('tutorial.playerTank')}
						/>
						{#if bullet}<span class="entity bullet" style={`--x:${bullet.x};--y:${bullet.y}`}
							></span>{/if}
					</div>
				</div>

				<article
					class="flex flex-col border-2 border-outline-variant bg-surface-container-low p-5 shadow-[6px_6px_0_#000]"
				>
					<p class="mb-2 text-[9px] font-bold tracking-[0.25em] text-tertiary uppercase">
						LESSON {String(lesson.id).padStart(2, '0')} / 06
					</p>
					<h2 class="mb-3 text-2xl font-black text-primary uppercase">
						{$t(`tutorial.lessons.${lesson.id}.title`)}
					</h2>
					<p class="mb-5 text-sm leading-6 text-on-surface-variant">
						{$t(`tutorial.lessons.${lesson.id}.brief`)}
					</p>
					<div class="mb-5 border-l-4 border-tertiary bg-black/30 p-3 text-xs leading-5">
						<b class="text-tertiary">{$t('tutorial.hint')}:</b>
						{$t(`tutorial.lessons.${lesson.id}.hint`)}
					</div>
					<div class="mb-4 grid grid-cols-4 gap-2 text-center text-[9px] uppercase">
						<div class="stat"><b>{stats.moves}</b>{$t('tutorial.moves')}</div>
						<div class="stat"><b>{stats.scans}</b>SCAN</div>
						<div class="stat"><b>{stats.walls}</b>{$t('tutorial.walls')}</div>
						<div class="stat"><b>{stats.enemies}</b>KO</div>
					</div>
					<div
						class="min-h-20 flex-1 overflow-auto border border-outline-variant bg-black p-3 text-[10px] text-on-surface-variant"
					>
						{#if logs.length}{#each logs.slice(-5) as log}<div>&gt; {log}</div>{/each}{:else}<div>
								&gt; {$t('tutorial.awaiting')}
							</div>{/if}
					</div>
					{#if message}<div
							class="mt-4 border-2 p-3 text-xs font-bold"
							class:border-secondary-fixed={result === 'success'}
							class:text-secondary-fixed={result === 'success'}
							class:border-error={result === 'failed'}
							class:text-error={result === 'failed'}
						>
							{message}
						</div>{/if}
				</article>
			</section>

			<section
				class="overflow-hidden border-4 border-outline-variant bg-surface-container-low shadow-[8px_8px_0_#000]"
			>
				<div
					class="flex flex-wrap items-center justify-between gap-3 border-b-2 border-outline-variant px-4 py-3"
				>
					<div>
						<span class="font-black text-secondary-fixed"
							>training_{String(lesson.id).padStart(2, '0')}.py</span
						><span class="ml-3 text-[10px] text-on-surface-variant">{cursorInfo}</span>
					</div>
					<div class="flex gap-2">
						<button type="button" onclick={resetArena} disabled={running} class="control-btn"
							>↻ {$t('tutorial.reset')}</button
						><button type="button" onclick={runTutorial} disabled={running} class="run-btn"
							>{running ? $t('tutorial.running') : `▶ ${$t('tutorial.run')}`}</button
						>
					</div>
				</div>
				<div class="h-[420px]">
					<Editor bind:this={editor} bind:code bind:cursorInfo mode="tutorial" readOnly={running} />
				</div>
				{#if result === 'success' && currentLesson < LESSONS.length - 1}<div
						class="flex justify-end border-t-2 border-outline-variant p-3"
					>
						<button type="button" onclick={nextLesson} class="run-btn"
							>{$t('tutorial.next')} →</button
						>
					</div>{/if}
			</section>
		</div>
	</main>

	<footer
		class="mt-10 border-t-4 border-outline-variant bg-surface-container-low px-5 py-8 text-center text-[10px] font-bold text-tertiary uppercase"
	>
		{$t('common.copyright')}
	</footer>
</div>

<style>
	.tutorial-shell {
		background-image:
			linear-gradient(#202331 1px, transparent 1px),
			linear-gradient(90deg, #202331 1px, transparent 1px);
		background-size: 40px 40px;
	}
	.lesson-button:hover,
	.lesson-button.active {
		background: #242638;
		color: #b9c3ff;
	}
	.lesson-button.active {
		box-shadow: inset 4px 0 #72ff70;
	}
	.arena-grid {
		background-color: #0c0e15;
		background-image:
			linear-gradient(#292d3d 1px, transparent 1px),
			linear-gradient(90deg, #292d3d 1px, transparent 1px);
		background-size: 12.5% 16.6667%;
	}
	.entity,
	.goal-cell {
		position: absolute;
		left: calc(var(--x) * 12.5%);
		top: calc(var(--y) * 16.6667%);
		width: 12.5%;
		height: 16.6667%;
	}
	.entity {
		object-fit: contain;
		padding: 1.5%;
		transition:
			left 180ms linear,
			top 180ms linear,
			transform 150ms ease;
	}
	.tank {
		transform: rotate(var(--rotation));
		z-index: 4;
	}
	.wall {
		padding: 0.5%;
		z-index: 2;
	}
	.goal-cell {
		display: grid;
		place-items: center;
		margin: 0.6%;
		width: calc(12.5% - 1.2%);
		height: calc(16.6667% - 1.2%);
		border: 3px solid #72ff70;
		color: #72ff70;
		font-weight: 900;
		font-size: clamp(12px, 2vw, 26px);
	}
	.scan-ring {
		z-index: 3;
		border: 3px solid #b9c3ff;
		border-radius: 50%;
		opacity: 0;
		transform: scale(0.5);
	}
	.scan-ring.visible {
		animation: scan 420ms ease-out;
	}
	.bullet {
		z-index: 6;
		width: 2.1%;
		height: 2.8%;
		margin: 5.2% 0 0 5.2%;
		padding: 0;
		border-radius: 50%;
		background: #72ff70;
		box-shadow: 0 0 12px #72ff70;
		transition:
			left 75ms linear,
			top 75ms linear;
	}
	.stat {
		border: 1px solid #434656;
		padding: 8px 4px;
		color: #8e90a2;
	}
	.stat b {
		display: block;
		color: #b9c3ff;
		font-size: 16px;
	}
	.control-btn,
	.run-btn {
		border: 2px solid #434656;
		padding: 8px 14px;
		font-size: 10px;
		font-weight: 900;
		text-transform: uppercase;
	}
	.control-btn:hover:not(:disabled) {
		border-color: #ffb778;
		color: #ffb778;
	}
	.run-btn {
		border-color: #72ff70;
		background: #72ff70;
		color: #061006;
		box-shadow: 4px 4px #000;
	}
	.control-btn:disabled,
	.run-btn:disabled {
		opacity: 0.4;
	}
	@keyframes scan {
		0% {
			opacity: 1;
			transform: scale(0.4);
		}
		100% {
			opacity: 0;
			transform: scale(4);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.entity {
			transition: none;
		}
		.scan-ring.visible {
			animation: none;
			opacity: 0.8;
		}
	}
</style>
