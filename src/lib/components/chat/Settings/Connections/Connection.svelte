<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext<any>('i18n');

	import { settings } from '$lib/stores';
	import { QLCODE_API_PORTAL_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	export let onSubmit = (_connection: { url: string; key: string }) => {};

	export let url = '';
	export let key = '';
</script>

<div class="flex w-full flex-col gap-2">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`QLCodeChat will use "{{url}}" for OpenAI-compatible requests.`, {
			url
		})}
		placement="top-start"
	>
		<div class="flex w-full gap-2">
			<div class="flex-1 relative">
				<input
					class={`w-full bg-transparent ${($settings?.highContrastMode ?? false) ? '' : 'outline-hidden'} text-gray-500 dark:text-gray-400`}
					placeholder={$i18n.t('API Base URL')}
					value={url}
					autocomplete="off"
					readonly
				/>
			</div>
		</div>
	</Tooltip>

	<div class="flex items-center justify-between gap-3 pt-1">
		<label for="qlcode-api-key" class="text-sm font-semibold text-gray-900 dark:text-gray-50">
			{$i18n.t('API Key')}
		</label>
		<a
			class="shrink-0 text-sm font-semibold text-blue-700 underline-offset-4 hover:text-blue-900 hover:underline dark:text-blue-300 dark:hover:text-blue-100"
			href={QLCODE_API_PORTAL_URL}
			target="_blank"
			rel="noreferrer"
			aria-label="获取 QLCodeAPI 密钥"
		>
			获取密钥
		</a>
	</div>

	<div class="flex items-center">
		<SensitiveInput
			id="qlcode-api-key"
			bind:value={key}
			screenReader={false}
			placeholder={$i18n.t('API Key')}
			required={false}
			on:change={() => {
				onSubmit({ url, key });
			}}
		/>
	</div>
</div>
