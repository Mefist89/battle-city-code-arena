<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';

	type AuthMode = 'login' | 'register';
	type AuthUser = { id: string; email: string; name: string; picture?: string; provider: string };
	const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

	let mode = $state<AuthMode>('login');
	let message = $state('');
	let messageType = $state<'info' | 'error'>('info');
	let user = $state<AuthUser | null>(null);

	onMount(async () => {
		const result = new URLSearchParams(window.location.search).get('oauth');
		if (result === 'error' || result === 'unverified') {
			messageType = 'error';
			message = $t('auth.oauthError');
		}
		await loadUser();
	});

	async function loadUser() {
		try {
			const response = await fetch(`${API_URL}/auth/me`, { credentials: 'include' });
			if (!response.ok) return;
			const data = await response.json();
			user = data.authenticated ? data.user : null;
		} catch {
			user = null;
		}
	}

	function switchMode(nextMode: AuthMode) {
		mode = nextMode;
		message = '';
	}

	function selectProvider(provider: string) {
		const providerKey = provider.toLowerCase() as 'google' | 'github';
		const next = new URLSearchParams(window.location.search).get('next');
		const suffix = next ? `?next=${encodeURIComponent(next)}` : '';
		window.location.assign(`${API_URL}/auth/${providerKey}${suffix}`);
	}

	async function logout() {
		await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
		user = null;
		message = '';
	}
</script>

<svelte:head>
	<title>{$t('auth.pageTitle')}</title>
	<meta name="description" content={$t('auth.subtitle')} />
</svelte:head>

<div
	class="grid-bg relative min-h-screen overflow-hidden bg-surface px-4 py-8 font-mono text-on-surface sm:px-6 lg:grid lg:place-items-center lg:py-12"
>
	<div class="scanlines pointer-events-none fixed inset-0 z-50 opacity-[0.035]"></div>

	<a
		href="/"
		class="relative z-10 mx-auto mb-6 flex w-fit items-center gap-3 text-primary uppercase lg:fixed lg:top-7 lg:left-8 lg:m-0"
	>
		<span
			class="flex h-11 w-11 overflow-hidden border-2 border-outline-variant bg-black shadow-[4px_4px_0_#000]"
		>
			<img
				src="/assets/codetank-logo-mark-transparent.png"
				alt=""
				class="h-full w-full scale-[1.45] object-cover"
			/>
		</span>
		<span class="font-black">CODETANK ARENA</span>
	</a>

	<main
		class="relative z-10 mx-auto grid w-full max-w-[1080px] border-4 border-outline-variant bg-surface-container-lowest shadow-[12px_12px_0_#000] lg:grid-cols-[0.9fr_1.1fr]"
	>
		<section
			class="relative hidden overflow-hidden border-r-4 border-outline-variant bg-primary-container p-10 text-on-primary-container lg:flex lg:flex-col lg:justify-between"
		>
			<div
				class="absolute inset-0 [background-image:linear-gradient(#fff_1px,transparent_1px),linear-gradient(90deg,#fff_1px,transparent_1px)] [background-size:32px_32px] opacity-15"
			></div>
			<div class="relative">
				<div
					class="mb-8 inline-flex border-2 border-on-primary-container px-3 py-1 text-[10px] font-black tracking-[0.2em] uppercase"
				>
					{$t('auth.secure')}
				</div>
				<div
					class="mx-auto mb-9 flex aspect-square max-w-64 items-center justify-center bg-transparent"
				>
					<img
						src="/assets/codetank-logo-mark-transparent.png"
						alt=""
						class="h-full w-full object-contain p-2"
					/>
				</div>
				<p class="text-xs leading-6 font-bold tracking-wider uppercase">
					&gt; AUTH_PROTOCOL INITIALIZED<br />&gt; IDENTITY CHECK READY<br />&gt; CLOUD SAVE STANDBY
				</p>
			</div>

			<ul class="relative space-y-3 text-xs font-bold uppercase">
				<li class="flex items-center gap-3">
					<span class="text-secondary-fixed">✓</span>{$t('auth.featureOne')}
				</li>
				<li class="flex items-center gap-3">
					<span class="text-secondary-fixed">✓</span>{$t('auth.featureTwo')}
				</li>
				<li class="flex items-center gap-3">
					<span class="text-secondary-fixed">✓</span>{$t('auth.featureThree')}
				</li>
			</ul>
		</section>

		<section class="p-5 sm:p-8 lg:p-12">
			<p class="mb-3 text-[10px] font-bold tracking-[0.22em] text-tertiary uppercase">
				{$t('auth.eyebrow')}
			</p>
			<h1 class="mb-3 text-3xl leading-tight font-black text-primary uppercase sm:text-4xl">
				{$t('auth.title')}
			</h1>
			<p class="mb-8 max-w-xl text-sm leading-6 text-on-surface-variant">{$t('auth.subtitle')}</p>

			{#if user}
				<div
					class="mb-7 flex flex-wrap items-center gap-4 border-2 border-secondary-fixed bg-surface-container p-4 shadow-[4px_4px_0_#000]"
				>
					{#if user.picture}
						<img
							src={user.picture}
							alt=""
							referrerpolicy="no-referrer"
							class="h-12 w-12 border-2 border-secondary-fixed"
						/>
					{/if}
					<div class="min-w-0 flex-1">
						<p class="text-[10px] font-bold tracking-widest text-secondary-fixed uppercase">
							{$t('auth.welcome')}
						</p>
						<p class="truncate font-black text-primary">{user.name}</p>
						<p class="truncate text-xs text-on-surface-variant">{user.email}</p>
					</div>
					<div class="flex gap-2">
						<a
							href="/profile"
							class="border-2 border-primary px-3 py-2 text-xs font-black text-primary uppercase hover:bg-primary hover:text-on-primary"
							>{$t('common.profile')}</a
						>
						<button
							type="button"
							onclick={logout}
							class="border-2 border-error px-3 py-2 text-xs font-black text-error uppercase hover:bg-error hover:text-on-error"
							>{$t('auth.logout')}</button
						>
					</div>
				</div>
			{/if}

			<div class="mb-7 grid grid-cols-2 border-2 border-outline-variant bg-surface-container">
				<button
					type="button"
					class="border-r border-outline-variant px-3 py-3 text-sm font-black uppercase"
					class:bg-primary={mode === 'login'}
					class:text-on-primary={mode === 'login'}
					class:text-on-surface-variant={mode !== 'login'}
					aria-pressed={mode === 'login'}
					onclick={() => switchMode('login')}>{$t('auth.login')}</button
				>
				<button
					type="button"
					class="border-l border-outline-variant px-3 py-3 text-sm font-black uppercase"
					class:bg-primary={mode === 'register'}
					class:text-on-primary={mode === 'register'}
					class:text-on-surface-variant={mode !== 'register'}
					aria-pressed={mode === 'register'}
					onclick={() => switchMode('register')}>{$t('auth.register')}</button
				>
			</div>

			<div class="grid gap-3 sm:grid-cols-2">
				<button
					type="button"
					onclick={() => selectProvider('Google')}
					class="flex items-center justify-center gap-3 border-2 border-outline-variant bg-surface-container px-4 py-3 text-sm font-bold hover:border-primary hover:text-primary"
				>
					<span
						class="flex h-6 w-6 items-center justify-center bg-white font-sans text-base font-black text-[#4285f4]"
						>G</span
					>
					{$t('auth.google')}
				</button>
				<button
					type="button"
					onclick={() => selectProvider('GitHub')}
					class="flex items-center justify-center gap-3 border-2 border-outline-variant bg-surface-container px-4 py-3 text-sm font-bold hover:border-primary hover:text-primary"
				>
					<svg aria-hidden="true" viewBox="0 0 24 24" class="h-6 w-6 fill-current"
						><path
							d="M12 .7a11.5 11.5 0 0 0-3.64 22.4c.58.1.79-.25.79-.56v-2.23c-3.22.7-3.9-1.37-3.9-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.78 1.2 1.78 1.2 1.04 1.77 2.72 1.26 3.38.96.1-.75.4-1.26.74-1.55-2.57-.3-5.27-1.29-5.27-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.16 1.18A11 11 0 0 1 12 6.09c.98 0 1.96.13 2.87.39 2.2-1.49 3.16-1.18 3.16-1.18.63 1.59.23 2.77.11 3.06.74.81 1.19 1.84 1.19 3.1 0 4.41-2.71 5.39-5.29 5.68.42.36.79 1.06.79 2.14v3.26c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .7Z"
						/></svg
					>
					{$t('auth.github')}
				</button>
			</div>

			<div class="mt-7 border-2 border-tertiary bg-surface-container p-4 shadow-[4px_4px_0_#000]">
				<p class="mb-2 text-xs font-black tracking-wide text-tertiary uppercase">
					&gt; {$t('auth.emailUnavailable')}
				</p>
				<p class="text-xs leading-5 text-on-surface-variant">{$t('auth.useSocial')}</p>
			</div>

			{#if message}
				<div
					role="status"
					class="mt-5 border-2 p-3 text-xs leading-5"
					class:border-error={messageType === 'error'}
					class:text-error={messageType === 'error'}
					class:border-tertiary={messageType === 'info'}
					class:text-tertiary={messageType === 'info'}
				>
					&gt; {message}
				</div>
			{/if}
		</section>
	</main>
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
