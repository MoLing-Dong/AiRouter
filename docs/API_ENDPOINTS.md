# AI路由器 API 端点文档

## 模型管理 API

### 统一模型列表接口

- **端点**: `GET /v1/models/`
- **描述**: 获取模型列表，支持能力过滤
- **参数**:
  - `capabilities` (可选): 逗号分隔的能力名称列表
- **用途**: 统一的模型查询接口，支持灵活过滤

#### 使用示例

**获取所有模型**:

```bash
GET /v1/models/
```

**获取聊天模型**:

```bash
GET /v1/models/?capabilities=TEXT,MULTIMODAL_IMAGE_UNDERSTANDING
```

**获取图片生成模型**:

```bash
GET /v1/models/?capabilities=TEXT_TO_IMAGE,IMAGE_TO_IMAGE
```

**获取纯文本模型**:

```bash
GET /v1/models/?capabilities=TEXT
```

**获取多模态模型**:

```bash
GET /v1/models/?capabilities=MULTIMODAL_IMAGE_UNDERSTANDING,TEXT_TO_IMAGE,IMAGE_TO_IMAGE
```

## 聊天 API

### 聊天完成

- **端点**: `POST /v1/chat/completions`
- **描述**: OpenAI兼容的聊天接口
- **模型过滤**: 自动过滤支持 `TEXT` 和 `MULTIMODAL_IMAGE_UNDERSTANDING` 能力的模型
- **用途**: 文本对话、图片内容理解等任务

## 图片生成 API

### 文生图

- **端点**: `POST /v1/images/generations`
- **描述**: 从文本提示生成图片
- **模型过滤**: 自动过滤支持 `TEXT_TO_IMAGE` 能力的模型

### 图片编辑

- **端点**: `POST /v1/images/edits`
- **描述**: 基于提示和可选遮罩编辑图片
- **模型过滤**: 自动过滤支持 `IMAGE_TO_IMAGE` 能力的模型

## 能力类型说明

系统支持以下能力类型：

| 能力ID | 能力名称 | 描述 |
|--------|----------|------|
| 1 | TEXT | 文本处理能力 |
| 2 | IMAGE | 图片处理能力 |
| 3 | VIDEO | 视频处理能力 |
| 4 | AUDIO | 音频处理能力 |
| 5 | MULTIMODAL_IMAGE_UNDERSTANDING | 图片内容理解能力 |
| 6 | TEXT_TO_IMAGE | 文生图能力 |
| 7 | IMAGE_TO_IMAGE | 图生图能力 |

## 使用示例

### 获取聊天模型

```bash
curl -X GET "http://localhost:8000/v1/models/?capabilities=TEXT,MULTIMODAL_IMAGE_UNDERSTANDING"
```

### 获取图片生成模型

```bash
curl -X GET "http://localhost:8000/v1/models/?capabilities=TEXT_TO_IMAGE,IMAGE_TO_IMAGE"
```

### 获取纯文本模型

```bash
curl -X GET "http://localhost:8000/v1/models/?capabilities=TEXT"
```

### 获取所有模型

```bash
curl -X GET "http://localhost:8000/v1/models/"
```

### 使用聊天API（自动模型过滤）

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## 注意事项

1. **自动过滤**: 聊天和图片API会自动过滤不支持的模型，无需手动指定
2. **能力检查**: 系统会从数据库查询模型的实际能力，确保过滤准确性
3. **性能优化**: 能力过滤在应用层进行，避免无效的API调用
4. **扩展性**: 新的能力类型可以通过数据库配置添加，无需修改代码
