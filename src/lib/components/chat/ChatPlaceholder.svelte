<script lang="ts">
	import { CHAT_ASSISTANT_DISPLAY_NAME, WEBUI_BRAND_LOGO_URL } from '$lib/constants';

	import { config, temporaryChatEnabled } from '$lib/stores';
	import { getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};
</script>

<div class="m-auto w-full max-w-6xl px-8 lg:px-20">
	<div class="flex justify-start">
		<div class="flex mb-0.5" in:fade={{ duration: 200 }}>
			<img
				src={WEBUI_BRAND_LOGO_URL}
				class=" size-[2.7rem] rounded-full border-[1px] border-gray-100 dark:border-none"
				alt={CHAT_ASSISTANT_DISPLAY_NAME}
				draggable="false"
			/>
		</div>
	</div>

	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
			className="w-full flex justify-start mb-0.5"
			placement="top"
		>
			<div class="flex items-center gap-2 text-gray-500 text-lg mt-2 w-fit">
				<EyeSlash strokeWidth="2.5" className="size-5" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div
		class=" mt-2 mb-4 text-3xl text-gray-800 dark:text-gray-100 text-left flex items-center gap-4 font-primary"
	>
		<div>
			<div class=" capitalize line-clamp-1" in:fade={{ duration: 200 }}>
				{CHAT_ASSISTANT_DISPLAY_NAME}
			</div>

			<div in:fade={{ duration: 200, delay: 200 }}>
				<div class=" text-gray-400 dark:text-gray-500 line-clamp-1 font-p">
					{$i18n.t('How can I help you today?')}
				</div>
			</div>
		</div>
	</div>

	<div class=" w-full font-primary" in:fade={{ duration: 200, delay: 300 }}>
		<Suggestions
			className="grid grid-cols-2"
			suggestionPrompts={$config?.default_prompt_suggestions ?? []}
			{onSelect}
		/>
	</div>
</div>
