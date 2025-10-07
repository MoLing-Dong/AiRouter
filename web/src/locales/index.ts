/**
 * 国际化翻译文件
 *
 * 统一管理所有页面的多语言文本
 */

export const translations = {
  // 通用
  common: {
    confirm: { "zh-CN": "确认", "en-US": "Confirm" },
    cancel: { "zh-CN": "取消", "en-US": "Cancel" },
    save: { "zh-CN": "保存", "en-US": "Save" },
    delete: { "zh-CN": "删除", "en-US": "Delete" },
    edit: { "zh-CN": "编辑", "en-US": "Edit" },
    add: { "zh-CN": "添加", "en-US": "Add" },
    search: { "zh-CN": "搜索", "en-US": "Search" },
    refresh: { "zh-CN": "刷新", "en-US": "Refresh" },
    loading: { "zh-CN": "加载中...", "en-US": "Loading..." },
    success: { "zh-CN": "操作成功", "en-US": "Success" },
    error: { "zh-CN": "操作失败", "en-US": "Error" },
    submit: { "zh-CN": "提交", "en-US": "Submit" },
    reset: { "zh-CN": "重置", "en-US": "Reset" },
    actions: { "zh-CN": "操作", "en-US": "Actions" },
    status: { "zh-CN": "状态", "en-US": "Status" },
    name: { "zh-CN": "名称", "en-US": "Name" },
    description: { "zh-CN": "描述", "en-US": "Description" },
    createdAt: { "zh-CN": "创建时间", "en-US": "Created At" },
    updatedAt: { "zh-CN": "更新时间", "en-US": "Updated At" },
    enabled: { "zh-CN": "启用", "en-US": "Enabled" },
    disabled: { "zh-CN": "禁用", "en-US": "Disabled" },
    unknown: { "zh-CN": "未知", "en-US": "Unknown" },
    responseTime: { "zh-CN": "响应时间", "en-US": "Response Time" },
    none: { "zh-CN": "无", "en-US": "None" },
  },

  // 供应商页面
  providers: {
    title: { "zh-CN": "供应商管理", "en-US": "Providers Management" },
    addProvider: { "zh-CN": "新增供应商", "en-US": "Add Provider" },
    editProvider: { "zh-CN": "编辑供应商", "en-US": "Edit Provider" },
    providerName: { "zh-CN": "供应商名称", "en-US": "Provider Name" },
    providerType: { "zh-CN": "类型", "en-US": "Type" },
    apiKey: { "zh-CN": "API Key", "en-US": "API Key" },
    apiEndpoint: { "zh-CN": "API 端点", "en-US": "API Endpoint" },
    endpoint: { "zh-CN": "端点", "en-US": "Endpoint" },
    health: { "zh-CN": "健康状态", "en-US": "Health Status" },
    performance: { "zh-CN": "性能", "en-US": "Performance" },
    responseTime: { "zh-CN": "响应时间", "en-US": "Response Time" },
    successRate: { "zh-CN": "成功率", "en-US": "Success Rate" },
    healthCheck: { "zh-CN": "健康检查", "en-US": "Health Check" },
    healthCheckSuccess: {
      "zh-CN": "健康检查完成",
      "en-US": "Health check completed",
    },
    healthCheckFailed: {
      "zh-CN": "健康检查失败",
      "en-US": "Health check failed",
    },
    deleteConfirm: {
      "zh-CN": "确定要删除这个供应商吗？",
      "en-US": "Are you sure to delete this provider?",
    },
    deleteSuccess: { "zh-CN": "删除成功", "en-US": "Deleted successfully" },
    deleteFailed: { "zh-CN": "删除失败", "en-US": "Delete failed" },
    createSuccess: { "zh-CN": "创建成功", "en-US": "Created successfully" },
    createFailed: { "zh-CN": "创建失败", "en-US": "Create failed" },
    updateSuccess: { "zh-CN": "更新成功", "en-US": "Updated successfully" },
    updateFailed: { "zh-CN": "更新失败", "en-US": "Update failed" },
    fetchFailed: {
      "zh-CN": "获取供应商列表失败",
      "en-US": "Failed to fetch providers",
    },
    saveSuccess: { "zh-CN": "保存成功", "en-US": "Saved successfully" },
    pleaseInputName: {
      "zh-CN": "请输入供应商名称",
      "en-US": "Please input provider name",
    },
    pleaseSelectType: {
      "zh-CN": "请选择供应商类型",
      "en-US": "Please select provider type",
    },
    pleaseInputEndpoint: {
      "zh-CN": "请输入 API 端点",
      "en-US": "Please input API endpoint",
    },
    pleaseInputApiKey: {
      "zh-CN": "请输入 API Key",
      "en-US": "Please input API Key",
    },
    selectProviderType: {
      "zh-CN": "选择供应商类型",
      "en-US": "Select provider type",
    },
    providerNamePlaceholder: {
      "zh-CN": "例如：openai",
      "en-US": "e.g.: openai",
    },
    endpointPlaceholder: {
      "zh-CN": "例如：https://api.openai.com/v1",
      "en-US": "e.g.: https://api.openai.com/v1",
    },
    totalProviders: {
      "zh-CN": "共 {total} 个供应商",
      "en-US": "{total} providers in total",
    },
    active: { "zh-CN": "活跃", "en-US": "Active" },
    inactive: { "zh-CN": "停用", "en-US": "Inactive" },
    healthy: { "zh-CN": "健康", "en-US": "Healthy" },
    unhealthy: { "zh-CN": "不健康", "en-US": "Unhealthy" },
    unknown: { "zh-CN": "未知", "en-US": "Unknown" },
  },

  // 模型页面
  models: {
    title: { "zh-CN": "模型管理", "en-US": "Models Management" },
    addModel: { "zh-CN": "新增模型", "en-US": "Add Model" },
    editModel: { "zh-CN": "编辑模型", "en-US": "Edit Model" },
    modelName: { "zh-CN": "模型名称", "en-US": "Model Name" },
    modelType: { "zh-CN": "类型", "en-US": "Type" },
    accessType: { "zh-CN": "访问类型", "en-US": "Access Type" },
    publicModel: { "zh-CN": "公开模型", "en-US": "Public Model" },
    privateModel: { "zh-CN": "私有模型", "en-US": "Private Model" },
    public: { "zh-CN": "公开", "en-US": "Public" },
    private: { "zh-CN": "私有", "en-US": "Private" },
    modelCapabilities: { "zh-CN": "模型能力", "en-US": "Model Capabilities" },
    modelDescription: { "zh-CN": "模型描述", "en-US": "Model Description" },
    capabilities: { "zh-CN": "能力", "en-US": "Capabilities" },
    enabled: { "zh-CN": "启用", "en-US": "Enabled" },
    disabled: { "zh-CN": "禁用", "en-US": "Disabled" },
    unbound: { "zh-CN": "未绑定", "en-US": "Unbound" },
    weight: { "zh-CN": "权重", "en-US": "Weight" },
    health: { "zh-CN": "健康", "en-US": "Health" },
    modelIdNotExist: {
      "zh-CN": "模型ID不存在",
      "en-US": "Model ID does not exist",
    },
    deleteFailed: { "zh-CN": "删除失败", "en-US": "Delete failed" },
    createFailed: { "zh-CN": "创建失败", "en-US": "Create failed" },
    updateFailed: { "zh-CN": "更新失败", "en-US": "Update failed" },
    deleteConfirm: {
      "zh-CN": "确定要删除这个模型吗？",
      "en-US": "Are you sure to delete this model?",
    },
    deleteSuccess: { "zh-CN": "删除成功", "en-US": "Deleted successfully" },
    saveSuccess: { "zh-CN": "保存成功", "en-US": "Saved successfully" },
    fetchFailed: {
      "zh-CN": "获取模型列表失败",
      "en-US": "Failed to fetch models",
    },
    createSuccess: { "zh-CN": "创建成功", "en-US": "Created successfully" },
    updateSuccess: { "zh-CN": "更新成功", "en-US": "Updated successfully" },
    pleaseInputName: {
      "zh-CN": "请输入模型名称",
      "en-US": "Please input model name",
    },
    pleaseSelectAccessType: {
      "zh-CN": "请选择访问类型",
      "en-US": "Please select access type",
    },
    pleaseInputDescription: {
      "zh-CN": "请输入模型描述（可选）",
      "en-US": "Please input model description (optional)",
    },
    selectAccessType: {
      "zh-CN": "选择访问类型",
      "en-US": "Select access type",
    },
    selectCapabilities: {
      "zh-CN": "选择模型能力",
      "en-US": "Select model capabilities",
    },
    capabilityTooltip: {
      "zh-CN": "选择模型支持的功能,可多选",
      "en-US": "Select supported features, multiple selection allowed",
    },
    accessTypeTooltip: {
      "zh-CN": "模型的具体能力(对话、补全、嵌入、图像)通过下方的能力设置",
      "en-US":
        "Specific capabilities (chat, completion, embedding, image) are set via capabilities below",
    },
    examplePlaceholder: { "zh-CN": "例如：gpt-4", "en-US": "e.g.: gpt-4" },
    totalModels: {
      "zh-CN": "共 {total} 个模型",
      "en-US": "{total} models in total",
    },
  },

  // 仪表盘
  dashboard: {
    title: { "zh-CN": "仪表盘", "en-US": "Dashboard" },
    activeModels: { "zh-CN": "活跃模型", "en-US": "Active Models" },
    healthyProviders: { "zh-CN": "健康供应商", "en-US": "Healthy Providers" },
    averageResponseTime: {
      "zh-CN": "平均响应时间",
      "en-US": "Avg Response Time",
    },
    recentModels: { "zh-CN": "最近模型", "en-US": "Recent Models" },
    providerHealth: { "zh-CN": "供应商健康状态", "en-US": "Provider Health" },
    modelName: { "zh-CN": "模型名称", "en-US": "Model Name" },
    provider: { "zh-CN": "供应商", "en-US": "Provider" },
    healthy: { "zh-CN": "健康", "en-US": "Healthy" },
    unhealthy: { "zh-CN": "异常", "en-US": "Unhealthy" },
    healthStatus: { "zh-CN": "健康状态", "en-US": "Health Status" },
    public: { "zh-CN": "公共", "en-US": "Public" },
    private: { "zh-CN": "私有", "en-US": "Private" },
  },

  // 菜单
  menu: {
    dashboard: { "zh-CN": "仪表盘", "en-US": "Dashboard" },
    providers: { "zh-CN": "供应商", "en-US": "Providers" },
    models: { "zh-CN": "模型", "en-US": "Models" },
    apiKeys: { "zh-CN": "API 密钥", "en-US": "API Keys" },
    monitoring: { "zh-CN": "监控", "en-US": "Monitoring" },
    settings: { "zh-CN": "设置", "en-US": "Settings" },
    logout: { "zh-CN": "退出登录", "en-US": "Logout" },
  },

  // 设置
  settings: {
    theme: { "zh-CN": "主题", "en-US": "Theme" },
    language: { "zh-CN": "语言", "en-US": "Language" },
    lightMode: { "zh-CN": "亮色模式", "en-US": "Light Mode" },
    darkMode: { "zh-CN": "暗色模式", "en-US": "Dark Mode" },
    autoMode: { "zh-CN": "跟随系统", "en-US": "Auto" },
  },
};

// 类型定义
export type TranslationKey = keyof typeof translations;
export type Locale = "zh-CN" | "en-US";

/**
 * 获取翻译文本的辅助函数
 */
export function getTranslation(
  category: TranslationKey,
  key: string,
  locale: Locale
): string {
  const categoryTranslations = translations[category] as Record<
    string,
    Record<Locale, string>
  >;
  return categoryTranslations[key]?.[locale] || key;
}
