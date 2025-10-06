.PHONY: help routes routes-detail routes-export dev test

help:
	@echo "================================"
	@echo "AI Router 快捷命令"
	@echo "================================"
	@echo "make routes-export - 导出接口文档到 Markdown"
	@echo "make dev           - 启动开发服务器"
	@echo "make test          - 运行测试"
	@echo "================================"

# 导出接口文档
routes-export:
	@echo "📝 导出接口文档..."
	@mkdir -p docs
	@curl -s http://localhost:8888/openapi.json > docs/openapi.json 2>/dev/null || echo "⚠️  请先启动应用: make dev"
	@echo "✅ 已保存到: docs/openapi.json"

# 启动开发服务器
dev:
	@echo "🚀 启动开发服务器..."
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8888

# 运行测试
test:
	@echo "🧪 运行测试..."
	uv run pytest

