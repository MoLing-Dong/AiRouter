import axios from "axios";

// 创建 axios 实例
const api = axios.create({
  baseURL: "http://localhost:8000", // 后端 API 地址
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  }
);

// 模型相关 API
export const modelsApi = {
  // 获取所有模型
  getModels: (capabilities?: string) =>
    api.get("/admin/models/", { params: capabilities ? { capabilities } : {} }),

  // 获取数据库中的模型
  getDbModels: () => api.get("/api/database/models"),

  // 创建模型
  createModel: (data: any) => api.post("/api/database/models", data),

  // 获取模型详情
  getModelDetails: (modelName: string) => api.get(`/admin/models/${modelName}`),

  // 获取模型健康状态
  getModelHealth: (modelName: string) =>
    api.get(`/admin/models/${modelName}/health`),
};

// 供应商相关 API
export const providersApi = {
  // 获取所有供应商及健康状态
  getProviders: () => api.get("/admin/providers/"),

  // 获取数据库中的供应商
  getDbProviders: () => api.get("/api/database/providers"),

  // 创建供应商
  createProvider: (data: any) => api.post("/api/database/providers", data),

  // 获取供应商健康状态
  getProviderHealth: (providerName: string) =>
    api.get(`/admin/providers/${providerName}/health`),

  // 更新供应商健康状态
  updateProviderHealth: (providerName: string, data: any) =>
    api.put(`/admin/providers/${providerName}/health`, data),
};

// 系统统计相关 API
export const statsApi = {
  // 获取路由统计
  getRoutingStats: () => api.get("/admin/stats/"),

  // 获取系统监控状态
  getMonitoringStatus: () => api.get("/admin/monitoring/status"),

  // 获取系统指标
  getSystemMetrics: () => api.get("/admin/monitoring/metrics"),

  // 获取健康检查
  getHealthCheck: () => api.get("/admin/health/"),
};

export default api;
