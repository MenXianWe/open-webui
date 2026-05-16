<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';

	import { onDestroy, onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		sendSignupEmailVerificationCode,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import {
		QLCODE_LOGIN_APP_LOGO_URL,
		QLCODE_LOGIN_HERO_VISUAL_URL,
		QLCODE_LOGIN_WORDMARK_URL,
		QLCODE_TUTORIAL_URL,
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
	let emailVerificationCode = '';
	let verificationCooldown = 0;
	let verificationTimer: ReturnType<typeof setInterval> | null = null;
	let ldapUsername = '';
	let showPassword = false;
	let showConfirmPassword = false;
	let termsAccepted = false;
	let termsModalOpen = false;
	let termsInitializedKey = '';
	let selectedTermsSlug = '';

	type LoginTermsDocument = {
		id?: string;
		title: string;
		slug: string;
		content: string;
	};

	$: isSignup = mode === 'signup';
	$: isLdap = mode === 'ldap';
	$: canUsePasswordForm =
		$config?.features?.enable_login_form || $config?.features?.enable_ldap || form;
	$: canSignup = ($config?.features?.enable_signup ?? false) && !($config?.onboarding ?? false);
	$: requiresEmailVerification =
		isSignup &&
		!($config?.onboarding ?? false) &&
		($config?.features?.enable_email_verification ?? false);
	$: loginTermsConfig = $config?.login_terms ?? null;
	$: loginTermsRequired = Boolean(loginTermsConfig?.enabled);
	$: loginTermsDisplayStyle = loginTermsConfig?.display_style === 'checkbox' ? 'checkbox' : 'modal';
	$: loginTermsUpdatedAt = loginTermsConfig?.updated_at ?? '';
	$: loginTermsDocuments = (loginTermsConfig?.documents ?? []) as LoginTermsDocument[];
	$: loginTermsFingerprint = `${loginTermsUpdatedAt || 'none'}:${getTermsDocumentsFingerprint(loginTermsDocuments)}`;
	$: selectedTermsDocument =
		loginTermsDocuments.find((document) => document.slug === selectedTermsSlug) ??
		loginTermsDocuments[0] ??
		null;
	$: renderedTermsHtml = selectedTermsDocument
		? DOMPurify.sanitize(
				marked.parse(selectedTermsDocument.content || '', { async: false }) as string
			)
		: '';
	$: submitDisabled = loginTermsRequired && !termsAccepted;
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
	$: tutorialUrl = $config?.qlcode_tutorial_url || QLCODE_TUTORIAL_URL;

	function getTermsDocumentsFingerprint(documents: LoginTermsDocument[]) {
		const value = JSON.stringify(
			documents.map((document) => ({
				title: document.title,
				slug: document.slug,
				content: document.content
			}))
		);
		let hash = 0;
		for (let i = 0; i < value.length; i += 1) {
			hash = (hash * 31 + value.charCodeAt(i)) | 0;
		}
		return Math.abs(hash).toString(36);
	}

	const getTermsStorageKey = () => {
		return `qlcode-login-terms:${loginTermsFingerprint || 'default'}`;
	};

	const initializeTermsAcceptance = () => {
		if (!loginTermsRequired) {
			termsAccepted = true;
			termsModalOpen = false;
			termsInitializedKey = '';
			return;
		}

		const key = getTermsStorageKey();
		if (termsInitializedKey === key) {
			return;
		}

		termsInitializedKey = key;
		termsAccepted = localStorage.getItem(key) === 'accepted';
		selectedTermsSlug = loginTermsDocuments[0]?.slug ?? '';
		termsModalOpen = loginTermsDisplayStyle === 'modal' && !termsAccepted;
	};

	$: if (loaded) {
		initializeTermsAcceptance();
	}

	const acceptTermsHandler = () => {
		if (!loginTermsRequired) {
			termsAccepted = true;
			termsModalOpen = false;
			return;
		}

		localStorage.setItem(getTermsStorageKey(), 'accepted');
		termsAccepted = true;
		termsModalOpen = false;
	};

	const rejectTermsHandler = () => {
		if (loginTermsRequired) {
			localStorage.removeItem(getTermsStorageKey());
		}
		termsAccepted = false;
		termsModalOpen = false;
	};

	const ensureTermsAccepted = () => {
		if (!loginTermsRequired || termsAccepted) {
			return true;
		}

		if (loginTermsDisplayStyle === 'modal') {
			termsModalOpen = true;
		}
		toast.error('请先阅读并同意服务条款。');
		return false;
	};

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
		const sessionUser = await userSignIn(email, password, termsAccepted, loginTermsUpdatedAt).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation && password !== confirmPassword) {
			toast.error($i18n.t('Passwords do not match.'));
			return;
		}

		if (requiresEmailVerification && !emailVerificationCode.trim()) {
			toast.error('请输入邮箱验证码。');
			return;
		}

		const sessionUser = await userSignUp(
			name,
			email,
			password,
			generateInitialsImage(name),
			requiresEmailVerification ? emailVerificationCode.trim() : null,
			termsAccepted,
			loginTermsUpdatedAt
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const startVerificationCooldown = () => {
		verificationCooldown = 60;
		if (verificationTimer) {
			clearInterval(verificationTimer);
		}
		verificationTimer = setInterval(() => {
			verificationCooldown = Math.max(0, verificationCooldown - 1);
			if (verificationCooldown === 0 && verificationTimer) {
				clearInterval(verificationTimer);
				verificationTimer = null;
			}
		}, 1000);
	};

	const sendEmailVerificationCodeHandler = async () => {
		const normalizedEmail = email.trim();
		if (!normalizedEmail) {
			toast.error('请先输入电子邮箱。');
			return;
		}

		const res = await sendSignupEmailVerificationCode(normalizedEmail).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success('验证码已发送，请查看邮箱。');
			startVerificationCooldown();
		}
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(
			ldapUsername,
			password,
			termsAccepted,
			loginTermsUpdatedAt
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (!ensureTermsAccepted()) {
			return;
		}

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

	onDestroy(() => {
		if (verificationTimer) {
			clearInterval(verificationTimer);
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
						href={tutorialUrl}
						target="_blank"
						rel="noreferrer"
						aria-label="查看 QLCodeChat 使用教程"
					>
						使用教程
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

								{#if requiresEmailVerification}
									<label class="ql-field">
										<span>邮箱验证码</span>
										<div class="ql-input-wrap ql-code-wrap">
											<span class="ql-field-icon" aria-hidden="true">
												<svg viewBox="0 0 24 24" fill="none">
													<path
														d="M4 6h16v12H4V6Z"
														stroke="currentColor"
														stroke-width="2"
														stroke-linejoin="round"
													/>
													<path
														d="m8 12 2.4 2.4L16 9"
														stroke="currentColor"
														stroke-width="2"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											</span>
											<input
												bind:value={emailVerificationCode}
												type="text"
												inputmode="numeric"
												autocomplete="one-time-code"
												placeholder="输入邮箱验证码"
												maxlength="6"
												required
											/>
											<button
												type="button"
												class="ql-code-send"
												disabled={verificationCooldown > 0 || !email.trim()}
												on:click={sendEmailVerificationCodeHandler}
											>
												{verificationCooldown > 0 ? `${verificationCooldown}s` : '发送验证码'}
											</button>
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

								{#if loginTermsRequired}
									<div class="ql-terms-confirm">
										{#if loginTermsDisplayStyle === 'checkbox'}
											<label class="ql-terms-checkbox">
												<input type="checkbox" bind:checked={termsAccepted} />
												<span>
													我已阅读并同意
													{#each loginTermsDocuments as document, index}
														<a href={`/legal/${document.slug}`} target="_blank" rel="noreferrer">
															{document.title}
														</a>{index < loginTermsDocuments.length - 1 ? '、' : ''}
													{/each}
												</span>
											</label>
										{:else}
											<div class="ql-terms-status">
												<span>
													{termsAccepted ? '已同意当前服务条款' : '请先阅读并同意服务条款'}
													{#if loginTermsUpdatedAt}
														<small>更新日期：{loginTermsUpdatedAt}</small>
													{/if}
												</span>
												<button
													type="button"
													on:click={() => {
														termsModalOpen = true;
													}}
												>
													查看条款
												</button>
											</div>
										{/if}
									</div>
								{/if}

								<button class="ql-submit" type="submit" disabled={submitDisabled}
									>{submitText}</button
								>
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
										disabled={submitDisabled}
										on:click={() => {
											if (!ensureTermsAccepted()) {
												return;
											}
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										使用 Google 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										type="button"
										disabled={submitDisabled}
										on:click={() => {
											if (!ensureTermsAccepted()) {
												return;
											}
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										使用 Microsoft 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										type="button"
										disabled={submitDisabled}
										on:click={() => {
											if (!ensureTermsAccepted()) {
												return;
											}
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										使用 GitHub 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										type="button"
										disabled={submitDisabled}
										on:click={() => {
											if (!ensureTermsAccepted()) {
												return;
											}
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										使用 {$config?.oauth?.providers?.oidc ?? 'SSO'} 登录
									</button>
								{/if}
								{#if $config?.oauth?.providers?.feishu}
									<button
										type="button"
										disabled={submitDisabled}
										on:click={() => {
											if (!ensureTermsAccepted()) {
												return;
											}
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

			{#if termsModalOpen && loginTermsRequired}
				<div class="ql-terms-modal-backdrop" role="presentation">
					<section
						class="ql-terms-modal"
						role="dialog"
						aria-modal="true"
						aria-labelledby="ql-terms-modal-title"
					>
						<header class="ql-terms-modal-header">
							<div>
								<h2 id="ql-terms-modal-title">服务条款确认</h2>
								{#if loginTermsUpdatedAt}
									<p>更新日期：{loginTermsUpdatedAt}</p>
								{/if}
							</div>
							<button type="button" aria-label="关闭服务条款" on:click={rejectTermsHandler}>
								<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
									<path
										d="m6 6 12 12M18 6 6 18"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
									/>
								</svg>
							</button>
						</header>

						<div class="ql-terms-modal-body">
							<nav class="ql-terms-tabs" aria-label="服务条款文档">
								{#each loginTermsDocuments as document}
									<button
										type="button"
										class:selected={selectedTermsDocument?.slug === document.slug}
										on:click={() => {
											selectedTermsSlug = document.slug;
										}}
									>
										{document.title}
									</button>
								{/each}
							</nav>

							<article class="ql-terms-markdown">
								{#if selectedTermsDocument}
									{@html renderedTermsHtml}
								{:else}
									<p>管理员尚未配置服务条款文档。</p>
								{/if}
							</article>
						</div>

						<footer class="ql-terms-modal-footer">
							<button type="button" class="ql-terms-secondary" on:click={rejectTermsHandler}>
								暂不同意
							</button>
							<button type="button" class="ql-terms-primary" on:click={acceptTermsHandler}>
								同意并继续
							</button>
						</footer>
					</section>
				</div>
			{/if}
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
		padding: clamp(12px, 1.55vw, 28px) clamp(18px, 2vw, 36px) clamp(20px, 2.6vw, 44px);
		display: flex;
		flex-direction: column;
	}

	.ql-auth-brand {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		min-height: 56px;
	}

	.ql-auth-brand img {
		width: clamp(170px, 13vw, 260px);
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
		background: #075cf8;
		color: #ffffff;
		font-size: 1rem;
		font-weight: 800;
		line-height: 1;
		text-decoration: none;
		box-shadow: 0 0.75rem 1.8rem rgba(7, 92, 248, 0.24);
		animation: ql-auth-link-pulse 1.5s ease-in-out infinite;
		transition:
			border-color 160ms ease,
			background-color 160ms ease,
			color 160ms ease,
			box-shadow 160ms ease,
			transform 160ms ease;
	}

	.ql-auth-key-link:hover,
	.ql-auth-key-link:focus-visible {
		border-color: #003bc0;
		background: #003bc0;
		color: #ffffff;
		box-shadow: 0 0.9rem 2rem rgba(7, 92, 248, 0.32);
		transform: translateY(-1px);
	}

	@keyframes ql-auth-link-pulse {
		0%,
		100% {
			box-shadow:
				0 0.75rem 1.8rem rgba(7, 92, 248, 0.22),
				0 0 0 0 rgba(17, 201, 202, 0.42);
		}

		50% {
			box-shadow:
				0 0.95rem 2.25rem rgba(7, 92, 248, 0.34),
				0 0 0 8px rgba(17, 201, 202, 0);
		}
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
		padding: 0 0 clamp(76px, 10vh, 140px);
		transform: translateY(clamp(-72px, -6vh, -34px));
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

	.ql-code-wrap input {
		padding-right: 10px;
	}

	.ql-code-send {
		flex: 0 0 auto;
		min-width: 104px;
		height: 42px;
		margin-right: 8px;
		border: 0;
		border-radius: 14px;
		background: #075cf8;
		color: #ffffff;
		font-size: 0.95rem;
		font-weight: 800;
		cursor: pointer;
		transition:
			background-color 160ms ease,
			transform 160ms ease,
			opacity 160ms ease;
	}

	.ql-code-send:hover:not(:disabled) {
		background: #003bc0;
		transform: translateY(-1px);
	}

	.ql-code-send:disabled {
		cursor: not-allowed;
		opacity: 0.55;
	}

	.ql-terms-confirm {
		border: 1px solid rgba(7, 88, 255, 0.18);
		border-radius: 18px;
		background: rgba(245, 249, 255, 0.86);
		padding: 14px 16px;
	}

	.ql-terms-checkbox {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		color: #283966;
		font-size: 0.95rem;
		font-weight: 700;
		line-height: 1.55;
	}

	.ql-terms-checkbox input {
		margin-top: 4px;
		width: 18px;
		height: 18px;
		accent-color: #075cf8;
		flex: 0 0 auto;
	}

	.ql-terms-checkbox a,
	.ql-terms-status button {
		color: #0758ff;
		font-weight: 900;
		text-decoration: none;
	}

	.ql-terms-checkbox a:hover,
	.ql-terms-status button:hover {
		color: #003bc0;
	}

	.ql-terms-status {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}

	.ql-terms-status span {
		display: grid;
		gap: 3px;
		color: #07135b;
		font-size: 0.95rem;
		font-weight: 800;
	}

	.ql-terms-status small {
		color: #5f6f91;
		font-size: 0.78rem;
		font-weight: 700;
	}

	.ql-terms-status button {
		flex: 0 0 auto;
		border: 0;
		background: transparent;
		cursor: pointer;
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

	.ql-submit:disabled,
	.ql-oauth button:disabled {
		cursor: not-allowed;
		opacity: 0.55;
		transform: none;
		box-shadow: none;
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

	.ql-terms-modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 20;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 24px;
		background: rgba(5, 14, 87, 0.5);
	}

	.ql-terms-modal {
		width: min(920px, 100%);
		max-height: min(760px, calc(100dvh - 48px));
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border-radius: 24px;
		background: #ffffff;
		border: 1px solid rgba(109, 132, 171, 0.22);
		box-shadow: 0 2rem 5rem rgba(4, 16, 58, 0.22);
	}

	.ql-terms-modal-header,
	.ql-terms-modal-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 20px 24px;
		border-bottom: 1px solid rgba(109, 132, 171, 0.16);
	}

	.ql-terms-modal-header h2 {
		margin: 0;
		color: #061155;
		font-size: 1.35rem;
		font-weight: 900;
		letter-spacing: 0;
	}

	.ql-terms-modal-header p {
		margin: 6px 0 0;
		color: #5f6f91;
		font-size: 0.92rem;
		font-weight: 700;
	}

	.ql-terms-modal-header button {
		width: 40px;
		height: 40px;
		border: 1px solid rgba(109, 132, 171, 0.24);
		border-radius: 999px;
		background: #ffffff;
		color: #33415f;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.ql-terms-modal-header svg {
		width: 20px;
		height: 20px;
	}

	.ql-terms-modal-body {
		min-height: 0;
		display: grid;
		grid-template-columns: 220px minmax(0, 1fr);
		flex: 1;
	}

	.ql-terms-tabs {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 18px;
		border-right: 1px solid rgba(109, 132, 171, 0.16);
		background: #f7faff;
	}

	.ql-terms-tabs button {
		min-height: 42px;
		border: 1px solid transparent;
		border-radius: 14px;
		background: transparent;
		color: #33415f;
		font-size: 0.95rem;
		font-weight: 800;
		text-align: left;
		padding: 0 14px;
		cursor: pointer;
	}

	.ql-terms-tabs button.selected {
		border-color: rgba(7, 88, 255, 0.2);
		background: #ffffff;
		color: #0758ff;
		box-shadow: 0 0.75rem 1.6rem rgba(18, 66, 160, 0.08);
	}

	.ql-terms-markdown {
		min-height: 0;
		overflow: auto;
		padding: 24px 28px 34px;
		color: #17213d;
		font-size: 1rem;
		line-height: 1.82;
	}

	.ql-terms-markdown :global(h1),
	.ql-terms-markdown :global(h2),
	.ql-terms-markdown :global(h3) {
		color: #061155;
		letter-spacing: 0;
	}

	.ql-terms-markdown :global(h1) {
		margin: 0 0 18px;
		font-size: 1.65rem;
		font-weight: 900;
	}

	.ql-terms-markdown :global(h2) {
		margin: 28px 0 10px;
		font-size: 1.18rem;
		font-weight: 900;
	}

	.ql-terms-markdown :global(p) {
		margin: 0 0 14px;
	}

	.ql-terms-markdown :global(ul),
	.ql-terms-markdown :global(ol) {
		margin: 0 0 14px 1.4rem;
		padding: 0;
	}

	.ql-terms-modal-footer {
		justify-content: flex-end;
		border-top: 1px solid rgba(109, 132, 171, 0.16);
		border-bottom: 0;
	}

	.ql-terms-secondary,
	.ql-terms-primary {
		min-width: 120px;
		height: 44px;
		border-radius: 14px;
		font-size: 0.98rem;
		font-weight: 900;
		cursor: pointer;
	}

	.ql-terms-secondary {
		border: 1px solid rgba(109, 132, 171, 0.28);
		background: #ffffff;
		color: #33415f;
	}

	.ql-terms-primary {
		border: 0;
		background: #075cf8;
		color: #ffffff;
		box-shadow: 0 0.8rem 1.8rem rgba(7, 92, 248, 0.22);
	}

	@media (max-width: 1100px) {
		.ql-auth-content {
			grid-template-columns: minmax(0, 480px);
			justify-content: center;
			padding-bottom: clamp(44px, 8vh, 88px);
			transform: translateY(clamp(-44px, -5vh, -24px));
		}

		.ql-auth-hero {
			display: none;
		}
	}

	@media (max-width: 640px) {
		.ql-auth-shell {
			padding: 14px 16px 20px;
		}

		.ql-auth-content {
			display: block;
			width: calc(100vw - 32px);
			max-width: calc(100vw - 32px);
			min-width: 0;
			padding-bottom: 24px;
			transform: none;
		}

		.ql-auth-brand {
			min-height: 52px;
		}

		.ql-auth-brand img {
			width: min(42vw, 172px);
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

		.ql-code-send {
			min-width: 88px;
			padding: 0 10px;
			font-size: 0.82rem;
		}

		.ql-terms-modal-backdrop {
			padding: 14px;
		}

		.ql-terms-modal {
			max-height: calc(100dvh - 28px);
			border-radius: 20px;
		}

		.ql-terms-modal-body {
			grid-template-columns: minmax(0, 1fr);
		}

		.ql-terms-tabs {
			flex-direction: row;
			overflow-x: auto;
			border-right: 0;
			border-bottom: 1px solid rgba(109, 132, 171, 0.16);
		}

		.ql-terms-tabs button {
			flex: 0 0 auto;
			white-space: nowrap;
		}

		.ql-terms-markdown {
			padding: 20px;
			font-size: 0.95rem;
		}
	}
</style>
