# WenShanKB 常用命令

.PHONY: up down build migrate seed logs

# 启动全部服务
up:
	docker compose up -d

# 停止全部服务
down:
	docker compose down

# 重新构建并启动
build:
	docker compose build --no-cache
	docker compose up -d

# 数据迁移
migrate:
	docker compose exec api python -m app.migration.runner --source /data/markdown --mode full

# 增量同步
sync:
	docker compose exec api python -m app.migration.runner --source /data/markdown --mode incremental

# 查看日志
logs:
	docker compose logs -f --tail=100

# 仅查看 API 日志
logs-api:
	docker compose logs -f api

# 初始化数据库（需要先启动 db）
db-init:
	docker compose exec db psql -U kb_user -d wenshan_kb -f /docker-entrypoint-initdb.d/01-schema.sql

# 进入 API 容器
shell:
	docker compose exec api bash

# 运行测试
test:
	docker compose exec api pytest app/tests/ -v
