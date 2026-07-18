export type GameSound = 'move' | 'fire' | 'impact' | 'explosion';

const SOURCES: Record<GameSound, string> = {
	move: '/audio/missions/move.mp3',
	fire: '/audio/missions/fire.mp3',
	impact: '/audio/missions/explosive.mp3',
	explosion: '/audio/missions/explosive.mp3'
};

const SOUND_GAIN: Record<GameSound, number> = {
	move: 0.45,
	fire: 0.8,
	impact: 0.45,
	explosion: 1
};

const VOICES_PER_SOUND = 4;
const PLAY_COOLDOWN_MS: Record<GameSound, number> = {
	move: 100,
	fire: 45,
	impact: 60,
	explosion: 120
};

export class GameAudio {
	private voices = new Map<GameSound, HTMLAudioElement[]>();
	private active = new Map<HTMLAudioElement, GameSound>();
	private lastPlayed = new Map<GameSound, number>();
	private volume = 0.7;
	private muted = false;

	constructor() {
		if (typeof Audio === 'undefined') return;
		for (const sound of Object.keys(SOURCES) as GameSound[]) {
			const pool = Array.from({ length: VOICES_PER_SOUND }, () => {
				const audio = new Audio(SOURCES[sound]);
				audio.preload = 'auto';
				const cleanup = () => this.active.delete(audio);
				audio.addEventListener('ended', cleanup);
				audio.addEventListener('error', cleanup);
				return audio;
			});
			this.voices.set(sound, pool);
		}
	}

	configure(volume: number, muted: boolean) {
		this.volume = Math.min(1, Math.max(0, volume));
		this.muted = muted;
		for (const [audio, sound] of this.active) {
			audio.muted = muted;
			audio.volume = Math.min(1, this.volume * SOUND_GAIN[sound]);
		}
	}

	play(sound: GameSound) {
		const pool = this.voices.get(sound);
		if (!pool || this.muted || this.volume <= 0) return;
		const now = performance.now();
		if (now - (this.lastPlayed.get(sound) ?? -Infinity) < PLAY_COOLDOWN_MS[sound]) return;
		const audio = pool.find((voice) => voice.paused || voice.ended);
		if (!audio) return;
		this.lastPlayed.set(sound, now);
		audio.currentTime = 0;
		audio.volume = Math.min(1, this.volume * SOUND_GAIN[sound]);
		audio.muted = this.muted;
		this.active.set(audio, sound);
		void audio.play().catch(() => this.active.delete(audio));
	}

	stop() {
		for (const audio of this.active.keys()) {
			audio.pause();
			audio.currentTime = 0;
		}
		this.active.clear();
		this.lastPlayed.clear();
	}
}
