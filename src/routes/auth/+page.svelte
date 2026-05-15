<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import {
		QLCODE_API_PORTAL_URL,
		QLCODE_LOGIN_APP_LOGO_URL,
		QLCODE_LOGIN_HERO_VISUAL_URL,
		QLCODE_LOGIN_WORDMARK_URL,
		WEBUI_BASE_URL
	} from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let mode = 'signin';
	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let ldapUsername = '';
	let showPassword = false;
	let showConfirmPassword = false;

	$: isSignup = mode === 'signup';
	$: isLdap = mode === 'ldap';
	$: canUsePasswordForm =
		$config?.features?.enable_login_form || $config?.features?.enable_ldap || form;
	$: canSignup = ($config?.features?.enable_signup ?? false) && !($config?.onboarding ?? false);
	$: authTitle =
		($config?.onboarding ?? false)
			? '创建管理员账号'
			: isSignup
				? '注册 QLCodeChat'
				: isLdap
					? 'LDAP 登录 QLCodeChat'
					: '登录 QLCodeChat';
	$: submitText =
		($config?.onboarding ?? false)
			? '创建管理员账号'
			: isSignup
				? '注册'
				: isLdap
					? '认证'
					: '登录';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation && password !== confirmPassword) {
			toast.error($i18n.t('Passwords do not match.'));
			return;
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (isLdap) {
			await ldapSignInHandler();
		} else if (isSignup) {
			await signUpHandler();
		} else {
			await signInHandler();
		}
	};

	const oauthCallbackHandler = async () => {
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	const initializeMode = () => {
		if ($config?.onboarding ?? false) {
			mode = 'signup';
		} else if (
			($config?.features?.enable_ldap ?? false) &&
			!($config?.features?.enable_login_form ?? true)
		) {
			mode = 'ldap';
		} else {
			mode = 'signin';
		}
	};

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
			return;
		}

		if (redirectPath) {
			localStorage.setItem('redirectPath', redirectPath);
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');
		initializeMode();
		loaded = true;

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		}
	});
</script>

<svelte:head>
	<title>{`${$WEBUI_NAME}`}</title>
</svelte:head>

<div class="ql-auth-page" id="auth-page">
	{#if loaded}
		{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
			<div class="ql-auth-loading">
				<div class="ql-loading-title">
					{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
				</div>
				<Spinner className="size-5" />
			</div>
		{:else}
			<main class="ql-auth-shell">
				<header class="ql-auth-brand">
					<img src={QLCODE_LOGIN_WORDMARK_URL} alt="QLCodeChat" draggable="false" />
					<a
						class="ql-auth-key-link"
						href={QLCODE_API_PORTAL_URL}
						target="_blank"
						rel="noreferrer"
						aria-label="获取 QLCodeAPI 密钥"
					>
						获取密钥
					</a>
				</header>

				<section class="ql-auth-content" aria-label="QLCodeChat authentication">
					<div class="ql-auth-card {isSignup ? 'ql-auth-card--compact' : ''}">
						<img class="ql-card-logo" src={QLCODE_LOGIN_APP_LOGO_URL} alt="" draggable="false" />

						<h1>{authTitle}</h1>

						{#if canUsePasswordForm}
							<form
								class="ql-auth-form"
								on:submit={(event) => {
									event.preventDefault();
									submitHandler();
								}}
							>
								{#if isSignup}
									<label class="ql-field">
										<span>姓名</span>
										<div class="ql-input-wrap">
											<span class="ql-field-icon" aria-hidden="true">
												<svg viewBox="0 0 24 24" fill="none">
													<path
														d="M20 21a8 8 0 0 0-16 0"
														stroke="currentColor"
														stroke-width="2"
														stroke-linecap="round"
													/>
													<path
														d="M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z"
														stroke="currentColor"
														stroke-width="2"
													/>
												</svg>
											</span>
											<input
												bind:value={name}
												type="text"
												autocomplete="name"
												placeholder="输入您的姓名"
												required
											/>
										</div>
									</label>
								{/if}

								{#if isLdap}
									<label class="ql-field">
										<span>用户名</span>
										<div class="ql-input-wrap">
											<span class="ql-field-icon" aria-hidden="true">
												<svg viewBox="0 0 24 24" fill="none">
													<path
														d="M20 21a8 8 0 0 0-16 0"
														stroke="currentColor"
														stroke-width="2"
														stroke-linecap="round"
													/>
													<path
														d="M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z"
														stroke="currentColor"
														stroke-width="2"
													/>
												</svg>
											</span>
											<input
												bind:value={ldapUsername}
												type="text"
												autocomplete="username"
												placeholder="输入您的用户名"
												required
											/>
										</div>
									</label>
								{:else}
									<label class="ql-field">
										<span>电子邮箱</span>
										<div class="ql-input-wrap">
											<span class="ql-field-icon" aria-hidden="true">
												<svg viewBox="0 0 24 24" fill="none">
													<path
														d="M4 6h16v12H4V6Z"
														stroke="currentColor"
														stroke-width="2"
														stroke-linejoin="round"
													/>
													<path
														d="m5 7 7 6 7-6"
														stroke="currentColor"
														stroke-width="2"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											</span>
											<input
												bind:value={email}
												type="email"
												autocomplete="email"
												placeholder="输入您的电子邮箱"
												required
											/>
										</div>
									</label>
								{/if}

								<label class="ql-field">
									<span>密码</span>
									<div class="ql-input-wrap">
										<span class="ql-field-icon" aria-hidden="true">
											<svg viewBox="0 0 24 24" fill="none">
												<path
													d="M7 10V8a5 5 0 0 1 10 0v2"
													stroke="currentColor"
													stroke-width="2"
													stroke-linecap="round"
												/>
												<path
													d="M6 10h12v10H6V10Z"
													stroke="currentColor"
													stroke-width="2"
													stroke-linejoin="round"
												/>
											</svg>
										</span>
										<input
											bind:value={password}
											type={showPassword ? 'text' : 'password'}
											autocomplete={isSignup ? 'new-password' : 'current-password'}
											placeholder="输入您的密码"
											required
										/>
										<button
											type="button"
											class="ql-password-toggle"
											aria-label="切换密码显示"
											on:click={() => {
												showPassword = !showPassword;
											}}
										>
											<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
												<path
													d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"
													stroke="currentColor"
													stroke-width="2"
													stroke-linejoin="round"
												/>
												<path
													d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
													stroke="currentColor"
													stroke-width="2"
												/>
											</svg>
										</button>
									</div>
								</label>

								{#if isSignup && $config?.features?.enable_signup_password_confirmation}
									<label class="ql-field">
										<span>确认密码</span>
										<div class="ql-input-wrap">
											<span class="ql-field-icon" aria-hidden="true">
												<svg viewBox="0 0 24 24" fill="none">
													<path
														d="M7 10V8a5 5 0 0 1 10 0v2"
														stroke="currentColor"
														stroke-width="2"
														stroke-linecap="round"
													/>
													<path
														d="M6 10h12v10H6V10Z"
														stroke="currentColor"
														stroke-width="2"
														stroke-linejoin="round"
													/>
												</svg>
											</span>
											<input
												bind:value={confirmPassword}
												type={showConfirmPassword ? 'text' : 'password'}
												autocomplete="new-password"
												placeholder="再次输入您的密码"
												required
											/>
											<button
												type="button"
												class="ql-password-toggle"
												aria-label="切换确认密码显示"
												on:click={() => {
													showConfirmPassword = !showConfirmPassword;
												}}
											>
												<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
													<path
														d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"
														stroke="currentColor"
														stroke-width="2"
														stroke-linejoin="round"
													/>
													<path
														d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
														stroke="currentColor"
														stroke-width="2"
													/>
												</svg>
											</button>
										</div>
									</label>
								{/if}

								<button class="ql-submit" type="submit">{submitText}</button>
							</form>
						{/if}

						{#if canSignup || (isSignup && !($config?.onboarding ?? false))}
							<div class="ql-mode-switch">
								<span>{isSignup ? '已有账号？' : '没有账号？'}</span>
								<button
									type="button"
									on:click={() => {
										mode = isSignup ? 'signin' : 'signup';
									}}
								>
									{isSignup ? '去登录' : '立即注册'}
								</button>
							</div>
						{/if}

						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<div class="ql-mode-switch">
								<button
									type="button"
									on:click={() => {
										mode = isLdap ? 'signin' : 'ldap';
									}}
								>
									{isLdap ? '使用邮箱登录' : '使用 LDAP 登录'}
								</button>
							</div>
						{/if}

						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="ql-oauth">
								<div class="ql-oauth-divider"><span>或</span></div>

								{#if $config?.oauth?.providers?.google}
									<button
										type="button"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										使用 Google 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										type="button"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										使用 Microsoft 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										type="button"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										使用 GitHub 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										type="button"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										使用 {$config?.oauth?.providers?.oidc ?? 'SSO'} 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.feishu}
									<button
										type="button"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
										}}
									>
										使用 Feishu 登录
									</button>
								{/if}
							</div>
						{/if}
					</div>

					<div class="ql-auth-hero" aria-hidden="true">
						<img src={QLCODE_LOGIN_HERO_VISUAL_URL} alt="" draggable="false" />
					</div>
				</section>
			</main>
		{/if}
	{/if}
</div>

<style>
	:global(body) {
		background: #f8fbff;
	}

	.ql-auth-page {
		position: relative;
		min-height: 100dvh;
		overflow-x: hidden;
		overflow-y: auto;
		color: #061155;
		background:
			radial-gradient(circle at 84% 34%, rgba(16, 196, 211, 0.14), transparent 28rem),
			radial-gradient(circle at 22% 78%, rgba(5, 83, 255, 0.12), transparent 34rem),
			linear-gradient(135deg, #fbfdff 0%, #f5f9ff 52%, #eef6ff 100%);
		font-family: var(--font-primary);
	}

	.ql-auth-page,
	.ql-auth-page * {
		box-sizing: border-box;
	}

	.ql-auth-page::before {
		content: '';
		position: absolute;
		inset: 0;
		pointer-events: none;
		background-image:
			linear-gradient(rgba(10, 64, 190, 0.04) 1px, transparent 1px),
			linear-gradient(90deg, rgba(10, 64, 190, 0.04) 1px, transparent 1px);
		background-size: 48px 48px;
		mask-image: radial-gradient(circle at 73% 50%, black, transparent 45rem);
	}

	.ql-auth-shell {
		position: relative;
		z-index: 1;
		min-height: 100dvh;
		padding: clamp(20px, 2.6vw, 44px);
		display: flex;
		flex-direction: column;
	}

	.ql-auth-brand {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		min-height: 72px;
	}

	.ql-auth-brand img {
		width: clamp(220px, 18vw, 360px);
		height: auto;
		object-fit: contain;
	}

	.ql-auth-key-link {
		flex: none;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 42px;
		padding: 0 18px;
		border: 1px solid rgba(6, 17, 85, 0.22);
		border-radius: 999px;
		background: #ffffff;
		color: #061155;
		font-size: 1rem;
		font-weight: 800;
		line-height: 1;
		text-decoration: none;
		box-shadow: 0 0.7rem 1.6rem rgba(21, 65, 151, 0.1);
		transition:
			border-color 160ms ease,
			background-color 160ms ease,
			color 160ms ease,
			box-shadow 160ms ease,
			transform 160ms ease;
	}

	.ql-auth-key-link:hover,
	.ql-auth-key-link:focus-visible {
		border-color: #075cf8;
		background: #075cf8;
		color: #ffffff;
		box-shadow: 0 0.8rem 1.8rem rgba(7, 92, 248, 0.18);
		transform: translateY(-1px);
	}

	.ql-auth-content {
		flex: 1;
		display: grid;
		grid-template-columns: minmax(440px, 480px) minmax(420px, 1fr);
		align-items: center;
		gap: clamp(36px, 3vw, 56px);
		max-width: 1180px;
		width: 100%;
		margin: 0 auto;
	}

	.ql-auth-card {
		width: 100%;
		padding: clamp(36px, 2.6vw, 48px) clamp(34px, 2.7vw, 50px);
		border: 1px solid rgba(21, 199, 211, 0.45);
		border-radius: 24px;
		background: rgba(255, 255, 255, 0.72);
		box-shadow:
			0 2rem 5rem rgba(21, 65, 151, 0.12),
			inset 0 1px 0 rgba(255, 255, 255, 0.8);
	}

	.ql-card-logo {
		display: block;
		width: 86px;
		height: 86px;
		object-fit: contain;
		margin: 0 auto 18px;
	}

	.ql-auth-card h1 {
		margin: 0 0 30px;
		text-align: center;
		font-size: clamp(1.75rem, 2.2vw, 2.35rem);
		font-weight: 800;
		color: #050e57;
		letter-spacing: 0;
	}

	.ql-auth-card--compact {
		padding: clamp(22px, 1.8vw, 32px) clamp(34px, 2.7vw, 50px);
	}

	.ql-auth-card--compact .ql-card-logo {
		width: 56px;
		height: 56px;
		margin-bottom: 10px;
	}

	.ql-auth-card--compact h1 {
		margin-bottom: 14px;
		font-size: clamp(1.65rem, 2vw, 2.15rem);
	}

	.ql-auth-card--compact .ql-auth-form {
		gap: 10px;
	}

	.ql-auth-card--compact .ql-field {
		gap: 6px;
	}

	.ql-auth-card--compact .ql-input-wrap {
		height: 46px;
	}

	.ql-auth-card--compact .ql-submit {
		margin-top: 8px;
		height: 48px;
	}

	.ql-auth-card--compact .ql-mode-switch {
		margin-top: 12px;
	}

	.ql-auth-form {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.ql-field {
		display: grid;
		gap: 8px;
		min-width: 0;
		font-size: 1rem;
		font-weight: 700;
		color: #07135b;
	}

	.ql-input-wrap {
		position: relative;
		display: flex;
		align-items: center;
		width: 100%;
		min-width: 0;
		height: 58px;
		border: 1px solid rgba(109, 132, 171, 0.32);
		border-radius: 18px;
		background: rgba(255, 255, 255, 0.86);
		box-shadow: inset 0 1px 2px rgba(14, 39, 95, 0.04);
		transition:
			border-color 160ms ease,
			box-shadow 160ms ease;
	}

	.ql-input-wrap:focus-within {
		border-color: rgba(13, 197, 211, 0.72);
		box-shadow:
			0 0 0 4px rgba(13, 197, 211, 0.13),
			inset 0 1px 2px rgba(14, 39, 95, 0.04);
	}

	.ql-field-icon {
		display: inline-flex;
		width: 24px;
		height: 24px;
		margin-left: 20px;
		color: #72809d;
		flex: 0 0 auto;
	}

	.ql-field-icon svg,
	.ql-password-toggle svg {
		width: 100%;
		height: 100%;
	}

	.ql-input-wrap input {
		min-width: 0;
		flex: 1;
		height: 100%;
		border: 0;
		outline: 0;
		background: transparent;
		padding: 0 16px;
		font-size: 1rem;
		font-weight: 600;
		color: #061155;
	}

	.ql-input-wrap input::placeholder {
		color: #8e98ae;
		font-weight: 600;
	}

	.ql-password-toggle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 52px;
		height: 100%;
		color: #72809d;
		background: transparent;
		border: 0;
		cursor: pointer;
	}

	.ql-password-toggle svg {
		width: 22px;
		height: 22px;
	}

	.ql-submit {
		margin-top: 12px;
		width: 100%;
		height: 62px;
		border: 0;
		border-radius: 22px;
		background: linear-gradient(100deg, #0758ff 0%, #008dff 47%, #11c9ca 100%);
		color: #fff;
		font-size: 1.28rem;
		font-weight: 800;
		box-shadow: 0 1.25rem 2.35rem rgba(4, 91, 229, 0.24);
		cursor: pointer;
		transition:
			transform 160ms ease,
			box-shadow 160ms ease;
	}

	.ql-submit:hover {
		transform: translateY(-1px);
		box-shadow: 0 1.4rem 2.6rem rgba(4, 91, 229, 0.3);
	}

	.ql-mode-switch {
		margin-top: 16px;
		display: flex;
		justify-content: center;
		gap: 0.45rem;
		font-size: 0.95rem;
		color: #61708d;
	}

	.ql-mode-switch button,
	.ql-oauth button {
		border: 0;
		background: transparent;
		color: #0758ff;
		font-weight: 800;
		cursor: pointer;
	}

	.ql-oauth {
		margin-top: 1rem;
		display: grid;
		gap: 0.75rem;
	}

	.ql-oauth-divider {
		display: flex;
		align-items: center;
		gap: 1rem;
		color: #73809b;
		font-size: 0.88rem;
	}

	.ql-oauth-divider::before,
	.ql-oauth-divider::after {
		content: '';
		flex: 1;
		height: 1px;
		background: rgba(109, 132, 171, 0.2);
	}

	.ql-oauth button {
		height: 2.75rem;
		border: 1px solid rgba(109, 132, 171, 0.24);
		border-radius: 999px;
		background: rgba(255, 255, 255, 0.7);
		color: #061155;
	}

	.ql-auth-hero {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: flex-start;
		min-height: 520px;
	}

	.ql-auth-hero::before {
		content: '';
		position: absolute;
		width: min(48rem, 86%);
		aspect-ratio: 1;
		border-radius: 999px;
		background: radial-gradient(circle, rgba(5, 116, 255, 0.16), transparent 68%);
	}

	.ql-auth-hero img {
		position: relative;
		width: clamp(680px, 48vw, 860px);
		max-width: none;
		max-height: min(84vh, calc(100dvh - 148px));
		object-fit: contain;
		filter: drop-shadow(0 1.6rem 2.6rem rgba(35, 83, 151, 0.12));
	}

	.ql-auth-loading {
		min-height: 100dvh;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: #061155;
	}

	.ql-loading-title {
		font-size: 1.35rem;
		font-weight: 800;
	}

	@media (max-width: 1100px) {
		.ql-auth-content {
			grid-template-columns: minmax(0, 480px);
			justify-content: center;
		}

		.ql-auth-hero {
			display: none;
		}
	}

	@media (max-width: 640px) {
		.ql-auth-shell {
			padding: 20px;
		}

		.ql-auth-content {
			display: block;
			width: calc(100vw - 40px);
			max-width: calc(100vw - 40px);
			min-width: 0;
		}

		.ql-auth-brand {
			min-height: 64px;
		}

		.ql-auth-brand img {
			width: min(52vw, 220px);
		}

		.ql-auth-key-link {
			min-height: 38px;
			padding: 0 14px;
			font-size: 0.92rem;
		}

		.ql-auth-card {
			width: 100%;
			max-width: 100%;
			min-width: 0;
			min-height: auto;
			padding: 28px 20px;
			border-radius: 20px;
		}

		.ql-card-logo {
			width: 76px;
			height: 76px;
		}

		.ql-auth-card h1 {
			font-size: 1.35rem;
			overflow-wrap: anywhere;
		}

		.ql-input-wrap {
			height: 58px;
		}

		.ql-submit {
			height: 60px;
			border-radius: 20px;
			font-size: 1.1rem;
		}
	}
</style>
