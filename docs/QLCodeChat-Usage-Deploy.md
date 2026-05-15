# QLCodeChat 使用与部署说明

本文档用于本项目的本地验证、镜像构建、服务器部署、日常运维和故障排查。

## 1. 项目定位

QLCodeChat 是 QLCode 的私有 AI 对话应用，面向 QLCodeAPI 使用场景定制。

- 品牌名称：QLCodeChat
- 品牌官网：https://qlcodeapi.com/
- 用户侧 API 地址固定为：https://api.qlcodeapi.com/v1
- 用户只需要填写自己的 QLCodeAPI 密钥，不需要选择或修改服务商地址
- 用户侧模型选择器只展示 `gpt-5.5` 和 `gpt-5.4`
- 图片生成默认使用用户自己的密钥，并固定使用 `gpt-image-2`
- 如果用户密钥没有 `gpt-image-2` 权限，图片生成会给出明确提示
- 新注册用户默认是普通用户，不需要管理员审核
- 对话模型在用户界面以 `QL` 展示
- 容器内应用监听 `8080`，宿主机默认映射为 `3000`

## 2. 本地运行

进入项目根目录：

```bash
cd /path/to/qlcode-chat
```

启动当前本地镜像：

```bash
QLCODE_CHAT_SECRET_KEY='local-test-secret-change-before-server' docker compose up -d qlcode-chat
```

查看运行状态：

```bash
docker compose ps
docker logs -f qlcode-chat
curl -i http://127.0.0.1:3000/health
```

本机访问：

```text
http://127.0.0.1:3000/
```

局域网访问时使用本机局域网 IP，例如：

```text
http://192.168.9.106:3000/
```

如果要换宿主机端口，例如改为 `8081`：

```bash
QLCODE_CHAT_PORT=8081 QLCODE_CHAT_SECRET_KEY='local-test-secret-change-before-server' docker compose up -d qlcode-chat
```

## 3. 构建镜像

普通构建：

```bash
docker compose build qlcode-chat
```

中国大陆网络构建时，如果 Docker 拉镜像慢，可以让构建过程走本机代理：

```bash
HTTP_PROXY=http://127.0.0.1:8890 \
HTTPS_PROXY=http://127.0.0.1:8890 \
ALL_PROXY=socks5://127.0.0.1:8891 \
NO_PROXY=localhost,127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12 \
docker compose build qlcode-chat
```

这个代理只用于本机开发构建。美国 VPS 通常不要配置这个代理，也不要把 `127.0.0.1:8890` 复制到服务器。

构建完成后检查镜像：

```bash
docker images qlcode-chat
```

## 4. 快速部署到服务器

如果服务器不需要保留旧数据，最快方式是本机构建镜像，然后传到服务器加载运行。这样服务器不需要重新构建，速度更快，也更稳定。

本机打包镜像：

```bash
docker save qlcode-chat:v0.9.6 | gzip > qlcode-chat-v0.9.6.tar.gz
```

上传到服务器：

```bash
scp qlcode-chat-v0.9.6.tar.gz docker-compose.prod.yaml .env.example root@你的服务器IP:/opt/
```

服务器上准备目录：

```bash
ssh root@你的服务器IP
mkdir -p /opt/qlcode-chat
mv /opt/qlcode-chat-v0.9.6.tar.gz /opt/qlcode-chat/
mv /opt/docker-compose.prod.yaml /opt/qlcode-chat/docker-compose.yaml
mv /opt/.env.example /opt/qlcode-chat/.env
cd /opt/qlcode-chat
```

服务器加载镜像：

```bash
docker load < qlcode-chat-v0.9.6.tar.gz
```

生成正式密钥并写入 `.env`：

```bash
openssl rand -hex 32
nano .env
```

至少修改：

```env
QLCODE_CHAT_SECRET_KEY=替换成上一步生成的长随机值
QLCODE_CHAT_DOCKER_TAG=v0.9.6
QLCODE_CHAT_PORT=3000
CORS_ALLOW_ORIGIN=https://你的正式域名
```

启动：

```bash
docker compose up -d
```

检查：

```bash
docker compose ps
docker logs --tail=100 qlcode-chat
curl -i http://127.0.0.1:3000/health
```

## 5. 域名反向代理

如果使用 Nginx，将域名反代到容器宿主机端口即可。示例：

```nginx
server {
    listen 80;
    server_name chat.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用 HTTPS 后，把 `.env` 中的 `CORS_ALLOW_ORIGIN` 改成正式域名，例如：

```env
CORS_ALLOW_ORIGIN=https://chat.example.com
```

## 6. 更新版本

本机重新构建：

```bash
docker compose build qlcode-chat
docker tag qlcode-chat:v0.9.5 qlcode-chat:v0.9.6
docker save qlcode-chat:v0.9.6 | gzip > qlcode-chat-v0.9.6.tar.gz
```

上传并替换服务器镜像：

```bash
scp qlcode-chat-v0.9.6.tar.gz root@你的服务器IP:/opt/qlcode-chat/
ssh root@你的服务器IP
cd /opt/qlcode-chat
docker compose down
docker load < qlcode-chat-v0.9.6.tar.gz
sed -i 's/^QLCODE_CHAT_DOCKER_TAG=.*/QLCODE_CHAT_DOCKER_TAG=v0.9.6/' .env
docker compose up -d
```

确认健康：

```bash
docker compose ps
curl -i http://127.0.0.1:3000/health
```

## 7. 数据与备份

默认数据卷：

```text
qlcode-chat
```

查看数据卷：

```bash
docker volume ls | grep qlcode-chat
```

备份数据卷：

```bash
docker run --rm \
  -v qlcode-chat:/data \
  -v "$PWD":/backup \
  busybox \
  tar czf /backup/qlcode-chat-data-$(date +%Y%m%d-%H%M).tar.gz -C /data .
```

恢复数据卷前先停止容器：

```bash
docker compose down
docker run --rm \
  -v qlcode-chat:/data \
  -v "$PWD":/backup \
  busybox \
  sh -c 'cd /data && tar xzf /backup/你的备份文件.tar.gz'
docker compose up -d
```

## 8. 常用运维命令

查看容器：

```bash
docker ps
docker compose ps
```

查看日志：

```bash
docker logs -f qlcode-chat
```

重启：

```bash
docker compose restart
```

停止：

```bash
docker compose down
```

清理未使用镜像和构建缓存：

```bash
docker image prune -f
docker builder prune -f
```

## 9. 常见问题

### 端口被占用

如果 `3000` 被占用，修改 `.env`：

```env
QLCODE_CHAT_PORT=8081
```

然后重启：

```bash
docker compose up -d
```

### 容器刚启动显示 unhealthy

第一次启动会初始化数据库和加载后端模块，可能短时间显示 `starting` 或 `unhealthy`。先看日志：

```bash
docker logs --tail=200 qlcode-chat
```

再检查健康接口：

```bash
curl -i http://127.0.0.1:3000/health
```

只要返回下面内容就说明服务正常：

```json
{"status":true}
```

### 用户没有模型可用

用户需要在连接设置中填写自己的 QLCodeAPI 密钥。服务商地址已经固定为 `https://api.qlcodeapi.com/v1`，用户不需要也不能修改地址。

### 服务器不需要代理

美国 VPS 一般直接访问 Docker Hub 和 QLCodeAPI，不需要配置本机代理。只有本地开发机网络慢时，才需要 Docker 代理配置。
