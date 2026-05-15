# QLCodeChat v0.9.5 服务器部署包说明

本说明对应镜像版本：

```text
qlcode-chat:v0.9.5
```

部署包目录包含：

```text
qlcode-chat-v0.9.5.tar.gz   Docker 镜像压缩包
docker-compose.yaml         服务器运行配置
.env.example                环境变量模板
README-部署说明.md          本说明文档副本
SHA256SUMS                  文件校验值
```

## 1. 上传到服务器

在本机执行：

```bash
scp qlcode-chat-v0.9.5.tar.gz docker-compose.yaml .env.example README-部署说明.md SHA256SUMS root@你的服务器IP:/opt/qlcode-chat/
```

如果服务器目录不存在，先执行：

```bash
ssh root@你的服务器IP "mkdir -p /opt/qlcode-chat"
```

## 2. 服务器加载镜像

登录服务器：

```bash
ssh root@你的服务器IP
cd /opt/qlcode-chat
```

校验文件：

```bash
sha256sum -c SHA256SUMS
```

加载镜像：

```bash
docker load < qlcode-chat-v0.9.5.tar.gz
docker images qlcode-chat
```

确认能看到：

```text
qlcode-chat   v0.9.5
```

## 3. 准备运行配置

复制环境变量文件：

```bash
cp .env.example .env
```

生成正式密钥：

```bash
openssl rand -hex 32
```

编辑 `.env`：

```bash
nano .env
```

至少确认这些值：

```env
QLCODE_CHAT_DOCKER_TAG=v0.9.5
QLCODE_CHAT_PORT=3000
QLCODE_CHAT_SECRET_KEY=替换成 openssl 生成的长随机值
CORS_ALLOW_ORIGIN=https://你的正式域名
```

如果暂时没有域名，可以先用：

```env
CORS_ALLOW_ORIGIN=*
```

## 4. 停止原官方容器

如果服务器上原来运行过官方容器，先查看：

```bash
docker ps
```

如果容器名是 `open-webui`：

```bash
docker stop open-webui || true
docker rm open-webui || true
```

如果占用的是 3000 端口，但容器名不同，需要停止对应容器，或者把 `.env` 里的端口改成其他端口：

```env
QLCODE_CHAT_PORT=8081
```

## 5. 启动 QLCodeChat

在服务器 `/opt/qlcode-chat` 目录执行：

```bash
docker compose up -d
```

检查状态：

```bash
docker compose ps
docker logs --tail=100 qlcode-chat
curl -i http://127.0.0.1:3000/health
```

成功时健康接口返回：

```json
{"status":true}
```

## 6. 访问地址

如果没有反向代理：

```text
http://服务器IP:3000/
```

如果使用 Nginx、宝塔或 1Panel，把域名反代到：

```text
http://127.0.0.1:3000
```

## 7. 后续更新

后续发布新版本时，不要复用旧标签。使用新的版本号，例如：

```text
qlcode-chat:v0.9.6
```

服务器更新流程：

```bash
docker compose down
docker load < qlcode-chat-v0.9.6.tar.gz
sed -i 's/^QLCODE_CHAT_DOCKER_TAG=.*/QLCODE_CHAT_DOCKER_TAG=v0.9.6/' .env
docker compose up -d
```
