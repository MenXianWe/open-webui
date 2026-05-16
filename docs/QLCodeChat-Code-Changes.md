# QLCodeChat 代码改动说明

本文档只记录 QLCodeChat 定制过程中对应用代码、前端资源、运行配置和部署配置的改动，不记录非代码类清理事项。

当前定制版本：

```text
QLCodeChat v0.9.8
Docker image: qlcode-chat:v0.9.8
Base branch: main
Production branch: qlcode-chat-production
```

## 1. 品牌与应用基础信息

目标：

- 将应用对外展示统一为 `QLCodeChat`。
- 将品牌官网统一为 `https://qlcodeapi.com/`。
- 将用户侧 OpenAI 兼容接口固定为 `https://api.qlcodeapi.com/v1`。
- 将聊天助手在界面中的展示名固定为 `QL`。

主要改动：

- `package.json`
  - 包名改为 `qlcode-chat`。
  - 版本保持为 `0.9.8`，作为 Docker 镜像版本标签来源。
- `src/lib/constants.ts`
  - 新增并集中维护品牌常量：
    - `APP_NAME = 'QLCodeChat'`
    - `CHAT_ASSISTANT_DISPLAY_NAME = 'QL'`
    - `QLCODE_API_BASE_URL = 'https://api.qlcodeapi.com/v1'`
    - `QLCODE_API_PORTAL_URL = 'https://api.qlcodeapi.com/'`
  - 新增品牌 Logo、登录页素材、默认用户头像相关静态资源路径。
- `backend/open_webui/env.py`
  - 默认应用名改为 `QLCodeChat`。
  - 默认 favicon URL 指向 QLCode 官网资源。
  - 数据库、Redis、追踪服务等默认命名前缀改为 QLCodeChat 体系。
- `backend/open_webui/main.py`
  - FastAPI 应用标题、启动横幅、Swagger favicon、OpenSearch 输出等对外信息改为 QLCodeChat。
- `static/manifest.json`
- `static/opensearch.xml`
- `backend/open_webui/static/site.webmanifest`
  - PWA、搜索描述、站点名称改为 QLCodeChat。

## 2. 品牌 Logo 与静态资源

目标：

- 替换原应用 Logo、favicon、启动图、PWA 图标。
- 登录页使用 QLCode 品牌素材。
- 通过资源版本参数避免浏览器和局域网设备继续读取旧缓存。

主要改动：

- `static/static/qlcode-login/`
- `backend/open_webui/static/qlcode-login/`
  - 新增登录页和品牌相关 WebP 素材：
    - `app-logo.webp`
    - `brand-wordmark.webp`
    - `hero-visual.webp`
    - `login-reference.webp`
- `static/static/logo.png`
- `static/static/favicon.png`
- `static/static/favicon.ico`
- `static/static/favicon.svg`
- `static/static/splash.png`
- `static/static/splash-dark.png`
- `backend/open_webui/static/logo.png`
- `backend/open_webui/static/favicon.png`
- `backend/open_webui/static/favicon.ico`
- `backend/open_webui/static/splash.png`
- `backend/open_webui/static/splash-dark.png`
  - 替换为 QLCodeChat 品牌资源。
- `src/app.html`
- `src/routes/+layout.svelte`
  - favicon、splash、通知图标路径增加 `?v=qlcode`，用于刷新旧缓存。

## 3. 用户侧 QLCodeAPI 固定连接

目标：

- 用户侧只保留 QLCodeAPI 连接。
- 用户不能修改服务商地址。
- 用户只填写自己的 QLCodeAPI 密钥。
- 用户密钥保存在原用户设置结构中，减少对原数据结构的破坏。

主要改动：

- `backend/open_webui/utils/qlcode.py`
  - 新增 QLCodeAPI 统一工具模块。
  - 固定基础地址：`https://api.qlcodeapi.com/v1`。
  - 固定用户侧可见对话模型白名单：`gpt-5.5`、`gpt-5.4`。
  - 提供用户密钥读取函数：
    - 从用户设置的 direct connection 中读取 QLCodeAPI key。
    - 如果旧数据存在多个连接，会提取并归一化到 QLCodeAPI 固定连接。
  - 提供请求头生成和错误详情解析能力。
- `src/lib/components/chat/Settings/Connections.svelte`
  - 用户连接设置页由“多个外部连接管理”改为“QLCodeAPI Connection”。
  - 只渲染一个固定连接。
  - 连接地址固定为 QLCodeAPI，不提供新增、删除、修改 URL 的入口。
- `src/lib/components/chat/Settings/Connections/Connection.svelte`
  - 地址输入改为固定展示。
  - 用户只需要填写 API Key。
  - 在输入密钥位置增加“获取密钥”入口，指向 `https://api.qlcodeapi.com/`。
  - API Key 输入框增加明显边框、聚焦态高亮和自动聚焦，降低用户找不到输入位置的概率。
- `src/lib/components/common/SensitiveInput.svelte`
  - 增加可选 `autofocus` 参数，供 QLCodeAPI 密钥输入框打开时自动聚焦。
- `src/lib/apis/openai/index.ts`
  - 对 QLCodeAPI 地址做特殊处理：
    - 获取模型时不让浏览器直接跨域访问 QLCodeAPI，而是请求后端代理接口。
    - 聊天补全也通过后端代理接口转发，避免前端 CORS 和暴露额外连接逻辑。
- `backend/open_webui/routers/users.py`
  - 增加用户侧 direct connection 的规范化处理。
  - 增加用户 QLCodeAPI 模型和聊天代理相关接口。
  - 用户直连模型列表只返回 `gpt-5.5` 和 `gpt-5.4`。
  - 用户直连聊天请求会拒绝白名单外的模型，避免前端隐藏被绕过。
  - 用户保存设置时保持 QLCodeAPI 地址固定。
- `backend/open_webui/main.py`
  - `/api/models` 返回用户可用模型前增加 QLCodeChat 白名单过滤，左上角模型选择器只展示 `gpt-5.5` 和 `gpt-5.4`。
- `src/lib/apis/index.ts`
  - 前端模型列表再做一层白名单过滤，防止直接连接或旧缓存把其他模型带回选择器。

## 4. 图片生成与图片编辑

目标：

- 用户默认拥有图片生成能力。
- 图片生成不再依赖管理员在后台统一配置的图片服务密钥。
- 图片生成使用用户自己填写的 QLCodeAPI 密钥。
- 图片模型固定为 `gpt-image-2`。

主要改动：

- `backend/open_webui/utils/qlcode.py`
  - 固定图片模型：

    ```text
    gpt-image-2
    ```

  - 默认图片尺寸：

    ```text
    1024x1024
    ```

- `backend/open_webui/routers/images.py`
  - `/api/v1/images/models` 固定返回 `gpt-image-2`。
  - `/api/v1/images/generations` 改为：
    - 从当前用户设置中读取 QLCodeAPI key。
    - 调用 `https://api.qlcodeapi.com/v1/images/generations`。
    - 自动上传返回图片到应用文件系统，继续复用原聊天图片展示流程。
  - `/api/v1/images/edits` 改为：
    - 使用当前用户 QLCodeAPI key。
    - 固定模型为 `gpt-image-2`。
    - 保留 multipart 图片编辑请求能力。
  - 错误处理改为尽量返回 QLCodeAPI 的原始错误详情，便于用户定位密钥或额度问题。
  - 图片生成和图片编辑前会读取用户密钥可用模型；如果密钥未开通 `gpt-image-2`，返回明确提示。
- `src/lib/apis/images/index.ts`
  - 图片编辑请求体结构调整为后端新接口需要的格式。
- `backend/open_webui/config.py`
  - 图片生成默认模型调整为 `gpt-image-2`。

## 5. 聊天模型展示固定为 QL

目标：

- 聊天消息中不再根据具体模型名称展示。
- 助手头像使用 QLCodeChat 品牌 Logo。
- 界面统一展示为 `QL`。

主要改动：

- `src/lib/components/chat/Messages/ResponseMessage.svelte`
  - 助手消息头像固定使用 QLCodeChat 品牌 Logo。
  - 助手名称固定显示为 `QL`。
  - Tooltip 同样固定为 `QL`。
- `src/lib/constants.ts`
  - 新增 `CHAT_ASSISTANT_DISPLAY_NAME`。
- `src/lib/components/chat/ModelSelector/ModelItem.svelte`
- `src/lib/components/chat/ModelSelector/ModelItemMenu.svelte`
- `src/lib/components/chat/MessageInput/Commands/Models.svelte`
  - 模型选择和模型展示相关 UI 做品牌化处理，减少用户对底层模型供应商的感知。

## 6. 默认用户头像与个人图标

目标：

- 左上角和登录页品牌位置使用 QLCodeChat Logo。
- 用户头像位置继续保留字母头像逻辑。
- 用户没有上传头像前，不使用品牌 Logo 充当用户头像。

主要改动：

- `src/lib/constants.ts`
  - 新增默认用户头像路径：
    - `WEBUI_DEFAULT_USER_IMAGE_URL`
    - `WEBUI_DEFAULT_USER_PROFILE_IMAGE_VALUE`
- `src/lib/components/chat/Messages/UserMessage.svelte`
  - 用户消息头像兜底改为默认用户头像。
- `src/lib/components/chat/Messages/ProfileImage.svelte`
- `src/lib/components/chat/Settings/Account/UserProfileImage.svelte`
- `src/lib/components/layout/Sidebar/UserMenu.svelte`
  - 调整用户头像兜底行为，优先使用用户上传头像或字母头像。
- `backend/open_webui/models/models.py`
- `backend/open_webui/config.py`
  - 模型/默认配置中的品牌图片路径改为 QLCodeChat 品牌资源。

## 7. 登录与注册界面

目标：

- 替换原登录页为 QLCodeChat 登录页。
- 保留登录、注册、LDAP、首次管理员创建等原有流程。
- 右上角增加“使用教程”链接。
- 登录/注册表单视觉布局适配桌面和移动端。

主要改动：

- `src/routes/auth/+page.svelte`
  - 重构登录页结构。
  - 使用 QLCodeChat wordmark、app logo 和 hero visual。
  - 支持登录、注册、LDAP、首次管理员创建流程。
  - 注册状态下避免表单超出屏幕。
  - 密码和确认密码输入支持显示/隐藏。
  - 增加“使用教程”链接，默认指向 `https://qlcodeapi.com/`。
  - 缩小顶部品牌 wordmark，并让品牌和教程入口更靠近页面左右上角。
  - 登录表单和右侧视觉内容整体上移，减少首屏顶部留白。
  - 注册页在启用邮箱验证码后显示验证码输入框和发送验证码按钮。
  - 移除毛玻璃式模糊视觉，改为更清晰的实色和层级样式。
- `static/static/qlcode-login/`
- `backend/open_webui/static/qlcode-login/`
  - 提供登录页所需 WebP 素材。

### 注册邮箱验证码

目标：

- 支持管理员配置 SMTP，用于发送注册邮箱验证码。
- 新用户注册时可要求先通过邮箱验证码。
- 首个管理员创建流程不强制验证码，避免 SMTP 未配置时无法初始化系统。
- 验证码只保存 HMAC 哈希，并支持 Redis；未配置 Redis 时回退到当前进程内存 TTL。

主要改动：

- `backend/open_webui/config.py`
  - 新增 `ENABLE_EMAIL_VERIFICATION`、`EMAIL_VERIFICATION_TTL_SECONDS`。
  - 新增 SMTP 配置：`SMTP_HOST`、`SMTP_PORT`、`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM_EMAIL`、`SMTP_FROM_NAME`、`SMTP_USE_TLS`。
  - SMTP 默认主机为 `smtpdm.aliyun.com`，默认端口 `465`，默认用户名和发件人为 `no-reply@mail.qlcodeapi.com`，默认发件人名称为 `QLCode API`，默认启用 TLS。
  - 旧数据库中 SMTP 主机、用户名、发件人邮箱为空时会自动补齐；发件人名称为空或仍为旧默认 `QLCodeChat` 时会自动迁移为 `QLCode API`。
- `backend/open_webui/utils/email_verification.py`
  - 新增验证码生成、哈希存储、校验、SMTP 发送和邮件模板渲染能力。
  - 优先使用 Redis 保存验证码，失败或未配置时使用内存 TTL。
- `backend/open_webui/models/auths.py`
  - 注册表单新增 `email_verification_code`。
- `backend/open_webui/routers/auths.py`
  - 新增 `POST /api/v1/auths/email/verification/send` 发送注册验证码。
  - 新增 `POST /api/v1/auths/admin/config/smtp/test` 发送 SMTP 测试邮件。
  - 注册时在启用邮箱验证码且不是首个用户时校验验证码。
  - 管理员配置接口支持读取和保存 SMTP 设置；密码返回时不回显明文，留空保存会保留旧值。
- `backend/open_webui/main.py`
  - `/api/config` 增加 `features.enable_email_verification`，用于登录页控制验证码字段。
- `src/lib/apis/auths/index.ts`
  - 新增发送注册验证码和 SMTP 测试邮件 API。
- `src/lib/components/admin/Settings/General.svelte`
  - 通用设置中新增 SMTP 设置、注册邮箱验证码开关、测试连接和发送测试邮件。
- `src/routes/auth/+page.svelte`
  - 注册模式下按配置显示邮箱验证码输入框和发送按钮。
- `Dockerfile`、`docker-compose.yaml`、`docker-compose.prod.yaml`、`.env.example`
  - 增加邮箱验证码和 SMTP 相关环境变量默认值。

### 登录服务条款确认

目标：

- 登录页可要求用户先阅读并同意服务条款。
- 管理员可在通用设置中控制启用状态、展示形式、条款更新日期和 Markdown 文档内容。
- 条款更新日期变化后，登录页会要求用户重新确认。

主要改动：

- `backend/open_webui/config.py`
  - 新增 `LOGIN_TERMS_ENABLED`、`LOGIN_TERMS_DISPLAY_STYLE`、`LOGIN_TERMS_UPDATED_AT`、`LOGIN_TERMS_DOCUMENTS` 持久配置。
  - 默认启用条款确认，默认展示形式为弹窗，默认条款更新日期为 `2026-03-31`。
  - 内置服务条款、使用政策、支持的国家和地区、服务特定条款四份 Markdown 文档。
- `backend/open_webui/main.py`
  - `/api/config` 新增 `login_terms`，未登录状态下登录页可读取条款开关、展示形式、更新日期和文档内容。
- `backend/open_webui/models/auths.py`
  - 登录、注册、LDAP 登录表单新增 `terms_accepted` 和 `terms_updated_at`。
- `backend/open_webui/routers/auths.py`
  - 条款启用后，登录、注册、LDAP 登录会校验用户是否同意当前更新日期对应的条款。
  - 管理员配置接口支持读取和保存登录条款配置。
- `src/lib/components/admin/Settings/General.svelte`
  - 通用设置新增“登录条款确认”面板，支持启用开关、弹窗/复选框模式、更新日期和文档增删编辑。
- `src/routes/auth/+page.svelte`
  - 登录页按配置显示条款弹窗或复选框。
  - 未同意条款时禁用登录入口，并在提交时提示用户先同意条款。
- `src/routes/legal/[slug]/+page.svelte`
  - 新增公开条款文档页，用于查看 `/legal/terms`、`/legal/usage-policy` 等 Markdown 文档。
- `Dockerfile`、`docker-compose.yaml`、`docker-compose.prod.yaml`、`.env.example`
  - 增加登录条款相关环境变量默认值。

## 8. 字体、缩放、对比度与界面清晰度

目标：

- 页面默认比例回到 `1x`。
- 侧边栏和设置页字体更清晰、更大。
- 去除毛玻璃模糊效果。
- 提升文字颜色对比度。

主要改动：

- `src/lib/utils/text-scale.ts`
  - 增加默认缩放常量：

    ```text
    DEFAULT_TEXT_SCALE = 1
    ```

- `src/routes/+layout.svelte`
  - 初始化文本缩放时使用 `DEFAULT_TEXT_SCALE`。
- `src/app.css`
  - 为侧边栏增加独立字体缩放变量：

    ```text
    --sidebar-text-scale: 1.1
    ```

  - 放大侧边栏中的 `text-xs`、`text-sm`、`text-base` 和聊天列表项目尺寸。
  - 聊天列表项高度、padding、标题行高跟随侧边栏缩放。

- 多个 Svelte 组件
  - 移除或弱化 blur/backdrop blur 类样式。
  - 调整浅色文本为更高对比度颜色。

## 9. 关于页与版本信息

目标：

- 不显示“最新版本”相关远程更新提示。
- 只展示当前版本、作者和联系方式。

主要改动：

- `src/lib/components/chat/Settings/About.svelte`
  - 文案调整为：
    - 当前版本：`0.9.8`
    - 作者：`晴朗`
    - 联系方式：`qlcodeapi@qq.com`
  - 版本检查相关显示逻辑调整为当前版本口径。
- `backend/open_webui/main.py`
  - `/api/version/updates` 返回当前版本作为 latest，避免用户侧看到远程更新提示。
  - `/api/changelog` 返回空内容，避免前端或第三方入口读取更新日志。
- `backend/open_webui/env.py`
  - 固定关闭远程版本更新检查相关行为。
  - 移除运行时更新日志解析逻辑，不再从 `CHANGELOG.md` 读取更新内容。
- `src/routes/(app)/+layout.svelte`
  - 移除管理员登录后的“最近更新内容”弹窗挂载和触发逻辑。
  - 移除更新提示 toast 的检查和渲染逻辑。
- `src/lib/components/admin/Settings/General.svelte`
  - 管理设置中只保留当前版本号，不再显示“检查更新”“查看更新内容”“latest/available”等状态。
- `src/lib/components/chat/Settings/Interface.svelte`
  - 移除“更新 toast”和“登录显示 What's New 弹窗”的用户设置开关。
- `src/lib/components/ChangelogModal.svelte`
  - 删除更新日志弹窗组件。
- `CHANGELOG.md`
  - 删除镜像和源码包中不再需要的更新日志文件。
- `Dockerfile`、`pyproject.toml`
  - 移除更新日志文件的镜像复制和 Python 包强制包含配置。
- `cypress/support/e2e.ts`、`cypress/e2e/registration.cy.ts`
  - 移除测试中针对更新日志弹窗的兼容点击逻辑。
- `backend/open_webui/utils/qlcode.py`
  - 用户设置读取/保存时强制关闭 `showChangelog` 和 `showUpdateToast`，兼容旧管理员账号已有设置。

## 10. 后端品牌化与运行行为

目标：

- 后端对外响应、日志、默认路径、User-Agent 和数据命名不再暴露旧品牌。
- 私有部署时降低外部更新和远程依赖感知。

主要改动：

- `backend/open_webui/env.py`
  - 默认数据库文件名改为 `qlcode-chat.db`。
  - Redis key prefix 改为 `qlcode-chat`。
  - OpenTelemetry service name 改为 `qlcode-chat`。
  - Forward header 命名改为 `X-QLCodeChat-*`。
- `backend/open_webui/retrieval/web/*.py`
- `backend/open_webui/retrieval/loaders/*.py`
  - Web 检索和加载器 User-Agent 改为 QLCodeChat。
- `backend/open_webui/retrieval/vector/**/*.py`
  - 向量库 collection/index/prefix 默认值改为 QLCodeChat 命名体系。
- `backend/open_webui/tools/*.py`
- `backend/open_webui/utils/*.py`
  - 工具、自动化、PDF、telemetry 等内部说明和默认名称做品牌化调整。
- `backend/start.sh`
  - 启动提示文案改为 QLCodeChat。

### 注册默认角色

目标：

- 新注册用户默认成为普通用户，避免进入待审核状态。

主要改动：

- `backend/open_webui/config.py`
  - `DEFAULT_USER_ROLE` 默认值从 `pending` 调整为 `user`。
- `backend/open_webui/routers/auths.py`
  - 普通注册和 LDAP 自动创建用户时，写入角色固定为 `user`。
  - 首个用户注册成为管理员后，不再自动关闭注册开关。
- `backend/open_webui/main.py`
  - 使用环境变量预置管理员时，不再自动关闭注册开关。
- `backend/open_webui/utils/oauth.py`
  - OAuth 新用户无角色匹配时默认写入 `user`。

### 连接默认值

目标：

- Ollama API 默认关闭，避免新部署自动尝试连接本地 Ollama。
- 系统级 OpenAI 外部连接默认关闭，避免管理员未配置时暴露无效服务商入口。
- 直接连接默认打开，保证用户侧 QLCodeAPI 密钥入口可用。
- 通用设置中的 QLCodeChat URL 默认指向正式访问域名。
- 通用设置中的管理员邮箱默认使用 `qlcodeapi@qq.com`。
- 登录页“使用教程”链接默认指向 `https://qlcodeapi.com/`，并允许管理员在通用设置里修改。
- 首页建议词使用中文默认内容。

主要改动：

- `backend/open_webui/config.py`
  - `ENABLE_OLLAMA_API` 默认值从 `true` 调整为 `false`。
  - `ENABLE_OPENAI_API` 默认值从 `true` 调整为 `false`。
  - `ENABLE_DIRECT_CONNECTIONS` 默认保持为 `true`。
  - `WEBUI_URL` 默认值改为 `https://chat.qlcodeapi.com/`，旧配置为空时会自动补齐。
  - 新增 `QLCODE_TUTORIAL_URL` 持久配置，默认值为 `https://qlcodeapi.com/`，旧配置为空时会自动补齐。
  - `ADMIN_EMAIL` 默认值改为 `qlcodeapi@qq.com`，旧配置为空时会自动补齐。
  - 默认提示建议改为中文内容；如果旧数据库仍是官方英文默认建议，会自动迁移为 QLCodeChat 中文建议，不覆盖管理员自定义建议。
- `backend/open_webui/main.py`
  - `/api/config` 公开返回 `qlcode_tutorial_url`，用于登录页未登录状态读取教程链接。
- `backend/open_webui/routers/auths.py`
  - 管理员通用配置接口支持读取和保存 `QLCODE_TUTORIAL_URL`。
- `src/routes/auth/+page.svelte`
  - 右上角入口从“获取密钥”改为“使用教程”，链接从 `/api/config` 读取，默认回退到 `https://qlcodeapi.com/`。
  - 调整登录页纵向间距，让登录区域更接近视觉居中。
- `src/lib/components/admin/Settings/General.svelte`
  - 通用设置新增“使用教程 URL”输入项。
- `src/lib/utils/connections.ts`
  - 程序化新增/删除系统 OpenAI 连接时，缺省开关保持关闭。
- `Dockerfile`
  - 镜像默认环境增加 `WEBUI_URL=https://chat.qlcodeapi.com/`、`QLCODE_TUTORIAL_URL=https://qlcodeapi.com/`、`ADMIN_EMAIL=qlcodeapi@qq.com`、`ENABLE_OLLAMA_API=false`、`ENABLE_OPENAI_API=false`、`ENABLE_DIRECT_CONNECTIONS=true`、`ENABLE_EMAIL_VERIFICATION=false`、登录条款默认项和 SMTP 默认项。
- `docker-compose.yaml`、`docker-compose.prod.yaml`、`.env.example`
  - 运行环境默认带上 `WEBUI_URL=https://chat.qlcodeapi.com/`、`QLCODE_TUTORIAL_URL=https://qlcodeapi.com/`、`ADMIN_EMAIL=qlcodeapi@qq.com`、`ENABLE_SIGNUP=true`、`ENABLE_OLLAMA_API=false`、`ENABLE_OPENAI_API=false`、`ENABLE_DIRECT_CONNECTIONS=true`、`ENABLE_EMAIL_VERIFICATION=false`、登录条款默认项和 SMTP 默认项。

## 11. Docker 构建与运行配置

目标：

- 本地和服务器部署都使用固定版本镜像，不使用 `latest`。
- 降低 Docker 构建上下文体积。
- 支持本地构建时走代理，但不影响服务器运行。
- 提供生产运行 compose。

主要改动：

- `Dockerfile`
  - 移除会额外拉取 build syntax 镜像的声明，减少构建时网络失败点。
  - 增加构建镜像源参数：APT、npm、PyPI、uv 均可通过 build args 覆盖。
  - 前端构建默认设置 `ONNXRUNTIME_NODE_INSTALL_CUDA=skip`，避免 `onnxruntime-node` 在非 CUDA 构建中下载 GitHub 上的大体积 CUDA 二进制。
- `.dockerignore`
  - 忽略 `.venv`、`backend/.venv`、`release` 等本地大目录，避免传入 Docker build context。
- `docker-compose.yaml`
  - 服务名和容器名改为 `qlcode-chat`。
  - 镜像默认标签改为：

    ```text
    qlcode-chat:v0.9.8
    ```

  - 添加构建代理参数，便于本地网络较慢时构建。
  - 添加 `ONNXRUNTIME_NODE_INSTALL_CUDA=skip` 构建参数，提升干净构建稳定性。
  - 默认宿主机端口仍为 `3000`，容器内部监听 `8080`。

- `docker-compose.prod.yaml`
  - 新增服务器部署用 compose。
  - 使用已构建镜像运行，不在服务器上重新 build。
  - 通过 `.env` 控制端口、版本号、密钥、CORS。
- `.env.example`
  - 新增 QLCodeChat 服务器运行环境变量模板：
    - `QLCODE_CHAT_DOCKER_TAG=v0.9.8`
    - `QLCODE_CHAT_PORT=3000`
    - `NPM_CONFIG_REGISTRY=https://registry.npmmirror.com`
    - `DEBIAN_APT_MIRROR=http://mirrors.aliyun.com/debian`
    - `DEBIAN_SECURITY_MIRROR=http://mirrors.aliyun.com/debian-security`
    - `PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple`
    - `UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple`
    - `ONNXRUNTIME_NODE_INSTALL_CUDA=skip`
    - `QLCODE_CHAT_SECRET_KEY`
    - `CORS_ALLOW_ORIGIN`
    - `WEBUI_URL=https://chat.qlcodeapi.com/`
    - `QLCODE_TUTORIAL_URL=https://qlcodeapi.com/`
    - `ADMIN_EMAIL=qlcodeapi@qq.com`
    - `ENABLE_SIGNUP=true`
    - `ENABLE_OLLAMA_API=false`
    - `ENABLE_OPENAI_API=false`
    - `ENABLE_DIRECT_CONNECTIONS=true`
    - `ENABLE_EMAIL_VERIFICATION=false`
    - SMTP 相关默认项

## 12. 部署包与运维文档

目标：

- 服务器可以直接加载镜像包运行。
- 部署步骤、更新步骤、备份步骤可重复执行。

主要改动：

- `docs/QLCodeChat-Usage-Deploy.md`
  - 增加完整部署、更新、反向代理、备份、排错说明。
- `release/qlcode-chat-v0.9.8/`
  - 本地生成部署包目录，包含：
    - `qlcode-chat-v0.9.8.tar.gz`
    - `docker-compose.yaml`
    - `.env.example`
    - `README-部署说明.md`
    - `SHA256SUMS`
- `release/qlcode-chat-v0.9.8-release.tar.gz`
  - 本地生成总压缩包，便于一次性上传服务器。

## 13. 验证情况

v0.9.8 已执行过的验证：

- `PYTHONPATH=backend .venv/bin/python -m py_compile ...`
  - 本次涉及的后端文件语法检查通过。
- QLCode 模型过滤和图片模型判断辅助函数检查通过。
- `git diff --check`
  - 本次 diff 无空白格式问题。
- `rg ... Changelog/UpdateInfoToast/showChangelog/showUpdateToast/getVersionUpdates`
  - 前端运行代码中已无更新弹窗、更新 toast、更新日志 API 调用入口；后端仅保留返回空内容/当前版本的兼容接口和旧设置强制关闭逻辑。
- 临时数据目录启动配置检查
  - `WEBUI_URL` 默认返回 `https://chat.qlcodeapi.com/`。
  - `ENABLE_OLLAMA_API` 默认返回 `False`。
  - `ENABLE_OPENAI_API` 默认返回 `False`。
  - `ENABLE_DIRECT_CONNECTIONS` 默认返回 `True`。
  - `ADMIN_EMAIL` 默认返回 `qlcodeapi@qq.com`。
  - `QLCODE_TUTORIAL_URL` 默认返回 `https://qlcodeapi.com/`。
  - `ENABLE_EMAIL_VERIFICATION` 默认返回 `False`。
  - 登录条款默认返回 `enabled=True`、`display_style=modal`、`updated_at=2026-03-31`，并包含 4 份默认文档。
  - SMTP 默认返回主机 `smtpdm.aliyun.com`、端口 `465`、用户名 `no-reply@mail.qlcodeapi.com`、发件人 `no-reply@mail.qlcodeapi.com`、发件人名称 `QLCode API`、`SMTP_USE_TLS=True`。
  - `DEFAULT_PROMPT_SUGGESTIONS` 返回 6 条 QLCodeChat 中文建议。
- 邮箱验证码辅助函数检查
  - 验证码长度为 6 位。
  - 正确验证码可通过校验。
  - 验证码校验后会被消费，重复校验失败。
- 本地源码运行检查
  - 后端 `http://127.0.0.1:8080/health` 返回 `200`。
  - 前端 `http://192.168.9.106:3000/` 返回 `200`。
  - 未登录 `/api/config` 返回 `qlcode_tutorial_url=https://qlcodeapi.com/` 和 `features.enable_email_verification=false`。
  - 未同意条款时登录接口返回 `400` 和“请先阅读并同意服务条款。”。
  - 携带当前条款确认日期后，登录接口继续进入正常账号密码校验流程。
  - 未启用邮箱验证码时，发送验证码接口返回 `403` 和“邮箱验证码未启用。”。
  - 登录后 `/api/config` 返回中文建议和直接连接开启。
  - 管理员 `/api/v1/auths/admin/config` 返回 `WEBUI_URL=https://chat.qlcodeapi.com/` 和可编辑的 `QLCODE_TUTORIAL_URL`。
- `docker compose --env-file .env.example build qlcode-chat`
  - 本地 Docker 镜像 `qlcode-chat:v0.9.8` 构建完成。
  - 构建过程中使用代理和镜像源下载依赖。
  - 原 `onnxruntime-node` CUDA 二进制下载卡顿问题已通过 `ONNXRUNTIME_NODE_INSTALL_CUDA=skip` 固化处理。
- 临时 Docker 容器验证
  - 镜像 `qlcode-chat:v0.9.8` 启动成功。
  - `/health` 返回 `{"status":true}`。
  - `/api/config` 返回 `name=QLCodeChat`、`version=0.9.8`、`features.enable_signup=true`、`features.enable_version_update_check=false`、服务条款配置存在。
- `npx eslint ...`
  - 未通过，原因是 `src/lib/apis/index.ts`、`src/lib/stores/index.ts`、部分 Svelte 组件内已有多处 `any`、a11y 和未使用 CSS 选择器等历史 lint 问题；本次变更未留下更新弹窗相关的未使用导入。

v0.9.5 历史部署包已执行过的验证：

- `npm run build`
  - 前端构建通过。
- `docker compose build qlcode-chat`
  - Docker 镜像构建完成。
- `docker compose up -d qlcode-chat`
  - 本地容器运行成功，健康检查返回 `{"status":true}`。
- `docker compose -f docker-compose.prod.yaml --env-file .env.example config`
  - 生产 compose 配置校验通过。
- `gzip -t`、`sha256sum -c SHA256SUMS`
  - 镜像压缩包和 release 总包完整性校验通过。

## 14. 后续维护注意事项

- 后续发版不要复用旧 Docker 标签，应使用新版本号，例如 `v0.9.8`。
- 用户侧 API 地址应继续只从 `backend/open_webui/utils/qlcode.py` 和 `src/lib/constants.ts` 的 QLCode 常量派生，避免散落硬编码。
- 图片生成和聊天代理都依赖用户自己的 QLCodeAPI key，相关错误优先检查用户连接设置。
- 如果新增登录页视觉素材，应同时放入前端静态目录和后端静态目录，保证 Docker 构建后资源路径一致。
- 修改 favicon、splash、PWA 图标后，继续使用版本参数避免旧缓存。
