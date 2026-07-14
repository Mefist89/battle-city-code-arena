<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';

	type AuthUser = { id: string; email: string; name: string; picture?: string; provider: string };
	type MissionRecord = { best_score: number; completions: number; completed_at: string };
	type Progress = {
		completed_missions: number[];
		completed_count: number;
		total_missions: number;
		total_score: number;
		missions: Record<string, MissionRecord>;
	};

	const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
	let user = $state<AuthUser | null>(null);
	let progress = $state<Progress | null>(null);
	let loading = $state(true);
	let loggingOut = $state(false);
	let error = $state('');
	let percent = $derived(
		progress ? Math.round((progress.completed_count / progress.total_missions) * 100) : 0
	);

	onMount(loadProfile);

	async function loadProfile() {
		try {
			const response = await fetch(`${API}/auth/profile`, { credentials: 'include' });
			if (response.status === 401) return;
			if (!response.ok) throw new Error('Profile request failed');
			const data = await response.json();
			user = data.user;
			progress = data.progress;
		} catch {
			error = $t('profile.loadError');
		} finally {
			loading = false;
		}
	}

	async function logout() {
		if (loggingOut) return;
		loggingOut = true;
		error = '';
		try {
			const response = await fetch(`${API}/auth/logout`, {
				method: 'POST',
				credentials: 'include'
			});
			if (!response.ok) throw new Error('Logout request failed');
			window.location.assign('/');
		} catch {
			error = $t('profile.logoutError');
			loggingOut = false;
		}
	}
</script>

<svelte:head>
	<title>{$t('profile.pageTitle')}</title>
	<meta name="description" content={$t('profile.subtitle')} />
</svelte:head>

<div class="grid-bg min-h-screen bg-surface px-4 py-6 font-mono text-on-surface sm:px-6 lg:px-8">
	<div class="scanlines pointer-events-none fixed inset-0 z-50 opacity-[0.035]"></div>
	<header class="relative z-10 mx-auto mb-8 flex max-w-[1180px] items-center justify-between gap-4">
		<a href="/" class="flex items-center gap-3 text-primary uppercase">
			<span
				class="flex h-11 w-11 overflow-hidden border-2 border-outline-variant bg-black shadow-[4px_4px_0_#000]"
				><img
					src="/assets/codetank-logo-mark-transparent.png"
					alt=""
					class="h-full w-full scale-[1.45] object-cover"
				/></span
			>
			<span class="hidden font-black sm:inline">CODETANK ARENA</span>
		</a>
		<a
			href="/"
			class="border-2 border-outline-variant bg-surface-container px-4 py-2 text-xs font-black uppercase hover:border-primary hover:text-primary"
			>← {$t('common.home')}</a
		>
	</header>

	<main class="relative z-10 mx-auto max-w-[1180px]">
		{#if loading}
			<div
				class="border-4 border-outline-variant bg-surface-container-lowest p-12 text-center text-primary"
			>
				LOADING PROFILE...
			</div>
		{:else if !user || !progress}
			<section
				class="mx-auto max-w-2xl border-4 border-outline-variant bg-surface-container-lowest p-8 text-center shadow-[10px_10px_0_#000]"
			>
				<p class="mb-3 text-xs font-bold tracking-widest text-tertiary uppercase">
					&gt; AUTH REQUIRED
				</p>
				<h1 class="mb-4 text-3xl font-black text-primary uppercase">{$t('profile.title')}</h1>
				<p class="mb-7 text-sm leading-6 text-on-surface-variant">
					{error || $t('profile.loginRequired')}
				</p>
				<a
					href="/auth"
					class="pixel-shadow text-on-secondary-fixed inline-flex border-2 border-secondary-fixed bg-secondary-fixed px-6 py-4 font-black uppercase"
					>{$t('profile.goLogin')}</a
				>
			</section>
		{:else}
			<section
				class="mb-7 grid gap-5 border-4 border-outline-variant bg-surface-container-lowest p-5 shadow-[10px_10px_0_#000] md:grid-cols-[auto_1fr_auto] md:items-center md:p-7"
			>
				{#if user.picture}<img
						src={user.picture}
						alt=""
						referrerpolicy="no-referrer"
						class="h-24 w-24 border-4 border-secondary-fixed object-cover shadow-[5px_5px_0_#000]"
					/>{/if}
				<div class="min-w-0">
					<p class="mb-2 text-[10px] font-bold tracking-[0.2em] text-tertiary uppercase">
						{$t('profile.eyebrow')}
					</p>
					<h1 class="truncate text-3xl font-black text-primary uppercase sm:text-4xl">
						{user.name}
					</h1>
					<p class="truncate text-sm text-on-surface-variant">{user.email}</p>
					<p class="mt-2 text-[10px] font-bold text-secondary-fixed uppercase">
						✓ {$t('profile.signedWith', {
							provider: user.provider === 'github' ? 'GitHub' : 'Google'
						})}
					</p>
				</div>
				<div class="grid gap-3">
					<div class="border-2 border-outline-variant bg-surface-container p-4 text-center">
						<p class="text-3xl font-black text-secondary-fixed">{percent}%</p>
						<p class="text-[10px] font-bold uppercase">{$t('profile.campaign')}</p>
					</div>
					<button
						type="button"
						onclick={logout}
						disabled={loggingOut}
						class="border-2 border-error bg-surface-container px-4 py-3 text-xs font-black text-error uppercase transition-colors hover:bg-error hover:text-on-error disabled:cursor-wait disabled:opacity-60"
					>
						{loggingOut ? $t('profile.signingOut') : $t('auth.logout')}
					</button>
				</div>
			</section>
			{#if error}<p
					class="mb-5 border-2 border-error bg-surface-container p-3 text-center text-xs font-bold text-error"
				>
					{error}
				</p>{/if}

			<section class="mb-7 grid gap-4 sm:grid-cols-3">
				<div
					class="border-2 border-outline-variant bg-surface-container p-5 shadow-[5px_5px_0_#000]"
				>
					<p class="text-3xl font-black text-primary">{progress.completed_count}/9</p>
					<p class="text-xs font-bold text-on-surface-variant uppercase">
						{$t('profile.completed')}
					</p>
				</div>
				<div
					class="border-2 border-outline-variant bg-surface-container p-5 shadow-[5px_5px_0_#000]"
				>
					<p class="text-3xl font-black text-tertiary">{progress.total_score}</p>
					<p class="text-xs font-bold text-on-surface-variant uppercase">{$t('profile.score')}</p>
				</div>
				<div
					class="border-2 border-outline-variant bg-surface-container p-5 shadow-[5px_5px_0_#000]"
				>
					<p class="text-3xl font-black text-secondary-fixed">{percent}%</p>
					<p class="text-xs font-bold text-on-surface-variant uppercase">
						{$t('profile.progress')}
					</p>
				</div>
			</section>

			<section>
				<div class="mb-4 flex items-end justify-between gap-4">
					<div>
						<p class="text-[10px] font-bold tracking-widest text-tertiary uppercase">
							MISSION ARCHIVE
						</p>
						<h2 class="text-2xl font-black text-primary uppercase">{$t('profile.progress')}</h2>
					</div>
					<span class="text-xs text-on-surface-variant">{progress.completed_count}/9</span>
				</div>
				<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{#each Array.from({ length: 9 }, (_, index) => index + 1) as missionId}
						{@const record = progress.missions[String(missionId)]}
						<article
							class="border-2 bg-surface-container p-5 shadow-[5px_5px_0_#000]"
							class:border-secondary-fixed={!!record}
							class:border-outline-variant={!record}
						>
							<div class="mb-5 flex items-start justify-between">
								<span
									class="text-3xl font-black"
									class:text-secondary-fixed={!!record}
									class:text-outline={!record}>{String(missionId).padStart(2, '0')}</span
								><span
									class="border px-2 py-1 text-[9px] font-black uppercase"
									class:border-secondary-fixed={!!record}
									class:text-secondary-fixed={!!record}
									class:border-outline={!record}
									class:text-outline={!record}
									>{record ? $t('profile.complete') : $t('profile.notComplete')}</span
								>
							</div>
							{#if record}<p class="mb-4 text-xs text-on-surface-variant">
									{$t('profile.bestScore')}:
									<span class="font-black text-tertiary">{record.best_score}</span>
								</p>{:else}<p class="mb-4 text-xs text-outline">NO BATTLE DATA</p>{/if}
							<a
								href={`/game?mission=${missionId}`}
								class="block border-2 border-outline-variant px-3 py-2 text-center text-xs font-black uppercase hover:border-primary hover:text-primary"
								>{$t('profile.play')} →</a
							>
						</article>
					{/each}
				</div>
			</section>
		{/if}
	</main>

	<footer
		class="relative z-10 -mx-4 mt-14 -mb-6 border-t-4 border-outline-variant bg-surface-container-low sm:-mx-6 lg:-mx-8"
	>
		<div
			class="mx-auto flex max-w-[1280px] flex-col items-center justify-between gap-6 px-5 py-8 md:flex-row lg:px-8"
		>
			<a href="/" class="flex items-center gap-3" aria-label="CODETANK ARENA — Home">
				<span
					class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden border-2 border-outline-variant bg-black"
				>
					<img
						src="/assets/codetank-logo-mark-transparent.png"
						alt=""
						class="h-full w-full scale-[1.45] object-cover"
					/>
				</span>
				<span class="font-black text-primary uppercase">CODETANK ARENA</span>
			</a>
			<nav class="flex flex-wrap justify-center gap-5 text-xs uppercase" aria-label="Footer">
				<a href="/" class="text-on-surface-variant hover:text-primary">{$t('common.home')}</a>
				<a href="/missions" class="text-on-surface-variant hover:text-primary"
					>{$t('common.missions')}</a
				>
				<a href="/challenge-maps" class="text-on-surface-variant hover:text-primary"
					>{$t('common.challenge')}</a
				>
				<a href="/pvp-maps" class="text-on-surface-variant hover:text-primary">{$t('common.pvp')}</a
				>
				<a href="/instruction" class="text-on-surface-variant hover:text-primary"
					>{$t('common.instruction')}</a
				>
			</nav>
			<div class="text-center text-[10px] font-bold text-tertiary uppercase md:text-right">
				{$t('common.copyright')}
			</div>
		</div>
	</footer>
</div>

<style>
	.scanlines {
		background: repeating-linear-gradient(to bottom, transparent 0, transparent 3px, #fff 4px);
	}
	.grid-bg {
		background-image:
			linear-gradient(#242838 1px, transparent 1px),
			linear-gradient(90deg, #242838 1px, transparent 1px);
		background-size: 48px 48px;
	}
</style>
