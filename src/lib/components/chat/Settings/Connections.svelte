<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { QLCODE_API_BASE_URL } from '$lib/constants';

	const i18n = getContext<any>('i18n');

	import { settings } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Connection from './Connections/Connection.svelte';

	export let saveSettings: Function;

	type DirectConnectionsConfig = {
		OPENAI_API_BASE_URLS: string[];
		OPENAI_API_KEYS: string[];
		OPENAI_API_CONFIGS: Record<string, any>;
	};

	let config: DirectConnectionsConfig | null = null;

	const getQLCodeAPIKey = (directConnections: Partial<DirectConnectionsConfig> | null | undefined) => {
		const urls = directConnections?.OPENAI_API_BASE_URLS ?? [];
		const keys = directConnections?.OPENAI_API_KEYS ?? [];
		const fixedIdx = urls.findIndex((url: string) => url?.replace(/\/$/, '') === QLCODE_API_BASE_URL);
		return fixedIdx >= 0 ? (keys[fixedIdx] ?? '') : (keys[0] ?? '');
	};

	const updateHandler = async () => {
		await saveSettings({
			directConnections: config
		});
	};

	onMount(async () => {
		const key = getQLCodeAPIKey($settings?.directConnections);
		config = {
			OPENAI_API_BASE_URLS: [QLCODE_API_BASE_URL],
			OPENAI_API_KEYS: [key],
			OPENAI_API_CONFIGS: {
				0: {
					enable: true,
					auth_type: 'bearer',
					connection_type: 'external'
				}
			}
		};
	});
</script>

<form
	id="tab-connections"
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if config !== null}
			<div class="">
				<div class="pr-1.5">
					<div class="">
						<div class="flex justify-between items-center mb-0.5">
							<div class="font-medium">{$i18n.t('QLCodeAPI Connection')}</div>
						</div>

						<div class="flex flex-col gap-1.5">
							<Connection
								url={QLCODE_API_BASE_URL}
								bind:key={config.OPENAI_API_KEYS[0]}
								onSubmit={() => {
									updateHandler();
								}}
							/>
						</div>
					</div>

					<div class="my-1.5">
						<div
							class="text-xs {($settings?.highContrastMode ?? false)
								? 'text-gray-800 dark:text-gray-100'
								: 'text-gray-500'}"
						>
							{$i18n.t(
								'QLCodeChat uses the fixed QLCodeAPI endpoint. Enter only your API key.'
							)}
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
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
