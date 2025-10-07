# Stores 目录

使用 Zustand 管理全局状态。

## Capabilities Store

### 功能特性

- ✅ **持久化存储**：使用 localStorage 持久化能力数据
- ✅ **智能缓存**：5分钟缓存有效期，避免频繁请求
- ✅ **自动刷新**：缓存过期自动重新获取
- ✅ **类型安全**：完整的 TypeScript 支持
- ✅ **错误处理**：内置错误处理机制

### 使用方法

```typescript
import { useCapabilitiesStore } from '@/stores/capabilitiesStore'

// 在组件中使用
const MyComponent = () => {
  const { 
    capabilities,      // 能力列表
    loading,          // 加载状态
    error,            // 错误信息
    fetchCapabilities, // 获取能力列表
    clearCapabilities  // 清除缓存
  } = useCapabilitiesStore()

  useEffect(() => {
    // 自动从缓存或API获取数据
    fetchCapabilities()
  }, [])

  return (
    <Select loading={loading}>
      {capabilities.map(cap => (
        <Select.Option key={cap.capability_id} value={cap.capability_id}>
          {cap.capability_name}
        </Select.Option>
      ))}
    </Select>
  )
}
```

### API

#### `fetchCapabilities(force?: boolean)`

获取能力列表

- `force`: 是否强制刷新（跳过缓存）

```typescript
// 正常获取（使用缓存）
fetchCapabilities()

// 强制刷新
fetchCapabilities(true)
```

#### `clearCapabilities()`

清除所有能力数据和缓存

```typescript
clearCapabilities()
```

### 缓存机制

- **缓存时长**：5分钟
- **存储位置**：localStorage (`capabilities-storage`)
- **自动过期**：超过5分钟自动重新请求

### 数据结构

```typescript
interface Capability {
  capability_id: number
  capability_name: string
  description?: string
}
```
