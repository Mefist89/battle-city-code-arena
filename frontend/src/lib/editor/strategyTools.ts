export type StrategyIssue = {
	line: number;
	message: string;
};

export type StrategyExample = {
	id: 'if' | 'for' | 'while' | 'scan';
	code: string;
};

export const STRATEGY_EXAMPLES: StrategyExample[] = [
	{ id: 'if', code: "if scan():\n    fire()\nelse:\n    rotate('RIGHT')" },
	{ id: 'for', code: 'for i in range(3):\n    move()\n    scan()' },
	{ id: 'while', code: "while scan():\n    fire()\n    rotate('LEFT')" },
	{ id: 'scan', code: 'scan()\nif scan():\n    fire()' }
];

const CALL_PATTERN = /^(move|fire|scan)\s*\(\s*\)\s*$/;
const ROTATE_PATTERN = /^rotate\s*\(\s*(?:['"](?:LEFT|RIGHT)['"])?\s*\)\s*$/i;
const FOR_PATTERN = /^for\s+[A-Za-z_]\w*\s+in\s+range\s*\(([^)]*)\)\s*:\s*$/;
const CONDITION_PATTERN = /^(if|while)\s+scan\s*\(\s*\)\s*:\s*$/;

export function validateStrategy(source: string): StrategyIssue[] {
	const issues: StrategyIssue[] = [];
	const lines = source.replaceAll('\t', '    ').split('\n');
	let expectsIndentAfter: { line: number; indent: number } | null = null;

	for (let index = 0; index < lines.length; index++) {
		const raw = lines[index];
		const trimmed = raw.trim();
		if (!trimmed || trimmed.startsWith('#')) continue;
		const indent = raw.length - raw.trimStart().length;

		if (indent % 4 !== 0) {
			issues.push({ line: index + 1, message: 'Indentation must use groups of 4 spaces' });
		}
		if (expectsIndentAfter) {
			if (indent <= expectsIndentAfter.indent) {
				issues.push({
					line: index + 1,
					message: `Expected an indented block after line ${expectsIndentAfter.line}`
				});
			}
			expectsIndentAfter = null;
		}

		const forMatch = trimmed.match(FOR_PATTERN);
		if (forMatch) {
			const args = forMatch[1]
				.split(',')
				.map((value) => value.trim())
				.filter(Boolean);
			if (args.length < 1 || args.length > 3 || args.some((value) => !/^-?\d+$/.test(value))) {
				issues.push({ line: index + 1, message: 'range() requires 1 to 3 integer constants' });
			}
			expectsIndentAfter = { line: index + 1, indent };
			continue;
		}
		if (CONDITION_PATTERN.test(trimmed)) {
			expectsIndentAfter = { line: index + 1, indent };
			continue;
		}
		if (/^else\s*:\s*$/.test(trimmed)) {
			expectsIndentAfter = { line: index + 1, indent };
			continue;
		}
		if (CALL_PATTERN.test(trimmed) || ROTATE_PATTERN.test(trimmed) || trimmed === 'pass') continue;

		if (/^(if|while)\b/.test(trimmed)) {
			issues.push({ line: index + 1, message: 'if and while conditions must use scan()' });
		} else if (/^for\b/.test(trimmed)) {
			issues.push({ line: index + 1, message: 'Use: for i in range(N):' });
		} else {
			issues.push({ line: index + 1, message: 'Unsupported command or Python syntax' });
		}
	}

	if (expectsIndentAfter) {
		issues.push({
			line: expectsIndentAfter.line,
			message: 'This block needs at least one indented command'
		});
	}
	return issues;
}

export function formatStrategy(source: string): string {
	const formatted = source
		.replaceAll('\t', '    ')
		.split('\n')
		.map((line) => {
			const content = line.trim();
			if (!content) return '';
			const spaces = line.length - line.trimStart().length;
			const indent = ' '.repeat(Math.round(spaces / 4) * 4);
			return `${indent}${content}`;
		})
		.join('\n')
		.replace(/\n{3,}/g, '\n\n')
		.trimEnd();
	return formatted ? `${formatted}\n` : '';
}
