export type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT';
export type LogLevel = 'ok' | 'info' | 'warn' | 'error' | 'cmd';

export interface TankState {
	x: number;
	y: number;
	direction: Direction;
	hp: number;
	score: number;
}

export interface EnemyState {
	x: number;
	y: number;
	direction: Direction;
	hp: number;
	alive: boolean;
}

export interface WallState {
	x: number;
	y: number;
	type: 'brick' | 'steel';
}

export interface LogEntry {
	time: string;
	msg: string;
	level: LogLevel;
}
