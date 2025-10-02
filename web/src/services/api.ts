/**
 * API 服务层
 *
 * 封装所有后端 API 请求，提供统一的接口调用方式
 * 包含请求/响应拦截器，用于处理认证、错误等公共逻辑
 */
import axios from "axios";

/**
 * 创建 axios 实例
 *
 * 跨域处理：
 * - 开发环境：使用空字符串作为 baseURL，请求将使用相对路径（如 /api/...）
 *   这样会触发 vite.config.ts 中配置的代理，由 Vite 转发到后端服务器
 * - 生产环境：使用环境变量中的完整 URL，直接请求后端 API
 *   前提是后端已配置 CORS 或前后端部署在同一域名下
 */
const api = axios.create({
  baseURL:
    import.meta.env.MODE === "development"
      ? "" // 开发环境使用相对路径，走 Vite 代理避免跨域
      : import.meta.env.VITE_API_BASE_URL || "", // 生产环境使用完整 API 地址
  timeout: 10000, // 请求超时时间 10 秒
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * 请求拦截器
 *
 * 在请求发送前执行，可用于：
 * - 添加认证 token 到请求头
 * - 修改请求参数
 * - 记录请求日志等
 */
api.interceptors.request.use(
  (config) => {
    // TODO: 添加认证 token（需要时取消注释）
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config;
  },
  (error) => {
    // 请求错误时的处理
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 *
 * 在响应返回后执行，可用于：
 * - 统一处理响应数据格式
 * - 处理错误状态码
 * - 刷新 token 等
 */
api.interceptors.response.use(
  (response) => {
    // 直接返回响应数据，简化调用方代码
    return response.data;
  },
  (error) => {
    // 统一错误处理
    console.error("API Error:", error);

    // TODO: 可以根据不同的错误状态码做不同处理
    // if (error.response?.status === 401) {
    //   // 未授权，跳转到登录页
    // } else if (error.response?.status === 403) {
    //   // 无权限
    // } else if (error.response?.status >= 500) {
    //   // 服务器错误
    // }

    return Promise.reject(error);
  }
);

/**
 * 模型相关 API
 *
 * 提供模型的 CRUD 操作和健康检查功能
 */
export const modelsApi = {
  /**
   * 获取所有模型列表
   * @param capabilities - 可选的能力筛选参数
   * @returns 模型列表
   */
  getModels: (capabilities?: string) =>
    api.get("/admin/models/", { params: capabilities ? { capabilities } : {} }),

  /**
   * 获取数据库中存储的模型
   * @returns 数据库中的模型列表
   */
  getDbModels: () => api.get("/api/database/models"),

  /**
   * 创建新模型
   * @param data - 模型数据
   * @returns 创建结果
   */
  createModel: (data: any) => api.post("/api/database/models", data),
  /**
   * 删除指定模型
   * @param modelName - 模型名称
   * @returns 删除结果
   */
  deleteModel: (modelName: string) =>
    api.delete(`/api/database/models/${modelName}`),

  /**
   * 获取指定模型的详细信息
   * @param modelName - 模型名称
   * @returns 模型详情
   */
  getModelDetails: (modelName: string) => api.get(`/admin/models/${modelName}`),

  /**
   * 获取指定模型的健康状态
   * @param modelName - 模型名称
   * @returns 健康状态信息
   */
  getModelHealth: (modelName: string) =>
    api.get(`/admin/models/${modelName}/health`),
};

/**
 * 供应商相关 API
 *
 * 管理 AI 模型供应商（如 OpenAI, Anthropic 等）的配置和健康状态
 */
export const providersApi = {
  /**
   * 获取所有供应商列表及其健康状态
   * @returns 供应商列表
   */
  getProviders: () => api.get("/admin/providers/"),

  /**
   * 获取数据库中存储的供应商配置
   * @returns 数据库中的供应商列表
   */
  getDbProviders: () => api.get("/api/database/providers"),

  /**
   * 创建新供应商
   * @param data - 供应商配置数据
   * @returns 创建结果
   */
  createProvider: (data: any) => api.post("/api/database/providers", data),

  /**
   * 获取指定供应商的健康状态
   * @param providerName - 供应商名称
   * @returns 健康状态信息
   */
  getProviderHealth: (providerName: string) =>
    api.get(`/admin/providers/${providerName}/health`),

  /**
   * 更新指定供应商的健康状态
   * @param providerName - 供应商名称
   * @param data - 健康状态数据
   * @returns 更新结果
   */
  updateProviderHealth: (providerName: string, data: any) =>
    api.put(`/admin/providers/${providerName}/health`, data),
};

/**
 * 系统统计相关 API
 *
 * 提供系统监控、统计数据和健康检查等功能
 */
export const statsApi = {
  /**
   * 获取路由统计信息
   * @returns 路由使用统计数据
   */
  getRoutingStats: () => api.get("/admin/stats/"),

  /**
   * 获取系统监控状态
   * @returns 监控状态信息
   */
  getMonitoringStatus: () => api.get("/admin/monitoring/status"),

  /**
   * 获取系统性能指标
   * @returns 系统指标数据（CPU、内存、请求量等）
   */
  getSystemMetrics: () => api.get("/admin/monitoring/metrics"),

  /**
   * 执行系统健康检查
   * @returns 健康检查结果
   */
  getHealthCheck: () => api.get("/admin/health/"),
};

// 导出默认的 axios 实例，供特殊场景使用
export default api;
