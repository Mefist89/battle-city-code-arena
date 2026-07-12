<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Application, Assets, Sprite, Container, Graphics } from 'pixi.js';

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
	};

	let {
		room,
		shotPath
	}: {
		room: Room | null;
		shotPath: Array<{ x: number; y: number }>;
	} = $props();

	let gameDiv: HTMLDivElement | null = $state(null);
	let pixiApp: Application | null = null;

	const ROTATION: Record<string, number> = {
		UP: Math.PI,
		RIGHT: -Math.PI / 2,
		DOWN: 0,
		LEFT: Math.PI / 2
	};
	const BULLET_ROTATION: Record<string, number> = {
		UP: 0,
		RIGHT: Math.PI / 2,
		DOWN: Math.PI,
		LEFT: -Math.PI / 2
	};
	const TILE = 64;
	const MAP_W = 10;
	const MAP_H = 8;

	let tank1Sprite: Sprite | null = null;
	let tank2Sprite: Sprite | null = null;
	let wallsContainer: Container | null = null;
	let pathGraphics: Graphics | null = null;
	let bulletsContainer: Container | null = null;
	let blueBulletTexture: import('pixi.js').Texture | null = null;
	let redBulletTexture: import('pixi.js').Texture | null = null;
	let brickTexture: import('pixi.js').Texture | null = null;
	let steelTexture: import('pixi.js').Texture | null = null;
	let sceneReady = $state(false);

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
			pixiApp = app;
			await app.init({
				width: MAP_W * TILE,
				height: MAP_H * TILE,
				backgroundColor: 0x0a1118,
				antialias: false
			});
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

			pathGraphics = new Graphics();
			app.stage.addChild(pathGraphics);
			bulletsContainer = new Container();
			app.stage.addChild(bulletsContainer);
			sceneReady = true;
		}
	});

	$effect(() => {
		if (!sceneReady) return;
		if (room && tank1Sprite && tank2Sprite && wallsContainer) {
			const t1 = room.tanks['1'];
			if (t1) {
				tank1Sprite.visible = t1.hp > 0;
				setSpritePos(tank1Sprite, t1.x, t1.y);
				updateTankTexture(tank1Sprite, t1.direction);
			} else {
				tank1Sprite.visible = false;
			}

			const t2 = room.tanks['2'];
			if (t2) {
				tank2Sprite.visible = t2.hp > 0;
				setSpritePos(tank2Sprite, t2.x, t2.y);
				updateTankTexture(tank2Sprite, t2.direction);
			} else {
				tank2Sprite.visible = false;
			}

			wallsContainer.removeChildren().forEach((child) => child.destroy());
			if (room.walls && brickTexture && steelTexture) {
				for (const wall of room.walls) {
					const alternating = (wall.x + wall.y) % 3 === 0;
					const sprite = new Sprite(alternating ? steelTexture : brickTexture);
					sprite.anchor.set(0.5);
					sprite.width = TILE - 6;
					sprite.height = TILE - 6;
					setSpritePos(sprite, wall.x, wall.y);
					wallsContainer.addChild(sprite);
				}
			}
		}

		if (pathGraphics && bulletsContainer) {
			pathGraphics.clear();
			bulletsContainer.removeChildren().forEach((child) => child.destroy());
			if (shotPath && shotPath.length > 0) {
				const first = shotPath[0];
				const tank1 = room?.tanks['1'];
				const tank2 = room?.tanks['2'];
				const fromPlayerOne =
					!tank2 ||
					(!!tank1 &&
						Math.abs(first.x - tank1.x) + Math.abs(first.y - tank1.y) <=
							Math.abs(first.x - tank2.x) + Math.abs(first.y - tank2.y));
				const texture = fromPlayerOne ? blueBulletTexture : redBulletTexture;
				const next = shotPath[1] ?? first;
				const direction =
					next.x > first.x ? 'RIGHT' : next.x < first.x ? 'LEFT' : next.y > first.y ? 'DOWN' : 'UP';
				for (let i = 0; i < shotPath.length; i++) {
					const p = shotPath[i];
					if (!texture) continue;
					const bullet = new Sprite(texture);
					bullet.anchor.set(0.5);
					bullet.width = 20;
					bullet.scale.y = bullet.scale.x;
					bullet.rotation = BULLET_ROTATION[direction];
					setSpritePos(bullet, p.x, p.y);
					bulletsContainer.addChild(bullet);
				}
			}
		}
	});

	onDestroy(() => {
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
