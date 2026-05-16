<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { getBackendConfig, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		testSmtpEmail,
		updateAdminConfig,
		updateLdapConfig,
		updateLdapServer
	} from '$lib/apis/auths';
	import { getBanners, setBanners } from '$lib/apis/configs';
	import { getGroups } from '$lib/apis/groups';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { banners as _banners, config } from '$lib/stores';
	import type { Banner } from '$lib/types';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Banners from './Interface/Banners.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let adminConfig: any = null;
	let webhookUrl = '';
	let smtpTestRecipientEmail = '';
	let groups: any[] = [];

	let banners: Banner[] = [];

	type LoginTermsDocument = {
		id: string;
		title: string;
		slug: string;
		content: string;
	};

	// LDAP
	let ENABLE_LDAP = false;
	let LDAP_SERVER = {
		label: '',
		host: '',
		port: '',
		attribute_for_mail: 'mail',
		attribute_for_username: 'uid',
		app_dn: '',
		app_dn_password: '',
		search_base: '',
		search_filters: '',
		use_tls: false,
		certificate_path: '',
		ciphers: ''
	};

	const normalizeTermsSlug = (value: string) => {
		return (
			value
				.trim()
				.toLowerCase()
				.replace(/[^a-z0-9-]+/g, '-')
				.replace(/^-+|-+$/g, '') || 'terms'
		);
	};

	const normalizeAdminConfig = (value: any) => {
		const documents = Array.isArray(value?.LOGIN_TERMS_DOCUMENTS)
			? value.LOGIN_TERMS_DOCUMENTS.map((document, index) => ({
					id: document.id || uuidv4(),
					title: document.title || `文档 ${index + 1}`,
					slug: normalizeTermsSlug(document.slug || document.title || `document-${index + 1}`),
					content: document.content || ''
				}))
			: [];

		return {
			...value,
			SMTP_PASSWORD: '',
			LOGIN_TERMS_DISPLAY_STYLE:
				value?.LOGIN_TERMS_DISPLAY_STYLE === 'checkbox' ? 'checkbox' : 'modal',
			LOGIN_TERMS_UPDATED_AT: (value?.LOGIN_TERMS_UPDATED_AT || '2026-03-31').replace(/\//g, '-'),
			LOGIN_TERMS_DOCUMENTS: documents
		};
	};

	const addLoginTermsDocument = () => {
		const nextIndex = (adminConfig.LOGIN_TERMS_DOCUMENTS?.length ?? 0) + 1;
		adminConfig.LOGIN_TERMS_DOCUMENTS = [
			...(adminConfig.LOGIN_TERMS_DOCUMENTS ?? []),
			{
				id: uuidv4(),
				title: `新文档 ${nextIndex}`,
				slug: `document-${nextIndex}`,
				content: `# 新文档 ${nextIndex}\n\n请在这里填写 Markdown 内容。`
			}
		];
	};

	const removeLoginTermsDocument = (documentId: string) => {
		adminConfig.LOGIN_TERMS_DOCUMENTS = (adminConfig.LOGIN_TERMS_DOCUMENTS ?? []).filter(
			(document) => document.id !== documentId
		);
	};

	const updateLdapServerHandler = async () => {
		if (!ENABLE_LDAP) return;
		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('LDAP server updated'));
		}
	};

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};

	const saveAdminConfigOnly = async () => {
		const res = await updateAdminConfig(localStorage.token, adminConfig);
		if (res) {
			adminConfig = normalizeAdminConfig({ ...adminConfig, ...res });
		}
		return res;
	};

	const testSmtpHandler = async (recipientEmail: string) => {
		const saved = await saveAdminConfigOnly().catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!saved) {
			return;
		}

		const target = recipientEmail.trim();
		if (!target) {
			toast.error('请先填写测试收件人邮箱');
			return;
		}

		const res = await testSmtpEmail(localStorage.token, target).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success('测试邮件已发送');
		}
	};

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		const res = await updateAdminConfig(localStorage.token, adminConfig);
		await updateLdapConfig(localStorage.token, ENABLE_LDAP);
		await updateLdapServerHandler();

		await updateBanners();

		await config.set(await getBackendConfig());

		if (res) {
			adminConfig = normalizeAdminConfig({ ...adminConfig, ...res });
			saveHandler();
		} else {
			toast.error($i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		await Promise.all([
			(async () => {
				adminConfig = normalizeAdminConfig(await getAdminConfig(localStorage.token));
			})(),

			(async () => {
				webhookUrl = await getWebhookUrl(localStorage.token);
			})(),
			(async () => {
				LDAP_SERVER = await getLdapServer(localStorage.token);
			})(),
			(async () => {
				groups = await getGroups(localStorage.token);
			})()
		]);

		const ldapConfig = await getLdapConfig(localStorage.token);
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;

		banners = await getBanners(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if adminConfig !== null}
			<div class="">
				<div class="mb-3.5">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium flex space-x-2 items-center">
							<div>
								{$i18n.t('Version')}
							</div>
						</div>
						<div class="flex w-full justify-between items-center">
							<div class="flex flex-col text-xs text-gray-700 dark:text-gray-200">
								<div class="flex gap-1">
									<Tooltip content={WEBUI_BUILD_HASH}>
										v{WEBUI_VERSION}
									</Tooltip>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Authentication')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Default User Role')}</div>
						<div class="flex items-center relative">
							<select
								class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
								bind:value={adminConfig.DEFAULT_USER_ROLE}
								placeholder={$i18n.t('Select a role')}
							>
								<option value="pending">{$i18n.t('pending')}</option>
								<option value="user">{$i18n.t('user')}</option>
								<option value="admin">{$i18n.t('admin')}</option>
							</select>
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Default Group')}</div>
						<div class="flex items-center relative">
							<select
								class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
								bind:value={adminConfig.DEFAULT_GROUP_ID}
								placeholder={$i18n.t('Select a group')}
							>
								<option value={''}>None</option>
								{#each groups as group}
									<option value={group.id}>{group.name}</option>
								{/each}
							</select>
						</div>
					</div>

					<div class=" mb-2.5 flex w-full justify-between pr-2">
						<div class=" self-center text-xs font-medium">{$i18n.t('Enable New Sign Ups')}</div>

						<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Show Admin Details in Account Pending Overlay')}
						</div>

						<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
					</div>

					{#if adminConfig.SHOW_ADMIN_DETAILS}
						<div class="mb-2.5 w-full justify-between">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">{$i18n.t('Admin Contact Email')}</div>
							</div>

							<div class="flex mt-2 space-x-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="email"
									placeholder={$i18n.t('Leave empty to use first admin user')}
									bind:value={adminConfig.ADMIN_EMAIL}
								/>
							</div>
						</div>
					{/if}

					<div class="mb-2.5">
						<div class=" self-center text-xs font-medium mb-2">
							{$i18n.t('Pending User Overlay Title')}
						</div>
						<Textarea
							placeholder={$i18n.t(
								'Enter a title for the pending user info overlay. Leave empty for default.'
							)}
							bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
						/>
					</div>

					<div class="mb-2.5">
						<div class=" self-center text-xs font-medium mb-2">
							{$i18n.t('Pending User Overlay Content')}
						</div>
						<Textarea
							placeholder={$i18n.t(
								'Enter content for the pending user info overlay. Leave empty for default.'
							)}
							bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
						/>
					</div>

					<div class="mb-2.5 flex w-full justify-between pr-2">
						<div class=" self-center text-xs font-medium">{$i18n.t('Enable API Keys')}</div>

						<Switch bind:state={adminConfig.ENABLE_API_KEYS} />
					</div>

					{#if adminConfig?.ENABLE_API_KEYS}
						<div class="mb-2.5 flex w-full justify-between pr-2">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('API Key Endpoint Restrictions')}
							</div>

							<Switch bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS} />
						</div>

						{#if adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
							<div class=" flex w-full flex-col pr-2 mb-2.5">
								<div class=" text-xs font-medium">
									{$i18n.t('Allowed Endpoints')}
								</div>

								<input
									class="w-full mt-1 text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
									bind:value={adminConfig.API_KEYS_ALLOWED_ENDPOINTS}
								/>

								<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
									<span
										>{$i18n.t(
											'Configure only endpoints that should be available to API keys.'
										)}</span
									>
								</div>
							</div>
						{/if}
					{/if}

					<div class=" mb-2.5 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('JWT Expiration')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={`e.g.) "30m","1h", "10d". `}
								bind:value={adminConfig.JWT_EXPIRES_IN}
							/>
						</div>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Valid time units:')}
							<span class=" text-gray-300 font-medium"
								>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
							>
						</div>

						{#if adminConfig.JWT_EXPIRES_IN === '-1'}
							<div class="mt-2 text-xs">
								<div
									class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-3 py-2"
								>
									<div>
										<span class=" font-medium">{$i18n.t('Warning')}:</span>
										<span>{$i18n.t('No expiration can pose security risks.')}</span>
									</div>
								</div>
							</div>
						{/if}
					</div>

					<div class=" space-y-3">
						<div class="mt-2 space-y-2 pr-1.5">
							<div class="flex justify-between items-center text-sm">
								<div class="  font-medium">{$i18n.t('LDAP')}</div>

								<div class="mt-1">
									<Switch bind:state={ENABLE_LDAP} />
								</div>
							</div>

							{#if ENABLE_LDAP}
								<div class="flex flex-col gap-1">
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Label')}
											</div>
											<input
												class="w-full bg-transparent outline-hidden py-0.5"
												required
												placeholder={$i18n.t('Enter server label')}
												bind:value={LDAP_SERVER.label}
											/>
										</div>
										<div class="w-full"></div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Host')}
											</div>
											<input
												class="w-full bg-transparent outline-hidden py-0.5"
												required
												placeholder={$i18n.t('Enter server host')}
												bind:value={LDAP_SERVER.host}
											/>
										</div>
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Port')}
											</div>
											<Tooltip
												placement="top-start"
												content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
												className="w-full"
											>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													type="number"
													placeholder={$i18n.t('Enter server port')}
													bind:value={LDAP_SERVER.port}
												/>
											</Tooltip>
										</div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Application DN')}
											</div>
											<Tooltip
												content={$i18n.t('The Application Account DN you bind with for search')}
												placement="top-start"
											>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													placeholder={$i18n.t('Enter Application DN')}
													bind:value={LDAP_SERVER.app_dn}
												/>
											</Tooltip>
										</div>
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Application DN Password')}
											</div>
											<SensitiveInput
												placeholder={$i18n.t('Enter Application DN Password')}
												required={false}
												bind:value={LDAP_SERVER.app_dn_password}
											/>
										</div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Attribute for Mail')}
											</div>
											<Tooltip
												content={$i18n.t(
													'The LDAP attribute that maps to the mail that users use to sign in.'
												)}
												placement="top-start"
											>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													required
													placeholder={$i18n.t('Example: mail')}
													bind:value={LDAP_SERVER.attribute_for_mail}
												/>
											</Tooltip>
										</div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Attribute for Username')}
											</div>
											<Tooltip
												content={$i18n.t(
													'The LDAP attribute that maps to the username that users use to sign in.'
												)}
												placement="top-start"
											>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													required
													placeholder={$i18n.t(
														'Example: sAMAccountName or uid or userPrincipalName'
													)}
													bind:value={LDAP_SERVER.attribute_for_username}
												/>
											</Tooltip>
										</div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Search Base')}
											</div>
											<Tooltip
												content={$i18n.t('The base to search for users')}
												placement="top-start"
											>
												<input
													class="w-full bg-transparent outline-hidden py-0.5"
													required
													placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
													bind:value={LDAP_SERVER.search_base}
												/>
											</Tooltip>
										</div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Search Filters')}
											</div>
											<input
												class="w-full bg-transparent outline-hidden py-0.5"
												placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
												bind:value={LDAP_SERVER.search_filters}
											/>
										</div>
									</div>
									<div class="text-xs text-gray-400 dark:text-gray-500">
										<a
											class=" text-gray-300 font-medium underline"
											href="https://ldap.com/ldap-filters/"
											target="_blank"
										>
											{$i18n.t('Click here for filter guides.')}
										</a>
									</div>
									<div>
										<div class="flex justify-between items-center text-sm">
											<div class="  font-medium">{$i18n.t('TLS')}</div>

											<div class="mt-1">
												<Switch bind:state={LDAP_SERVER.use_tls} />
											</div>
										</div>
										{#if LDAP_SERVER.use_tls}
											<div class="flex w-full gap-2">
												<div class="w-full">
													<div class=" self-center text-xs font-medium min-w-fit mb-1 mt-1">
														{$i18n.t('Certificate Path')}
													</div>
													<input
														class="w-full bg-transparent outline-hidden py-0.5"
														placeholder={$i18n.t('Enter certificate path')}
														bind:value={LDAP_SERVER.certificate_path}
													/>
												</div>
											</div>
											<div class="flex justify-between items-center text-xs">
												<div class=" font-medium">{$i18n.t('Validate certificate')}</div>

												<div class="mt-1">
													<Switch bind:state={LDAP_SERVER.validate_cert} />
												</div>
											</div>
											<div class="flex w-full gap-2">
												<div class="w-full">
													<div class=" self-center text-xs font-medium min-w-fit mb-1">
														{$i18n.t('Ciphers')}
													</div>
													<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
														<input
															class="w-full bg-transparent outline-hidden py-0.5"
															placeholder={$i18n.t('Example: ALL')}
															bind:value={LDAP_SERVER.ciphers}
														/>
													</Tooltip>
												</div>
												<div class="w-full"></div>
											</div>
										{/if}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Features')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Enable Community Sharing')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">{$i18n.t('Enable Message Rating')}</div>

						<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Folders')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_FOLDERS} />
					</div>

					{#if adminConfig.ENABLE_FOLDERS}
						<div class="mb-2.5 w-full justify-between">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Folder Max File Count')}
								</div>
							</div>

							<div class="flex mt-2 space-x-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="number"
									min="0"
									placeholder={$i18n.t('Leave empty for unlimited')}
									bind:value={adminConfig.FOLDER_MAX_FILE_COUNT}
								/>
							</div>

							<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Maximum number of files allowed per folder.')}
							</div>
						</div>
					{/if}

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Memories')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_MEMORIES} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Notes')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_NOTES} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Channels')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Calendar')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_CALENDAR} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Automations')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_AUTOMATIONS} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('User Webhooks')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('User Status')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_USER_STATUS} />
					</div>

					<div class="mb-2.5">
						<div class=" self-center text-xs font-medium mb-2">
							{$i18n.t('Response Watermark')}
						</div>
						<Textarea
							placeholder={$i18n.t('Enter a watermark for the response. Leave empty for none.')}
							bind:value={adminConfig.RESPONSE_WATERMARK}
						/>
					</div>

					<div class="mb-2.5 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('QLCodeChat URL')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={`e.g.) "http://localhost:3000"`}
								bind:value={adminConfig.WEBUI_URL}
							/>
						</div>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t(
								'Enter the public URL of your QLCodeChat deployment. This URL will be used to generate links in the notifications.'
							)}
						</div>
					</div>

					<div class="mb-2.5 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">使用教程 URL</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="url"
								placeholder="https://qlcodeapi.com/"
								bind:value={adminConfig.QLCODE_TUTORIAL_URL}
							/>
						</div>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							登录页右上角“使用教程”按钮会跳转到这个地址。
						</div>
					</div>

					<div
						class="mb-3.5 w-full overflow-hidden rounded-xl border border-gray-100 dark:border-gray-850"
					>
						<div
							class="flex items-start justify-between gap-3 border-b border-gray-100 px-4 py-3 dark:border-gray-850"
						>
							<div>
								<div class="text-sm font-semibold text-gray-900 dark:text-gray-50">
									登录条款确认
								</div>
								<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									控制登录页是否要求用户先阅读并同意服务条款、隐私政策或其他 Markdown 文档。
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{adminConfig.LOGIN_TERMS_ENABLED ? '已启用' : '已关闭'}
								</span>
								<Switch bind:state={adminConfig.LOGIN_TERMS_ENABLED} />
							</div>
						</div>

						<div class="grid gap-4 px-4 py-3 md:grid-cols-[1fr_220px]">
							<div>
								<div class="mb-2 text-xs font-medium text-gray-700 dark:text-gray-300">
									展示形式
								</div>
								<div
									class="grid grid-cols-2 overflow-hidden rounded-lg bg-gray-100 p-1 dark:bg-gray-850"
								>
									<button
										type="button"
										class="rounded-md px-3 py-2 text-xs font-semibold transition {adminConfig.LOGIN_TERMS_DISPLAY_STYLE ===
										'modal'
											? 'bg-white text-teal-700 shadow-sm dark:bg-gray-700 dark:text-teal-200'
											: 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}"
										on:click={() => {
											adminConfig.LOGIN_TERMS_DISPLAY_STYLE = 'modal';
										}}
									>
										弹窗
									</button>
									<button
										type="button"
										class="rounded-md px-3 py-2 text-xs font-semibold transition {adminConfig.LOGIN_TERMS_DISPLAY_STYLE ===
										'checkbox'
											? 'bg-white text-teal-700 shadow-sm dark:bg-gray-700 dark:text-teal-200'
											: 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}"
										on:click={() => {
											adminConfig.LOGIN_TERMS_DISPLAY_STYLE = 'checkbox';
										}}
									>
										复选框
									</button>
								</div>
								<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
									弹窗会在登录页打开；复选框会直接显示在登录按钮上方。
								</div>
							</div>

							<label class="block">
								<div class="mb-2 text-xs font-medium text-gray-700 dark:text-gray-300">
									条款更新日期
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="date"
									bind:value={adminConfig.LOGIN_TERMS_UPDATED_AT}
								/>
								<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
									日期或文档内容变更后，用户需要重新同意。
								</div>
							</label>
						</div>

						<div class="border-t border-gray-100 px-4 py-3 dark:border-gray-850">
							<div class="mb-3 flex items-center justify-between gap-3">
								<div>
									<div class="text-xs font-semibold text-gray-800 dark:text-gray-100">协议文档</div>
									<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
										文档名称可自定义，内容按 Markdown 保存。
									</div>
								</div>
								<button
									class="shrink-0 rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-700"
									type="button"
									on:click={addLoginTermsDocument}
								>
									添加文档
								</button>
							</div>

							<div class="space-y-3">
								{#each adminConfig.LOGIN_TERMS_DOCUMENTS as document}
									<div class="rounded-xl border border-gray-100 p-3 dark:border-gray-850">
										<div class="mb-3 flex items-start justify-between gap-3">
											<div>
												<div class="text-sm font-semibold text-gray-900 dark:text-gray-50">
													{document.title || '未命名文档'}
												</div>
												<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
													/legal/{document.slug || 'terms'}
												</div>
											</div>
											<button
												class="rounded-lg px-2 py-1 text-xs font-semibold text-red-500 transition hover:bg-red-50 dark:hover:bg-red-950/30"
												type="button"
												on:click={() => {
													removeLoginTermsDocument(document.id);
												}}
											>
												删除
											</button>
										</div>

										<div class="grid gap-3 md:grid-cols-2">
											<label class="block">
												<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
													文档名称
												</div>
												<input
													class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
													type="text"
													bind:value={document.title}
												/>
											</label>

											<label class="block">
												<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
													路由标识
												</div>
												<div
													class="flex overflow-hidden rounded-lg border border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-850"
												>
													<span
														class="flex items-center border-r border-gray-100 px-3 text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400"
													>
														/legal/
													</span>
													<input
														class="min-w-0 flex-1 bg-transparent px-4 py-2 text-sm outline-hidden dark:text-gray-100"
														type="text"
														bind:value={document.slug}
														on:blur={() => {
															document.slug = normalizeTermsSlug(document.slug);
														}}
													/>
												</div>
											</label>
										</div>

										<label class="mt-3 block">
											<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
												Markdown 内容
											</div>
											<textarea
												class="min-h-48 w-full resize-y rounded-xl bg-gray-50 px-4 py-3 font-mono text-sm leading-6 outline-hidden dark:bg-gray-850 dark:text-gray-100"
												bind:value={document.content}
											/>
										</label>
									</div>
								{/each}
							</div>
						</div>
					</div>

					<div
						class="mb-3.5 w-full overflow-hidden rounded-xl border border-gray-100 dark:border-gray-850"
					>
						<div
							class="flex items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 dark:border-gray-850"
						>
							<div>
								<div class="text-sm font-semibold text-gray-900 dark:text-gray-50">SMTP 设置</div>
								<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									配置用于发送注册邮箱验证码的邮件服务
								</div>
							</div>

							<button
								class="shrink-0 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-800 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-100 dark:hover:bg-gray-850"
								type="button"
								on:click={() => {
									testSmtpHandler(adminConfig.SMTP_FROM_EMAIL || adminConfig.ADMIN_EMAIL || '');
								}}
							>
								测试连接
							</button>
						</div>

						<div class="grid gap-3 px-4 py-3 md:grid-cols-2">
							<label class="block">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									SMTP 主机
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="text"
									placeholder="smtpdm.aliyun.com"
									bind:value={adminConfig.SMTP_HOST}
								/>
							</label>

							<label class="block">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									SMTP 端口
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="number"
									min="1"
									max="65535"
									placeholder="465"
									bind:value={adminConfig.SMTP_PORT}
								/>
							</label>

							<label class="block">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									SMTP 用户名
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="text"
									placeholder="no-reply@mail.qlcodeapi.com"
									bind:value={adminConfig.SMTP_USERNAME}
								/>
							</label>

							<label class="block">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									SMTP 密码
								</div>
								<SensitiveInput
									id="smtp-password"
									bind:value={adminConfig.SMTP_PASSWORD}
									placeholder={adminConfig.SMTP_PASSWORD_CONFIGURED
										? '留空以保留当前密码'
										: '请输入 SMTP 密码'}
									required={false}
									outerClassName="flex w-full rounded-lg bg-gray-50 px-4 py-2 dark:bg-gray-850"
									inputClassName="w-full bg-transparent text-sm dark:text-gray-100"
									showButtonClassName="pl-2 text-gray-600 transition hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
								/>
								{#if adminConfig.SMTP_PASSWORD_CONFIGURED}
									<div class="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
										密码已配置，留空将保留当前值。
									</div>
								{/if}
							</label>

							<label class="block">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									发件人邮箱
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="email"
									placeholder="no-reply@mail.qlcodeapi.com"
									bind:value={adminConfig.SMTP_FROM_EMAIL}
								/>
							</label>

							<label class="block">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									发件人名称
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="text"
									placeholder="QLCodeChat"
									bind:value={adminConfig.SMTP_FROM_NAME}
								/>
							</label>
						</div>

						<div
							class="flex items-center justify-between border-t border-gray-100 px-4 py-3 dark:border-gray-850"
						>
							<div>
								<div class="text-xs font-semibold text-gray-800 dark:text-gray-100">
									启用注册邮箱验证码
								</div>
								<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									开启后，新用户注册需要先通过邮箱验证码。
								</div>
							</div>
							<Switch bind:state={adminConfig.ENABLE_EMAIL_VERIFICATION} />
						</div>

						<div
							class="flex items-center justify-between border-t border-gray-100 px-4 py-3 dark:border-gray-850"
						>
							<div>
								<div class="text-xs font-semibold text-gray-800 dark:text-gray-100">使用 TLS</div>
								<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									为 SMTP 连接启用 TLS 加密。
								</div>
							</div>
							<Switch bind:state={adminConfig.SMTP_USE_TLS} />
						</div>
					</div>

					<div
						class="mb-3.5 w-full overflow-hidden rounded-xl border border-gray-100 dark:border-gray-850"
					>
						<div class="border-b border-gray-100 px-4 py-3 dark:border-gray-850">
							<div class="text-sm font-semibold text-gray-900 dark:text-gray-50">发送测试邮件</div>
							<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
								发送测试邮件以验证 SMTP 配置
							</div>
						</div>

						<div class="flex items-end gap-3 px-4 py-3">
							<label class="min-w-0 flex-1">
								<div class="mb-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
									收件人邮箱
								</div>
								<input
									class="w-full rounded-lg bg-gray-50 px-4 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									type="email"
									placeholder="test@example.com"
									bind:value={smtpTestRecipientEmail}
								/>
							</label>
							<button
								class="shrink-0 rounded-lg border border-gray-200 px-3.5 py-2 text-xs font-medium text-gray-800 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:text-gray-100 dark:hover:bg-gray-850"
								type="button"
								disabled={!smtpTestRecipientEmail.trim()}
								on:click={() => {
									testSmtpHandler(smtpTestRecipientEmail);
								}}
							>
								发送测试邮件
							</button>
						</div>
					</div>

					<div class=" w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Webhook URL')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={`https://example.com/webhook`}
								bind:value={webhookUrl}
							/>
						</div>
					</div>
				</div>

				<div class="mb-3.5">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('UI')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs">
								{$i18n.t('Banners')}
							</div>

							<button
								class="p-1 px-3 text-xs flex rounded-sm transition"
								type="button"
								on:click={() => {
									if (banners.length === 0 || banners.at(-1).content !== '') {
										banners = [
											...banners,
											{
												id: uuidv4(),
												type: '',
												title: '',
												content: '',
												dismissible: true,
												timestamp: Math.floor(Date.now() / 1000)
											}
										];
									}
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
									/>
								</svg>
							</button>
						</div>

						<Banners bind:banners />
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
