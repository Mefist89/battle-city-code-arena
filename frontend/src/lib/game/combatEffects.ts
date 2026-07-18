import { Application, Container, Graphics, Sprite, Texture } from 'pixi.js';

export type CombatDirection = 'UP' | 'RIGHT' | 'DOWN' | 'LEFT';
export type GridPoint = { x: number; y: number };
export type ImpactKind = 'none' | 'tank' | 'wall' | 'steel' | 'collision';

export const COMBAT_TIMING = {
	cellTravelMs: 48,
	minimumShotMs: 80,
	hitFlashMs: 140,
	impactMs: 120,
	explosionMs: 260
} as const;

export const BULLET_ROTATION: Record<CombatDirection, number> = {
	UP: 0,
	RIGHT: Math.PI / 2,
	DOWN: Math.PI,
	LEFT: -Math.PI / 2
};

export function projectileDuration(pathLength: number) {
	return Math.max(COMBAT_TIMING.minimumShotMs, pathLength * COMBAT_TIMING.cellTravelMs);
}

type ProjectileOptions = {
	texture: Texture;
	start: GridPoint;
	path: GridPoint[];
	direction: CombatDirection;
	impact?: ImpactKind;
	onImpact?: () => void;
};

type ActiveProjectile = {
	sprite: Sprite;
	finished: boolean;
	finish: (collided?: boolean, cancelled?: boolean) => void;
};

export class CombatEffects {
	private disposed = false;
	private timers = new Set<ReturnType<typeof setTimeout>>();
	private frames = new Set<number>();
	private projectiles = new Set<ActiveProjectile>();
	private layer: Container;

	constructor(
		private app: Application,
		private tile: number,
		private getAnimationSpeed: () => number = () => 1
	) {
		this.layer = new Container();
		this.app.stage.addChild(this.layer);
	}

	private scaled(duration: number) {
		return duration / Math.min(2, Math.max(0.5, this.getAnimationSpeed()));
	}

	private center(point: GridPoint) {
		return {
			x: point.x * this.tile + this.tile / 2,
			y: point.y * this.tile + this.tile / 2
		};
	}

	private schedule(callback: () => void, delay: number) {
		const timer = setTimeout(() => {
			this.timers.delete(timer);
			if (!this.disposed) callback();
		}, this.scaled(delay));
		this.timers.add(timer);
	}

	flashTank(sprite: Sprite | null) {
		if (!sprite || sprite.destroyed || !sprite.visible) return;
		sprite.tint = 0xff3030;
		this.schedule(() => {
			if (!sprite.destroyed) sprite.tint = 0xffffff;
		}, COMBAT_TIMING.hitFlashMs);
	}

	impactAt(point: GridPoint, kind: ImpactKind = 'wall') {
		if (kind === 'none' || this.disposed) return;
		const { x, y } = this.center(point);
		const color = {
			tank: 0xff3b30,
			wall: 0xffa12f,
			steel: 0xd8e3ea,
			collision: 0xffffff,
			none: 0xffffff
		}[kind];
		const impact = new Graphics();
		impact.rect(x - 14, y - 14, 28, 28);
		impact.fill({ color, alpha: 0.85 });
		impact.rect(x - 22, y - 5, 44, 10);
		impact.fill({ color, alpha: 0.45 });
		impact.rect(x - 5, y - 22, 10, 44);
		impact.fill({ color, alpha: 0.45 });
		this.layer.addChild(impact);
		this.schedule(() => impact.destroy(), COMBAT_TIMING.impactMs);
	}

	destroyWall(sprite: Sprite) {
		if (sprite.destroyed) return;
		sprite.destroy();
	}

	explodeTank(sprite: Sprite | null) {
		if (!sprite || sprite.destroyed || !sprite.visible) return;
		const x = sprite.x;
		const y = sprite.y;
		sprite.tint = 0xff5a36;
		const explosion = new Graphics();
		explosion.rect(x - 24, y - 8, 48, 16);
		explosion.fill({ color: 0xff6b2d, alpha: 0.9 });
		explosion.rect(x - 8, y - 24, 16, 48);
		explosion.fill({ color: 0xffc247, alpha: 0.95 });
		explosion.rect(x - 14, y - 14, 28, 28);
		explosion.fill({ color: 0xffffff, alpha: 0.7 });
		this.layer.addChild(explosion);
		this.schedule(() => {
			if (!sprite.destroyed) {
				sprite.visible = false;
				sprite.tint = 0xffffff;
			}
			explosion.destroy();
		}, COMBAT_TIMING.explosionMs);
	}

	animateProjectile(options: ProjectileOptions): Promise<void> {
		const { texture, start, path: rawPath, direction, impact = 'none', onImpact } = options;
		const path = rawPath.filter(
			(point): point is GridPoint =>
				Boolean(point) && Number.isFinite(point.x) && Number.isFinite(point.y)
		);
		if (this.disposed) return Promise.resolve();
		const bullet = new Sprite(texture);
		bullet.anchor.set(0.5);
		bullet.width = Math.floor(this.tile * 0.34);
		bullet.scale.y = bullet.scale.x;
		bullet.rotation = BULLET_ROTATION[direction];
		const startPixel = this.center(start);
		bullet.position.set(startPixel.x, startPixel.y);
		this.layer.addChild(bullet);
		return new Promise((resolve) => {
			let frameId: number | null = null;
			let watchdog: ReturnType<typeof setTimeout> | null = null;
			const projectile: ActiveProjectile = {
				sprite: bullet,
				finished: false,
				finish: (collided = false, cancelled = false) => {
					if (projectile.finished) return;
					projectile.finished = true;
					this.projectiles.delete(projectile);
					if (frameId !== null) {
						cancelAnimationFrame(frameId);
						this.frames.delete(frameId);
						frameId = null;
					}
					if (watchdog !== null) {
						clearTimeout(watchdog);
						this.timers.delete(watchdog);
						watchdog = null;
					}
					if (!bullet.destroyed) bullet.destroy();
					if (!collided && !cancelled && path.length) {
						const last = path[path.length - 1];
						this.impactAt(last, impact);
					}
					if (!cancelled) onImpact?.();
					resolve();
				}
			};
			this.projectiles.add(projectile);

			if (!path.length) {
				watchdog = setTimeout(() => projectile.finish(), this.scaled(COMBAT_TIMING.minimumShotMs));
				this.timers.add(watchdog);
				return;
			}

			const points = [start, ...path].map((point) => this.center(point));
			const duration = this.scaled(projectileDuration(path.length));
			const startedAt = performance.now();
			const step = (now: number) => {
				if (frameId !== null) this.frames.delete(frameId);
				frameId = null;
				if (this.disposed || projectile.finished || bullet.destroyed) {
					projectile.finish(true, true);
					return;
				}
				// Some browsers can provide an rAF timestamp a fraction earlier than
				// performance.now() used above. Clamp both ends so segment never becomes -1.
				const progress = Math.max(0, Math.min((now - startedAt) / duration, 1));
				const pathProgress = progress * path.length;
				const segment = Math.min(Math.floor(pathProgress), path.length - 1);
				const localProgress = Math.min(pathProgress - segment, 1);
				const from = points[segment] ?? points[0];
				const to = points[segment + 1] ?? points[points.length - 1];
				bullet.x = from.x + (to.x - from.x) * localProgress;
				bullet.y = from.y + (to.y - from.y) * localProgress;
				if (progress < 1) {
					frameId = requestAnimationFrame(step);
					this.frames.add(frameId);
					return;
				}

				projectile.finish();
			};
			frameId = requestAnimationFrame(step);
			this.frames.add(frameId);
			// requestAnimationFrame can be paused by the browser. The watchdog
			// guarantees that an awaited battle step cannot remain pending forever.
			watchdog = setTimeout(() => projectile.finish(), duration + this.scaled(250));
			this.timers.add(watchdog);
		});
	}

	destroy() {
		this.reset();
		this.disposed = true;
		this.layer.destroy({ children: true });
	}

	reset() {
		for (const projectile of [...this.projectiles]) projectile.finish(true, true);
		this.projectiles.clear();
		for (const timer of this.timers) clearTimeout(timer);
		for (const frame of this.frames) cancelAnimationFrame(frame);
		this.timers.clear();
		this.frames.clear();
		this.layer.removeChildren().forEach((child) => child.destroy());
	}
}
