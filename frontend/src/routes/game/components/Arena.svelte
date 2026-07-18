<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { Application, Assets, Sprite, Texture, Graphics, Text, TextStyle } from 'pixi.js';
	import { CombatEffects, type ImpactKind } from '$lib/game/combatEffects';
	import type { Direction, EnemyState, WallState, TankState } from '../types';
	type MissionData = {
		goal: { x: number; y: number };
		walls: WallState[];
		enemy: { x: number; y: number; skin?: string };
		enemies?: Array<{ x: number; y: number; skin?: string }>;
	};

	let {
		mission,
		initialTankState,
		animationSpeed = 1
	}: {
		mission: MissionData;
		initialTankState: TankState;
		animationSpeed?: number;
	} = $props();

	let gameDiv: HTMLDivElement | null = $state(null);
	let pixiApp: Application | null = null;

	const SPRITE_URL = '/assets/kenney-remastered/tank_blue.png';
	const TILE = 64;
	const MAP_W = 10;
	const MAP_H = 8;

	let tankSprite: Sprite | null = null;
	let enemySprite: Sprite | null = null;
	let enemySprites: Sprite[] = [];
	const wallSprites = new SvelteMap<string, Sprite>();
	let brickTexture: Texture | null = null;
	let steelTexture: Texture | null = null;
	let combatEffects: CombatEffects | null = null;
	let disposed = false;
	type ActiveMotion = { frame: number | null; finish: () => void };
	const activeMotions = new SvelteSet<ActiveMotion>();

	function cancelMotions() {
		for (const motion of [...activeMotions]) motion.finish();
		activeMotions.clear();
	}

	onMount(async () => {
		if (gameDiv) {
			const app = new Application();
			await app.init({
				width: MAP_W * TILE,
				height: MAP_H * TILE,
				backgroundColor: 0x0a1118,
				antialias: false
			});
			if (disposed) {
				app.destroy(true, { children: true });
				return;
			}
			pixiApp = app;
			gameDiv.appendChild(app.canvas);

			const cells = new Graphics();
			for (let row = 0; row < MAP_H; row++) {
				for (let col = 0; col < MAP_W; col++) {
					const even = (row + col) % 2 === 0;
					cells.rect(col * TILE, row * TILE, TILE, TILE);
					cells.fill({ color: even ? 0x111318 : 0x0e1014 });
				}
			}
			app.stage.addChild(cells);

			const grid = new Graphics();
			grid.setStrokeStyle({ width: 1, color: 0x2a2a3a, alpha: 1 });
			for (let col = 0; col <= MAP_W; col++) {
				grid.moveTo(col * TILE, 0);
				grid.lineTo(col * TILE, MAP_H * TILE);
			}
			for (let row = 0; row <= MAP_H; row++) {
				grid.moveTo(0, row * TILE);
				grid.lineTo(MAP_W * TILE, row * TILE);
			}
			grid.stroke();
			app.stage.addChild(grid);

			const goal = new Graphics();
			goal.rect(mission.goal.x * TILE + 5, mission.goal.y * TILE + 5, TILE - 10, TILE - 10);
			goal.fill({ color: 0x13ff43, alpha: 0.18 });
			goal.setStrokeStyle({ width: 3, color: 0x72ff70 });
			goal.stroke();
			app.stage.addChild(goal);

			const goalLabel = new Text({
				text: 'B',
				style: new TextStyle({
					fontFamily: "'Space Mono', monospace",
					fontSize: 22,
					fontWeight: 'bold',
					fill: 0x72ff70
				})
			});
			goalLabel.anchor.set(0.5);
			goalLabel.x = mission.goal.x * TILE + TILE / 2;
			goalLabel.y = mission.goal.y * TILE + TILE / 2;
			app.stage.addChild(goalLabel);

			const [loadedBrickTexture, loadedSteelTexture] = await Promise.all([
				Assets.load('/assets/kenney/wall-brick.png'),
				Assets.load('/assets/kenney/wall-steel.png')
			]);
			if (disposed) return;
			brickTexture = loadedBrickTexture;
			steelTexture = loadedSteelTexture;

			for (const wall of mission.walls) {
				const wallSprite = new Sprite(
					wall.type === 'brick' ? loadedBrickTexture : loadedSteelTexture
				);
				wallSprite.anchor.set(0.5);
				wallSprite.width = TILE - 6;
				wallSprite.height = TILE - 6;
				setSpritePos(wallSprite, wall.x, wall.y);
				app.stage.addChild(wallSprite);
				wallSprites.set(`${wall.x},${wall.y}`, wallSprite);
			}

			const labelStyle = new TextStyle({
				fontFamily: "'Space Mono', monospace",
				fontSize: 9,
				fill: 0x434656
			});
			for (let col = 0; col < MAP_W; col++) {
				const t = new Text({ text: String(col), style: labelStyle });
				t.x = col * TILE + 3;
				t.y = 2;
				app.stage.addChild(t);
			}
			for (let row = 0; row < MAP_H; row++) {
				const t = new Text({ text: String(row), style: labelStyle });
				t.x = 3;
				t.y = row * TILE + 3;
				app.stage.addChild(t);
			}

			const base = await Assets.load(SPRITE_URL);
			if (disposed) return;
			const sprite = new Sprite(base);
			sprite.anchor.set(0.5);
			sprite.width = TILE - 2;
			sprite.scale.y = sprite.scale.x;
			sprite.rotation = Math.PI;
			setSpritePos(sprite, initialTankState.x, initialTankState.y);
			app.stage.addChild(sprite);
			tankSprite = sprite;

			const enemySkin: Record<string, string> = {
				dark: 'tank_dark.png',
				red: 'tank_red.png',
				green: 'tank_green.png',
				sand: 'tank_sand.png',
				heavy: 'tank_bigRed.png'
			};
			const enemyTexture = await Assets.load(
				`/assets/kenney-remastered/${enemySkin[mission.enemy.skin ?? 'red'] ?? 'tank_red.png'}`
			);
			if (disposed) return;
			enemySprite = new Sprite(enemyTexture);
			enemySprites = [enemySprite];
			enemySprite.anchor.set(0.5);
			enemySprite.width = TILE - 8;
			enemySprite.height = TILE - 8;
			enemySprite.rotation = Math.PI;
			setSpritePos(enemySprite, mission.enemy.x, mission.enemy.y);
			app.stage.addChild(enemySprite);

			for (const extra of (mission.enemies ?? []).slice(1)) {
				const texture = await Assets.load(
					`/assets/kenney-remastered/${enemySkin[extra.skin ?? 'red'] ?? 'tank_red.png'}`
				);
				if (disposed) return;
				const sprite = new Sprite(texture);
				sprite.anchor.set(0.5);
				sprite.width = TILE - 8;
				sprite.height = TILE - 8;
				sprite.rotation = Math.PI;
				setSpritePos(sprite, extra.x, extra.y);
				app.stage.addChild(sprite);
				enemySprites.push(sprite);
			}
			combatEffects = new CombatEffects(app, TILE, () => animationSpeed);
		}
	});

	onDestroy(() => {
		disposed = true;
		cancelMotions();
		combatEffects?.destroy();
		combatEffects = null;
		pixiApp?.destroy(true, { children: true });
		pixiApp = null;
		tankSprite = null;
		enemySprite = null;
		enemySprites = [];
		wallSprites.clear();
	});

	// ── Internal Helpers ──────────────────────────────────────────────────────
	function setSpritePos(s: Sprite, x: number, y: number) {
		s.x = x * TILE + TILE / 2;
		s.y = y * TILE + TILE / 2;
	}

	async function internalAnimateFire(
		tank: Sprite,
		dir: Direction,
		bulletUrl = '/assets/kenney-remastered/bulletBlue2.png'
	) {
		if (!combatEffects) return;
		const bulletTexture = await Assets.load(bulletUrl);
		const tankGridX = Math.round((tank.x - TILE / 2) / TILE);
		const tankGridY = Math.round((tank.y - TILE / 2) / TILE);
		const [dx, dy] = {
			UP: [0, -1],
			RIGHT: [1, 0],
			DOWN: [0, 1],
			LEFT: [-1, 0]
		}[dir];
		let impact: ImpactKind = 'none';
		const path: Array<{ x: number; y: number }> = [];
		let cellX = tankGridX + dx;
		let cellY = tankGridY + dy;
		while (cellX >= 0 && cellX < MAP_W && cellY >= 0 && cellY < MAP_H) {
			path.push({ x: cellX, y: cellY });
			if (wallSprites.has(`${cellX},${cellY}`)) {
				impact = 'wall';
				break;
			}
			const hitTank = [tankSprite, ...enemySprites].some((sprite) => {
				if (!sprite || sprite === tank || !sprite.visible) return false;
				const spriteX = Math.round((sprite.x - TILE / 2) / TILE);
				const spriteY = Math.round((sprite.y - TILE / 2) / TILE);
				return spriteX === cellX && spriteY === cellY;
			});
			if (hitTank) {
				impact = 'tank';
				break;
			}
			cellX += dx;
			cellY += dy;
		}
		return combatEffects.animateProjectile({
			texture: bulletTexture,
			start: { x: tankGridX, y: tankGridY },
			path,
			direction: dir,
			impact
		});
	}

	// ── Public API ────────────────────────────────────────────────────────────
	export function setTankPos(x: number, y: number) {
		if (tankSprite) setSpritePos(tankSprite, x, y);
	}

	export function setTankAlive(alive: boolean) {
		if (!tankSprite) return;
		if (alive) tankSprite.visible = true;
		else combatEffects?.explodeTank(tankSprite);
	}

	export function flashPlayerHit() {
		combatEffects?.flashTank(tankSprite);
	}

	export async function setTankDir(dir: Direction) {
		if (!tankSprite) return;
		tankSprite.rotation = {
			UP: Math.PI,
			RIGHT: -Math.PI / 2,
			DOWN: 0,
			LEFT: Math.PI / 2
		}[dir];
	}

	export async function animateTankMove(
		targetGridX: number,
		targetGridY: number,
		durationMs: number
	) {
		if (!tankSprite) return;
		const targetX = targetGridX * TILE + TILE / 2;
		const targetY = targetGridY * TILE + TILE / 2;
		return new Promise<void>((resolve) => {
			const startX = tankSprite!.x;
			const startY = tankSprite!.y;
			const startTime = performance.now();
			const scaledDuration = durationMs / Math.min(2, Math.max(0.5, animationSpeed));
			let finished = false;
			const motion: ActiveMotion = {
				frame: null,
				finish: () => {
					if (finished) return;
					finished = true;
					if (motion.frame !== null) cancelAnimationFrame(motion.frame);
					activeMotions.delete(motion);
					resolve();
				}
			};
			activeMotions.add(motion);

			function step(time: number) {
				motion.frame = null;
				if (disposed || !tankSprite || tankSprite.destroyed) {
					motion.finish();
					return;
				}
				const elapsed = time - startTime;
				const progress = Math.min(elapsed / scaledDuration, 1);
				tankSprite.x = startX + (targetX - startX) * progress;
				tankSprite.y = startY + (targetY - startY) * progress;

				if (progress < 1) {
					motion.frame = requestAnimationFrame(step);
				} else {
					motion.finish();
				}
			}
			motion.frame = requestAnimationFrame(step);
		});
	}

	export async function animateTankFire(dir: Direction) {
		if (tankSprite) await internalAnimateFire(tankSprite, dir);
	}

	export function restoreMissionScene(missionData: MissionData) {
		if (!pixiApp || !brickTexture || !steelTexture) return;
		cancelMotions();
		combatEffects?.reset();
		if (tankSprite) {
			tankSprite.visible = true;
			tankSprite.tint = 0xffffff;
		}
		for (const sprite of wallSprites.values()) sprite.destroy();
		wallSprites.clear();
		for (const wall of missionData.walls) {
			const sprite = new Sprite(wall.type === 'brick' ? brickTexture : steelTexture);
			sprite.anchor.set(0.5);
			sprite.width = TILE - 6;
			sprite.height = TILE - 6;
			setSpritePos(sprite, wall.x, wall.y);
			pixiApp.stage.addChild(sprite);
			wallSprites.set(`${wall.x},${wall.y}`, sprite);
		}
		if (enemySprite) {
			for (const [index, sprite] of enemySprites.entries()) {
				const data = (missionData.enemies ?? [missionData.enemy])[index];
				if (!data) continue;
				sprite.visible = true;
				sprite.tint = 0xffffff;
				setSpritePos(sprite, data.x, data.y);
				sprite.rotation = 0;
			}
		}
	}

	export async function syncBattleState(
		enemy: EnemyState,
		walls: WallState[],
		enemyAction: string,
		enemies: EnemyState[] = [enemy],
		enemyActions: string[] = [enemyAction],
		enemyHitIndexes: number[] = []
	) {
		const activeWalls = new SvelteSet(walls.map((wall) => `${wall.x},${wall.y}`));
		const removeDestroyedWalls = () => {
			for (const [key, sprite] of wallSprites) {
				if (!activeWalls.has(key)) {
					combatEffects?.destroyWall(sprite);
					wallSprites.delete(key);
				}
			}
		};

		for (const [index, sprite] of enemySprites.entries()) {
			const state = enemies[index];
			if (!state) continue;
			if (state.alive) {
				sprite.visible = true;
				sprite.rotation = { UP: Math.PI, RIGHT: -Math.PI / 2, DOWN: 0, LEFT: Math.PI / 2 }[
					state.direction
				];
				if (!(index === 0 && enemyActions[index] === 'move')) {
					setSpritePos(sprite, state.x, state.y);
				}
			}
		}

		const enemyShots = enemySprites
			.map((sprite, index) => ({ sprite, state: enemies[index], action: enemyActions[index] }))
			.filter(({ state, action, sprite }) => state && sprite.visible && action === 'fire')
			.map(({ sprite, state }) =>
				internalAnimateFire(sprite, state!.direction, '/assets/kenney-remastered/bulletRed2.png')
			);

		let primaryMove: Promise<void> | undefined;
		const primaryEnemy = enemies[0] ?? enemy;
		const primaryAction = enemyActions[0] ?? enemyAction;
		if (enemySprite && primaryEnemy.alive && primaryAction === 'move') {
			const startX = enemySprite.x;
			const startY = enemySprite.y;
			const targetX = primaryEnemy.x * TILE + TILE / 2;
			const targetY = primaryEnemy.y * TILE + TILE / 2;
			primaryMove = new Promise<void>((resolve) => {
				const startTime = performance.now();
				const scaledDuration = 250 / Math.min(2, Math.max(0.5, animationSpeed));
				let finished = false;
				const motion: ActiveMotion = {
					frame: null,
					finish: () => {
						if (finished) return;
						finished = true;
						if (motion.frame !== null) cancelAnimationFrame(motion.frame);
						activeMotions.delete(motion);
						resolve();
					}
				};
				activeMotions.add(motion);
				function step(time: number) {
					motion.frame = null;
					if (disposed || !enemySprite || enemySprite.destroyed) {
						motion.finish();
						return;
					}
					const progress = Math.min((time - startTime) / scaledDuration, 1);
					enemySprite.x = startX + (targetX - startX) * progress;
					enemySprite.y = startY + (targetY - startY) * progress;
					if (progress < 1) motion.frame = requestAnimationFrame(step);
					else motion.finish();
				}
				motion.frame = requestAnimationFrame(step);
			});
		} else if (enemySprite && primaryEnemy.alive && primaryAction !== 'fire') {
			setSpritePos(enemySprite, primaryEnemy.x, primaryEnemy.y);
		}

		await Promise.all([...enemyShots, ...(primaryMove ? [primaryMove] : [])]);
		removeDestroyedWalls();

		for (const [index, sprite] of enemySprites.entries()) {
			const state = enemies[index];
			if (!state) continue;
			if (enemyHitIndexes.includes(index)) {
				if (state.alive) combatEffects?.flashTank(sprite);
				else combatEffects?.explodeTank(sprite);
			} else if (!state.alive && sprite.visible) {
				combatEffects?.explodeTank(sprite);
			}
		}
	}
</script>

<div
	class="relative flex flex-1 items-center justify-center overflow-hidden border-b-2 border-outline-variant p-2 sm:p-0"
	style="background-color:#0a1118; background-image:linear-gradient(to right,#1a1a1a 1px,transparent 1px),linear-gradient(to bottom,#1a1a1a 1px,transparent 1px); background-size:40px 40px;"
>
	<div
		bind:this={gameDiv}
		class="pixel-border aspect-[10/8] w-full max-w-[640px] overflow-hidden"
		style="box-shadow:8px 8px 0 #000;"
	></div>
</div>

<style>
	:global(canvas) {
		width: 100% !important;
		height: 100% !important;
		object-fit: contain;
	}
</style>
