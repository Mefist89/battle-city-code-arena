<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import {
		Application,
		Assets,
		Sprite,
		Texture,
		Graphics,
		Text,
		TextStyle
	} from 'pixi.js';
	import type { Direction, EnemyState, WallState, TankState } from '../types';

	let {
		mission,
		initialTankState
	}: {
		mission: any;
		initialTankState: TankState;
	} = $props();

	let gameDiv: HTMLDivElement | null = $state(null);
	let pixiApp: Application | null = null;

	const SPRITE_URL = '/assets/kenney-remastered/tank_blue.png';
	const TILE = 64;
	const MAP_W = 10;
	const MAP_H = 8;

	let tankSprite: Sprite | null = null;
	let enemySprite: Sprite | null = null;
	const wallSprites = new SvelteMap<string, Sprite>();
	let brickTexture: Texture | null = null;
	let steelTexture: Texture | null = null;

	onMount(async () => {
		if (gameDiv) {
			const app = new Application();
			pixiApp = app;
			await app.init({
				width: MAP_W * TILE,
				height: MAP_H * TILE,
				backgroundColor: 0x0a1118,
				antialias: false
			});
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
				`/assets/kenney-remastered/${enemySkin[mission.enemy.skin] ?? 'tank_red.png'}`
			);
			enemySprite = new Sprite(enemyTexture);
			enemySprite.anchor.set(0.5);
			enemySprite.width = TILE - 8;
			enemySprite.height = TILE - 8;
			enemySprite.rotation = Math.PI;
			setSpritePos(enemySprite, mission.enemy.x, mission.enemy.y);
			app.stage.addChild(enemySprite);
		}
	});

	onDestroy(() => {
		pixiApp?.destroy(true, { children: true });
		pixiApp = null;
		tankSprite = null;
		enemySprite = null;
		wallSprites.clear();
	});

	// ── Internal Helpers ──────────────────────────────────────────────────────
	function setSpritePos(s: Sprite, x: number, y: number) {
		s.x = x * TILE + TILE / 2;
		s.y = y * TILE + TILE / 2;
	}

	function setEnemyDir(dir: Direction) {
		if (!enemySprite) return;
		enemySprite.rotation = {
			UP: Math.PI,
			RIGHT: -Math.PI / 2,
			DOWN: 0,
			LEFT: Math.PI / 2
		}[dir];
	}

	async function internalAnimateFire(tank: Sprite, dir: Direction) {
		if (!pixiApp) return;
		const bulletTexture = await Assets.load('/assets/kenney-remastered/bulletBlue2.png');
		const bullet = new Sprite(bulletTexture);
		bullet.anchor.set(0.5);
		bullet.width = Math.floor(TILE * 0.34);
		bullet.scale.y = bullet.scale.x;
		bullet.rotation = {
			UP: 0,
			RIGHT: Math.PI / 2,
			DOWN: Math.PI,
			LEFT: -Math.PI / 2
		}[dir];
		bullet.x = tank.x;
		bullet.y = tank.y;
		pixiApp.stage.addChild(bullet);

		let targetX = bullet.x;
		let targetY = bullet.y;
		let dist = 0;
		if (dir === 'UP') {
			targetY = -TILE;
			dist = bullet.y + TILE;
		}
		if (dir === 'DOWN') {
			targetY = MAP_H * TILE + TILE;
			dist = targetY - bullet.y;
		}
		if (dir === 'LEFT') {
			targetX = -TILE;
			dist = bullet.x + TILE;
		}
		if (dir === 'RIGHT') {
			targetX = MAP_W * TILE + TILE;
			dist = targetX - bullet.x;
		}

		const speed = (MAP_W * TILE) / 500;
		const durationMs = dist / speed;

		return new Promise<void>((resolve) => {
			const startX = bullet.x;
			const startY = bullet.y;
			const startTime = performance.now();

			function step(time: number) {
				const elapsed = time - startTime;
				const progress = Math.min(elapsed / Math.max(durationMs, 100), 1);

				bullet.x = startX + (targetX - startX) * progress;
				bullet.y = startY + (targetY - startY) * progress;

				if (progress < 1) {
					requestAnimationFrame(step);
				} else {
					bullet.destroy();
					resolve();
				}
			}
			requestAnimationFrame(step);
		});
	}

	// ── Public API ────────────────────────────────────────────────────────────
	export function setTankPos(x: number, y: number) {
		if (tankSprite) setSpritePos(tankSprite, x, y);
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

			function step(time: number) {
				const elapsed = time - startTime;
				const progress = Math.min(elapsed / durationMs, 1);
				tankSprite!.x = startX + (targetX - startX) * progress;
				tankSprite!.y = startY + (targetY - startY) * progress;

				if (progress < 1) {
					requestAnimationFrame(step);
				} else {
					resolve();
				}
			}
			requestAnimationFrame(step);
		});
	}

	export async function animateTankFire(dir: Direction) {
		if (tankSprite) await internalAnimateFire(tankSprite, dir);
	}

	export function restoreMissionScene(missionData: any) {
		if (!pixiApp || !brickTexture || !steelTexture) return;
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
			enemySprite.visible = true;
			setSpritePos(enemySprite, missionData.enemy.x, missionData.enemy.y);
			setEnemyDir('DOWN');
		}
	}

	export async function syncBattleState(
		enemy: EnemyState,
		walls: WallState[],
		enemyAction: string
	) {
		const activeWalls = new Set(walls.map((wall) => `${wall.x},${wall.y}`));
		for (const [key, sprite] of wallSprites) {
			if (!activeWalls.has(key)) {
				sprite.destroy();
				wallSprites.delete(key);
			}
		}
		if (!enemySprite) return;
		setEnemyDir(enemy.direction);
		if (!enemy.alive) {
			enemySprite.visible = false;
			return;
		}
		enemySprite.visible = true;
		if (enemyAction === 'move') {
			const startX = enemySprite.x;
			const startY = enemySprite.y;
			const targetX = enemy.x * TILE + TILE / 2;
			const targetY = enemy.y * TILE + TILE / 2;
			await new Promise<void>((resolve) => {
				const startTime = performance.now();
				function step(time: number) {
					const progress = Math.min((time - startTime) / 250, 1);
					enemySprite!.x = startX + (targetX - startX) * progress;
					enemySprite!.y = startY + (targetY - startY) * progress;
					if (progress < 1) requestAnimationFrame(step);
					else resolve();
				}
				requestAnimationFrame(step);
			});
		} else if (enemyAction === 'fire') {
			await internalAnimateFire(enemySprite, enemy.direction);
		} else {
			setSpritePos(enemySprite, enemy.x, enemy.y);
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
