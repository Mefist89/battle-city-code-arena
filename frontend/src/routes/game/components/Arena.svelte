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
	let enemySprites: Sprite[] = [];
	const wallSprites = new SvelteMap<string, Sprite>();
	let brickTexture: Texture | null = null;
	let steelTexture: Texture | null = null;
	type ActiveBullet = { sprite: Sprite; cancelled: boolean };
	const activeBullets: ActiveBullet[] = [];

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
			enemySprites = [enemySprite];
			enemySprite.anchor.set(0.5);
			enemySprite.width = TILE - 8;
			enemySprite.height = TILE - 8;
			enemySprite.rotation = Math.PI;
			setSpritePos(enemySprite, mission.enemy.x, mission.enemy.y);
			app.stage.addChild(enemySprite);

			for (const extra of (mission.enemies ?? []).slice(1)) {
				const texture = await Assets.load(
					`/assets/kenney-remastered/${enemySkin[extra.skin] ?? 'tank_red.png'}`
				);
				const sprite = new Sprite(texture);
				sprite.anchor.set(0.5);
				sprite.width = TILE - 8;
				sprite.height = TILE - 8;
				sprite.rotation = Math.PI;
				setSpritePos(sprite, extra.x, extra.y);
				app.stage.addChild(sprite);
				enemySprites.push(sprite);
			}
		}
	});

	onDestroy(() => {
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

	function flashSpriteHit(sprite: Sprite) {
		sprite.tint = 0xff3030;
		setTimeout(() => {
			if (!sprite.destroyed) sprite.tint = 0xffffff;
		}, 140);
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

	async function internalAnimateFire(
		tank: Sprite,
		dir: Direction,
		bulletUrl = '/assets/kenney-remastered/bulletBlue2.png'
	) {
		if (!pixiApp) return;
		const bulletTexture = await Assets.load(bulletUrl);
		const bullet = new Sprite(bulletTexture);
		const projectile: ActiveBullet = { sprite: bullet, cancelled: false };
		activeBullets.push(projectile);
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

		// Stop the visual projectile at the first wall, matching Challenge VS AI.
		const tankGridX = Math.round((tank.x - TILE / 2) / TILE);
		const tankGridY = Math.round((tank.y - TILE / 2) / TILE);
		const [dx, dy] = {
			UP: [0, -1],
			RIGHT: [1, 0],
			DOWN: [0, 1],
			LEFT: [-1, 0]
		}[dir];
		let hitWall = false;
		const trailCells: Array<{ x: number; y: number }> = [];
		let cellX = tankGridX + dx;
		let cellY = tankGridY + dy;
		while (cellX >= 0 && cellX < MAP_W && cellY >= 0 && cellY < MAP_H) {
			trailCells.push({ x: cellX, y: cellY });
			if (wallSprites.has(`${cellX},${cellY}`)) {
				targetX = cellX * TILE + TILE / 2;
				targetY = cellY * TILE + TILE / 2;
				dist = Math.abs(targetX - bullet.x) + Math.abs(targetY - bullet.y);
				hitWall = true;
				break;
			}
			const hitTank = [tankSprite, ...enemySprites].some((sprite) => {
				if (!sprite || sprite === tank || !sprite.visible) return false;
				const spriteX = Math.round((sprite.x - TILE / 2) / TILE);
				const spriteY = Math.round((sprite.y - TILE / 2) / TILE);
				return spriteX === cellX && spriteY === cellY;
			});
			if (hitTank) {
				targetX = cellX * TILE + TILE / 2;
				targetY = cellY * TILE + TILE / 2;
				dist = Math.abs(targetX - bullet.x) + Math.abs(targetY - bullet.y);
				hitWall = true;
				break;
			}
			cellX += dx;
			cellY += dy;
		}

		const shotTrail = new Graphics();
		const trailColor = bulletUrl.includes('Red') ? 0xff4444 : 0x4da6ff;
		for (const cell of trailCells) {
			shotTrail.rect(cell.x * TILE, cell.y * TILE, TILE, TILE);
			shotTrail.fill({ color: trailColor, alpha: 0.2 });
		}
		pixiApp.stage.addChild(shotTrail);
		pixiApp.stage.setChildIndex(bullet, pixiApp.stage.children.length - 1);

		const speed = (MAP_W * TILE) / 500;
		const durationMs = dist / speed;

		return new Promise<void>((resolve) => {
			const startX = bullet.x;
			const startY = bullet.y;
			const startTime = performance.now();

			function step(time: number) {
				if (projectile.cancelled) {
					setTimeout(() => shotTrail.destroy(), 80);
					resolve();
					return;
				}
				const elapsed = time - startTime;
				const progress = Math.min(elapsed / Math.max(durationMs, 100), 1);

				bullet.x = startX + (targetX - startX) * progress;
				bullet.y = startY + (targetY - startY) * progress;

				const collision = activeBullets.find(
					(other) =>
						other !== projectile &&
						!other.cancelled &&
						Math.hypot(other.sprite.x - bullet.x, other.sprite.y - bullet.y) < 18
				);
				if (collision) {
					projectile.cancelled = true;
					collision.cancelled = true;
					for (const item of [projectile, collision]) {
						const index = activeBullets.indexOf(item);
						if (index >= 0) activeBullets.splice(index, 1);
					}
					const impact = new Graphics();
					impact.circle(bullet.x, bullet.y, 18);
					impact.fill({ color: 0xffffff, alpha: 0.8 });
					pixiApp?.stage.addChild(impact);
					if (!bullet.destroyed) bullet.destroy();
					if (!collision.sprite.destroyed) collision.sprite.destroy();
					setTimeout(() => impact.destroy(), 100);
					setTimeout(() => shotTrail.destroy(), 80);
					resolve();
					return;
				}

				if (progress < 1) {
					requestAnimationFrame(step);
				} else {
					if (hitWall && pixiApp) {
						const impact = new Graphics();
						impact.circle(targetX, targetY, 15);
						impact.fill({ color: 0xffb347, alpha: 0.65 });
						pixiApp.stage.addChild(impact);
						setTimeout(() => impact.destroy(), 90);
					}
					bullet.destroy();
					const bulletIndex = activeBullets.indexOf(projectile);
					if (bulletIndex >= 0) activeBullets.splice(bulletIndex, 1);
					setTimeout(() => shotTrail.destroy(), 80);
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

	export function setTankAlive(alive: boolean) {
		if (tankSprite) tankSprite.visible = alive;
	}

	export function flashPlayerHit() {
		if (tankSprite?.visible) flashSpriteHit(tankSprite);
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
		if (tankSprite) tankSprite.visible = true;
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
		const activeWalls = new Set(walls.map((wall) => `${wall.x},${wall.y}`));
		const removeDestroyedWalls = () => {
			for (const [key, sprite] of wallSprites) {
				if (!activeWalls.has(key)) {
					sprite.destroy();
					wallSprites.delete(key);
				}
			}
		};
		for (const [index, sprite] of enemySprites.entries()) {
			const state = enemies[index];
			if (!state) continue;
			sprite.visible = state.alive;
			if (state.alive) {
				sprite.rotation = { UP: Math.PI, RIGHT: -Math.PI / 2, DOWN: 0, LEFT: Math.PI / 2 }[state.direction];
				setSpritePos(sprite, state.x, state.y);
				if (enemyHitIndexes.includes(index)) flashSpriteHit(sprite);
			}
		}
		const extraShots = enemySprites
			.map((sprite, index) => ({ sprite, state: enemies[index], action: enemyActions[index] }))
			.filter(({ state, action }, index) => index > 0 && state?.alive && action === 'fire')
			.map(({ sprite, state }) =>
				internalAnimateFire(sprite, state.direction, '/assets/kenney-remastered/bulletRed2.png')
			);
		if (extraShots.length) await Promise.all(extraShots);
		if (!enemySprite) {
			removeDestroyedWalls();
			return;
		}
		const primaryEnemy = enemies[0] ?? enemy;
		const primaryAction = enemyActions[0] ?? enemyAction;
		setEnemyDir(primaryEnemy.direction);
		if (!primaryEnemy.alive) {
			enemySprite.visible = false;
			removeDestroyedWalls();
			return;
		}
		enemySprite.visible = true;
		if (primaryAction === 'move') {
			const startX = enemySprite.x;
			const startY = enemySprite.y;
			const targetX = primaryEnemy.x * TILE + TILE / 2;
			const targetY = primaryEnemy.y * TILE + TILE / 2;
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
		} else if (primaryAction === 'fire') {
			await internalAnimateFire(
				enemySprite,
				primaryEnemy.direction,
				'/assets/kenney-remastered/bulletRed2.png'
			);
		} else {
			setSpritePos(enemySprite, primaryEnemy.x, primaryEnemy.y);
		}
		removeDestroyedWalls();
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
