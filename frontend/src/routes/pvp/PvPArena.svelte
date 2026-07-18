<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Application, Assets, Sprite, Container, Graphics } from 'pixi.js';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { CombatEffects, type ImpactKind } from '$lib/game/combatEffects';

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
	};
	type Shot = {
		slot: '1' | '2';
		direction: Tank['direction'];
		path: Array<{ x: number; y: number }>;
		collision?: boolean;
		hit?: '1' | '2';
		wall?: { x: number; y: number; type: 'brick' | 'steel'; destroyed: boolean };
	};

	let {
		room,
		shots,
		animationSpeed = 1
	}: {
		room: Room | null;
		shots: Shot[];
		animationSpeed?: number;
	} = $props();

	let gameDiv: HTMLDivElement | null = $state(null);
	let pixiApp: Application | null = null;

	const ROTATION: Record<string, number> = {
		UP: Math.PI,
		RIGHT: -Math.PI / 2,
		DOWN: 0,
		LEFT: Math.PI / 2
	};
	const TILE = 64;
	const MAP_W = 10;
	const MAP_H = 8;

	let tank1Sprite: Sprite | null = null;
	let tank2Sprite: Sprite | null = null;
	let wallsContainer: Container | null = null;
	const wallSprites = new SvelteMap<string, Sprite>();
	let combatEffects: CombatEffects | null = null;
	let blueBulletTexture: import('pixi.js').Texture | null = null;
	let redBulletTexture: import('pixi.js').Texture | null = null;
	let brickTexture: import('pixi.js').Texture | null = null;
	let steelTexture: import('pixi.js').Texture | null = null;
	let sceneReady = $state(false);
	let disposed = false;
	let previousHp1 = 100;
	let previousHp2 = 100;
	let animatedShots: Shot[] | null = null;

	function setSpritePos(sprite: Sprite, x: number, y: number) {
		sprite.x = x * TILE + TILE / 2;
		sprite.y = y * TILE + TILE / 2;
	}

	function updateTankTexture(sprite: Sprite, direction: string) {
		sprite.rotation = ROTATION[direction] ?? ROTATION.UP;
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
				app.destroy(true, { children: true, texture: false });
				return;
			}
			pixiApp = app;
			gameDiv.appendChild(app.canvas);

			// Draw grid
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

			const [blueTank, redTank, blueBullet, redBullet, loadedBrick, loadedSteel] =
				await Promise.all([
					Assets.load('/assets/kenney-remastered/tank_blue.png'),
					Assets.load('/assets/kenney-remastered/tank_red.png'),
					Assets.load('/assets/kenney-remastered/bulletBlue2.png'),
					Assets.load('/assets/kenney-remastered/bulletRed2.png'),
					Assets.load('/assets/kenney/wall-brick.png'),
					Assets.load('/assets/kenney/wall-steel.png')
				]);
			if (disposed) return;
			blueBulletTexture = blueBullet;
			redBulletTexture = redBullet;
			brickTexture = loadedBrick;
			steelTexture = loadedSteel;

			// Create tank 1 (Blue/Default)
			tank1Sprite = new Sprite(blueTank);
			tank1Sprite.anchor.set(0.5);
			tank1Sprite.width = TILE - 2;
			tank1Sprite.scale.y = tank1Sprite.scale.x;
			tank1Sprite.visible = false;
			app.stage.addChild(tank1Sprite);

			// Create tank 2 (Red tinted)
			tank2Sprite = new Sprite(redTank);
			tank2Sprite.anchor.set(0.5);
			tank2Sprite.width = TILE - 2;
			tank2Sprite.scale.y = tank2Sprite.scale.x;
			tank2Sprite.visible = false;
			app.stage.addChild(tank2Sprite);

			wallsContainer = new Container();
			app.stage.addChild(wallsContainer);
			combatEffects = new CombatEffects(app, TILE, () => animationSpeed);
			previousHp1 = room?.tanks['1']?.hp ?? 100;
			previousHp2 = room?.tanks['2']?.hp ?? 100;
			sceneReady = true;
		}
	});

	$effect(() => {
		if (!sceneReady) return;
		if (room && tank1Sprite && tank2Sprite && wallsContainer) {
			const t1 = room.tanks['1'];
			if (t1) {
				if (t1.hp > 0) tank1Sprite.visible = true;
				setSpritePos(tank1Sprite, t1.x, t1.y);
				updateTankTexture(tank1Sprite, t1.direction);
			} else {
				tank1Sprite.visible = false;
			}

			const t2 = room.tanks['2'];
			if (t2) {
				if (t2.hp > 0) tank2Sprite.visible = true;
				setSpritePos(tank2Sprite, t2.x, t2.y);
				updateTankTexture(tank2Sprite, t2.direction);
			} else {
				tank2Sprite.visible = false;
			}

			if (room.walls && brickTexture && steelTexture) {
				const activeWalls = new SvelteSet(room.walls.map((wall) => `${wall.x},${wall.y}`));
				for (const [wallKey, sprite] of wallSprites) {
					if (!activeWalls.has(wallKey)) {
						combatEffects?.destroyWall(sprite);
						wallSprites.delete(wallKey);
					}
				}
				for (const wall of room.walls) {
					const wallKey = `${wall.x},${wall.y}`;
					if (wallSprites.has(wallKey)) continue;
					const sprite = new Sprite(wall.type === 'steel' ? steelTexture : brickTexture);
					sprite.anchor.set(0.5);
					sprite.width = TILE - 6;
					sprite.height = TILE - 6;
					setSpritePos(sprite, wall.x, wall.y);
					wallsContainer.addChild(sprite);
					wallSprites.set(wallKey, sprite);
				}
			}

			if (t1.hp < previousHp1) {
				if (t1.hp <= 0) combatEffects?.explodeTank(tank1Sprite);
				else combatEffects?.flashTank(tank1Sprite);
			}
			if (t2.hp < previousHp2) {
				if (t2.hp <= 0) combatEffects?.explodeTank(tank2Sprite);
				else combatEffects?.flashTank(tank2Sprite);
			}
			previousHp1 = t1.hp;
			previousHp2 = t2.hp;
		}

		if (shots?.length && shots !== animatedShots && room && combatEffects) {
			animatedShots = shots;
			for (const shot of shots) {
				const texture = shot.slot === '1' ? blueBulletTexture : redBulletTexture;
				const shooter = room.tanks[shot.slot];
				if (!texture || !shooter) continue;
				const impact: ImpactKind = shot.collision
					? shot.slot === '1'
						? 'collision'
						: 'none'
					: shot.hit
						? 'tank'
						: shot.wall?.type === 'steel'
							? 'steel'
							: shot.wall
								? 'wall'
								: 'none';
				void combatEffects.animateProjectile({
					texture,
					start: { x: shooter.x, y: shooter.y },
					path: shot.path,
					direction: shot.direction,
					impact
				});
			}
		}
	});

	onDestroy(() => {
		disposed = true;
		sceneReady = false;
		combatEffects?.destroy();
		combatEffects = null;
		wallSprites.clear();
		if (pixiApp) {
			pixiApp.destroy(true, { children: true, texture: false });
		}
	});
</script>

<div
	class="relative w-full overflow-hidden rounded border-2 border-slate-700 bg-slate-950 p-2 sm:p-0"
>
	<div
		bind:this={gameDiv}
		class="mx-auto flex aspect-[10/8] w-full max-w-[640px] justify-center"
	></div>
</div>

<style>
	:global(canvas) {
		width: 100% !important;
		height: 100% !important;
		object-fit: contain;
	}
</style>
