<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Application, Assets, Sprite, Texture, Graphics, Container } from 'pixi.js';
	import type { SvelteSet } from 'svelte/reactivity';

	type Direction = 'UP' | 'RIGHT' | 'DOWN' | 'LEFT';
	type Fighter = { x: number; y: number; direction: Direction; hp: number };
	type Bullet = {
		id: number;
		x: number;
		y: number;
		owner: 'PLAYER' | 'AI';
		direction: Direction;
	};

	let {
		player,
		ai,
		walls,
		bullets,
		shotCells
	}: {
		player: Fighter;
		ai: Fighter;
		walls: SvelteSet<string>;
		bullets: Bullet[];
		shotCells: SvelteSet<string>;
	} = $props();

	let gameDiv: HTMLDivElement | null = $state(null);
	let pixiApp: Application | null = null;

	const TILE = 64;
	const MAP_W = 10;
	const MAP_H = 8;

	let playerSprite: Sprite | null = null;
	let aiSprite: Sprite | null = null;
	let wallsContainer: Container | null = null;
	let bulletsContainer: Container | null = null;
	let pathGraphics: Graphics | null = null;
	let brickTexture: Texture | null = null;
	let playerBulletTexture: Texture | null = null;
	let aiBulletTexture: Texture | null = null;
	let sceneReady = $state(false);

	const ROTATION: Record<Direction, number> = {
		UP: Math.PI,
		RIGHT: -Math.PI / 2,
		DOWN: 0,
		LEFT: Math.PI / 2
	};
	const BULLET_ROTATION: Record<Direction, number> = {
		UP: 0,
		RIGHT: Math.PI / 2,
		DOWN: Math.PI,
		LEFT: -Math.PI / 2
	};

	function setSpritePos(sprite: Sprite, x: number, y: number) {
		sprite.x = x * TILE + TILE / 2;
		sprite.y = y * TILE + TILE / 2;
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

			brickTexture = await Assets.load('/assets/kenney/wall-brick.png');
			const [playerTex, aiTex, loadedPlayerBullet, loadedAiBullet] = await Promise.all([
				Assets.load('/assets/kenney-remastered/tank_blue.png'),
				Assets.load('/assets/kenney-remastered/tank_red.png'),
				Assets.load('/assets/kenney-remastered/bulletBlue2.png'),
				Assets.load('/assets/kenney-remastered/bulletRed2.png')
			]);
			playerBulletTexture = loadedPlayerBullet;
			aiBulletTexture = loadedAiBullet;

			playerSprite = new Sprite(playerTex);
			playerSprite.anchor.set(0.5);
			playerSprite.width = TILE - 8;
			playerSprite.height = TILE - 8;
			app.stage.addChild(playerSprite);

			aiSprite = new Sprite(aiTex);
			aiSprite.anchor.set(0.5);
			aiSprite.width = TILE - 8;
			aiSprite.height = TILE - 8;
			app.stage.addChild(aiSprite);

			wallsContainer = new Container();
			app.stage.addChild(wallsContainer);
			bulletsContainer = new Container();
			app.stage.addChild(bulletsContainer);

			pathGraphics = new Graphics();
			app.stage.addChild(pathGraphics);
			sceneReady = true;
		}
	});

	$effect(() => {
		if (!sceneReady) return;

		if (playerSprite && aiSprite && wallsContainer) {
			if (player) {
				playerSprite.visible = player.hp > 0;
				setSpritePos(playerSprite, player.x, player.y);
				playerSprite.rotation = ROTATION[player.direction];
			} else {
				playerSprite.visible = false;
			}

			if (ai) {
				aiSprite.visible = ai.hp > 0;
				setSpritePos(aiSprite, ai.x, ai.y);
				aiSprite.rotation = ROTATION[ai.direction];
			} else {
				aiSprite.visible = false;
			}

			wallsContainer.removeChildren();
			if (walls && brickTexture) {
				for (const wallKey of walls) {
					const [x, y] = wallKey.split(',').map(Number);
					const wSprite = new Sprite(brickTexture);
					wSprite.anchor.set(0.5);
					wSprite.width = TILE - 6;
					wSprite.height = TILE - 6;
					setSpritePos(wSprite, x, y);
					wallsContainer.addChild(wSprite);
				}
			}
		}

		if (pathGraphics && bulletsContainer) {
			pathGraphics.clear();
			bulletsContainer.removeChildren().forEach((child) => child.destroy());
			if (shotCells) {
				for (const cellKey of shotCells) {
					const [x, y] = cellKey.split(',').map(Number);
					pathGraphics.rect(x * TILE, y * TILE, TILE, TILE);
					pathGraphics.fill({ color: 0xff4444, alpha: 0.3 });
				}
			}

			if (bullets && bullets.length > 0) {
				for (const bullet of bullets) {
					const texture = bullet.owner === 'PLAYER' ? playerBulletTexture : aiBulletTexture;
					if (!texture) continue;
					const bulletSprite = new Sprite(texture);
					bulletSprite.anchor.set(0.5);
					bulletSprite.width = 22;
					bulletSprite.scale.y = bulletSprite.scale.x;
					bulletSprite.rotation = BULLET_ROTATION[bullet.direction];
					setSpritePos(bulletSprite, bullet.x, bullet.y);
					bulletsContainer.addChild(bulletSprite);
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
	class="relative flex flex-1 items-center justify-center overflow-hidden border-b-2 border-outline-variant p-2 sm:p-0"
	style="background-color:#0a1118; background-image:linear-gradient(to right,#1a1a1a 1px,transparent 1px),linear-gradient(to bottom,#1a1a1a 1px,transparent 1px); background-size:40px 40px;"
>
	<div
		bind:this={gameDiv}
		class="pixel-border mx-auto aspect-[10/8] w-full max-w-[640px] overflow-hidden"
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
