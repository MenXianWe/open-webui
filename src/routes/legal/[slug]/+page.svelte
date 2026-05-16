<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { page } from '$app/stores';

	import { QLCODE_LOGIN_WORDMARK_URL } from '$lib/constants';
	import { config, WEBUI_NAME } from '$lib/stores';

	type LoginTermsDocument = {
		id?: string;
		title: string;
		slug: string;
		content: string;
	};

	$: documents = ($config?.login_terms?.documents ?? []) as LoginTermsDocument[];
	$: document = documents.find((item) => item.slug === $page.params.slug) ?? null;
	$: renderedHtml = document
		? DOMPurify.sanitize(marked.parse(document.content || '', { async: false }) as string)
		: '';
</script>

<svelte:head>
	<title>{document?.title ?? '服务条款'} - {$WEBUI_NAME}</title>
</svelte:head>

<main class="ql-legal-page">
	<header class="ql-legal-header">
		<a href="/auth" aria-label="返回登录页">
			<img src={QLCODE_LOGIN_WORDMARK_URL} alt="QLCodeChat" draggable="false" />
		</a>
		<a href="/auth">返回登录</a>
	</header>

	<section class="ql-legal-shell">
		<aside class="ql-legal-nav" aria-label="服务条款文档">
			{#each documents as item}
				<a class:active={item.slug === $page.params.slug} href={`/legal/${item.slug}`}>
					{item.title}
				</a>
			{/each}
		</aside>

		<article class="ql-legal-document">
			{#if document}
				{@html renderedHtml}
			{:else}
				<h1>文档不存在</h1>
				<p>管理员尚未配置这个服务条款文档，或该文档已被移除。</p>
			{/if}
		</article>
	</section>
</main>

<style>
	:global(body) {
		background: #f8fbff;
	}

	.ql-legal-page {
		min-height: 100dvh;
		color: #061155;
		background:
			linear-gradient(rgba(10, 64, 190, 0.04) 1px, transparent 1px),
			linear-gradient(90deg, rgba(10, 64, 190, 0.04) 1px, transparent 1px),
			linear-gradient(135deg, #fbfdff 0%, #f5f9ff 52%, #eef6ff 100%);
		background-size:
			48px 48px,
			48px 48px,
			auto;
		font-family: var(--font-primary);
	}

	.ql-legal-header {
		max-width: 1180px;
		margin: 0 auto;
		padding: 22px 28px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
	}

	.ql-legal-header img {
		width: clamp(170px, 13vw, 240px);
		height: auto;
		display: block;
	}

	.ql-legal-header > a:last-child {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 40px;
		padding: 0 18px;
		border-radius: 999px;
		background: #075cf8;
		color: #ffffff;
		font-size: 0.95rem;
		font-weight: 900;
		text-decoration: none;
		box-shadow: 0 0.75rem 1.8rem rgba(7, 92, 248, 0.2);
	}

	.ql-legal-shell {
		width: min(1180px, calc(100vw - 40px));
		margin: 12px auto 48px;
		display: grid;
		grid-template-columns: 240px minmax(0, 1fr);
		gap: 22px;
		align-items: start;
	}

	.ql-legal-nav,
	.ql-legal-document {
		border: 1px solid rgba(109, 132, 171, 0.18);
		border-radius: 22px;
		background: rgba(255, 255, 255, 0.92);
		box-shadow: 0 1.25rem 3rem rgba(21, 65, 151, 0.08);
	}

	.ql-legal-nav {
		position: sticky;
		top: 22px;
		display: grid;
		gap: 8px;
		padding: 14px;
	}

	.ql-legal-nav a {
		display: flex;
		align-items: center;
		min-height: 44px;
		border-radius: 14px;
		padding: 0 14px;
		color: #33415f;
		font-size: 0.98rem;
		font-weight: 800;
		text-decoration: none;
	}

	.ql-legal-nav a.active,
	.ql-legal-nav a:hover {
		background: #eef5ff;
		color: #0758ff;
	}

	.ql-legal-document {
		min-height: 540px;
		padding: clamp(28px, 3vw, 48px);
		color: #17213d;
		font-size: 1.05rem;
		line-height: 1.86;
	}

	.ql-legal-document :global(h1),
	.ql-legal-document :global(h2),
	.ql-legal-document :global(h3) {
		color: #061155;
		letter-spacing: 0;
	}

	.ql-legal-document :global(h1) {
		margin: 0 0 20px;
		font-size: clamp(1.75rem, 2.2vw, 2.35rem);
		font-weight: 900;
	}

	.ql-legal-document :global(h2) {
		margin: 30px 0 12px;
		font-size: 1.25rem;
		font-weight: 900;
	}

	.ql-legal-document :global(p) {
		margin: 0 0 15px;
	}

	.ql-legal-document :global(ul),
	.ql-legal-document :global(ol) {
		margin: 0 0 15px 1.5rem;
		padding: 0;
	}

	@media (max-width: 820px) {
		.ql-legal-header {
			padding: 16px;
		}

		.ql-legal-header img {
			width: min(46vw, 180px);
		}

		.ql-legal-shell {
			width: calc(100vw - 28px);
			grid-template-columns: minmax(0, 1fr);
			margin-bottom: 28px;
		}

		.ql-legal-nav {
			position: static;
			display: flex;
			overflow-x: auto;
		}

		.ql-legal-nav a {
			flex: 0 0 auto;
			white-space: nowrap;
		}

		.ql-legal-document {
			min-height: auto;
			padding: 24px 20px;
			font-size: 1rem;
		}
	}
</style>
