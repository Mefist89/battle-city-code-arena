<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Application, Assets, Sprite, Texture, Graphics, Container } from 'pixi.js';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { CombatEffects, type ImpactKind, type GridPoint } from '$lib/game/combatEffects';

	type Direction = 'UP' | 'RIGHT' | 'DOWN' | 'LEFT';
	type Fighter = { x: number; y: number; direction: Direction; hp: number };
	let {
		player,
		ai,
		walls,
		animationSpeed = 1
	}: {
		player: Fighter;
		ai: Fighter;
		walls: SvelteSet<string>;
		animationSpeed?: number;
	} = $props();

	let gameDiv: HTMLDivElement | null = $state(null);
	let pixiApp: Application | null = null;

	const TILE = 64;
	const MAP_W = 10;
	const MAP_H = 8;

	let playerSprite: Sprite | null = null;
	let aiSprite: Sprite | null = null;
	let wallsContainer: Container | null = null;
	const wallSprites = new SvelteMap<string, Sprite>();
	let combatEffects: CombatEffects | null = null;
	let brickTexture: Texture | null = null;
	let playerBulletTexture: Texture | null = null;
	let aiBulletTexture: Texture | null = null;
	let sceneReady = $state(false);
	let disposed = false;
	let previousPlayerHp = 100;
	let previousAiHp = 100;

	const ROTATION: Record<Direction, number> = {
		UP: Math.PI,
		RIGHT: -Math.PI / 2,
		DOWN: 0,
		LEFT: Math.PI / 2
	};
	function setSpritePos(sprite: Sprite, x: number, y: number) {
		sprite.x = x * TILE + TILE / 2;
		sprite.y = y * TILE + TILE / 2;
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

			const [loadedBrick, playerTex, aiTex, loadedPlayerBullet, loadedAiBullet] = await Promise.all(
				[
					Assets.load('/assets/kenney/wall-brick.png'),
					Assets.load('/assets/kenney-remastered/tank_blue.png'),
					Assets.load('/assets/kenney-remastered/tank_red.png'),
					Assets.load('/assets/kenney-remastered/bulletBlue2.png'),
					Assets.load('/assets/kenney-remastered/bulletRed2.png')
				]
			);
			if (disposed) return;
			brickTexture = loadedBrick;
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
			combatEffects = new CombatEffects(app, TILE, () => animationSpeed);
			previousPlayerHp = player.hp;
			previousAiHp = ai.hp;
			sceneReady = true;
		}
	});

	$effect(() => {
		if (!sceneReady) return;

		if (playerSprite && aiSprite && wallsContainer) {
			if (player) {
				if (player.hp > 0) playerSprite.visible = true;
				setSpritePos(playerSprite, player.x, player.y);
				playerSprite.rotation = ROTATION[player.direction];
			} else {
				playerSprite.visible = false;
			}

			if (ai) {
				if (ai.hp > 0) aiSprite.visible = true;
				setSpritePos(aiSprite, ai.x, ai.y);
				aiSprite.rotation = ROTATION[ai.direction];
			} else {
				aiSprite.visible = false;
			}

			if (walls && brickTexture) {
				const activeWalls = new SvelteSet(walls);
				for (const [wallKey, sprite] of wallSprites) {
					if (!activeWalls.has(wallKey)) {
						combatEffects?.destroyWall(sprite);
						wallSprites.delete(wallKey);
					}
				}
				for (const wallKey of walls) {
					if (wallSprites.has(wallKey)) continue;
					const [x, y] = wallKey.split(',').map(Number);
					const wSprite = new Sprite(brickTexture);
					wSprite.anchor.set(0.5);
					wSprite.width = TILE - 6;
					wSprite.height = TILE - 6;
					setSpritePos(wSprite, x, y);
					wallsContainer.addChild(wSprite);
					wallSprites.set(wallKey, wSprite);
				}
			}

			if (player.hp < previousPlayerHp) {
				if (player.hp <= 0) combatEffects?.explodeTank(playerSprite);
				else combatEffects?.flashTank(playerSprite);
			}
			if (ai.hp < previousAiHp) {
				if (ai.hp <= 0) combatEffects?.explodeTank(aiSprite);
				else combatEffects?.flashTank(aiSprite);
			}
			previousPlayerHp = player.hp;
			previousAiHp = ai.hp;
		}
	});

	export function animateShot(
		owner: 'PLAYER' | 'AI',
		path: GridPoint[],
		impact: ImpactKind,
		onImpact: () => void
	) {
		const shooter = owner === 'PLAYER' ? player : ai;
		const texture = owner === 'PLAYER' ? playerBulletTexture : aiBulletTexture;
		if (!combatEffects || !texture) {
			onImpact();
			return Promise.resolve();
		}
		return combatEffects.animateProjectile({
			texture,
			start: { x: shooter.x, y: shooter.y },
			path,
			direction: shooter.direction,
			impact,
			onImpact
		});
	}

	export function resetEffects() {
		combatEffects?.reset();
		for (const sprite of [playerSprite, aiSprite]) {
			if (!sprite || sprite.destroyed) continue;
			sprite.visible = true;
			sprite.tint = 0xffffff;
		}
		previousPlayerHp = player.hp;
		previousAiHp = ai.hp;
	}

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
