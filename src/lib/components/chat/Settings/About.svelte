<script lang="ts">
	import { WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<div id="tab-about" class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] md:max-h-full">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>{$WEBUI_NAME}</div>
			</div>
			<div class="flex w-full">
				<div class="flex flex-col gap-2 text-xs text-gray-700 dark:text-gray-200">
					<div class="grid grid-cols-[5rem_1fr] items-center gap-3">
						<div class="text-gray-500 dark:text-gray-400">当前版本</div>
						<div>v{WEBUI_VERSION}</div>
					</div>
					<div class="grid grid-cols-[5rem_1fr] items-center gap-3">
						<div class="text-gray-500 dark:text-gray-400">作者</div>
						<div>晴朗</div>
					</div>
					<div class="grid grid-cols-[5rem_1fr] items-center gap-3">
						<div class="text-gray-500 dark:text-gray-400">联系方式</div>
						<a class="hover:underline" href="mailto:qlcodeapi@qq.com">qlcodeapi@qq.com</a>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
