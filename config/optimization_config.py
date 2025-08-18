"""
性能优化配置文件

集中管理所有性能优化相关的配置参数
"""

from pydantic import BaseSettings, Field
from typing import Dict, List, Optional, Any
from enum import Enum


class OptimizationLevel(str, Enum):
    """优化级别"""

    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"


class ConnectionPoolConfig(BaseSettings):
    """连接池配置"""

    max_pool_size: int = Field(default=20, description="最大连接池大小")
    min_pool_size: int = Field(default=5, description="最小连接池大小")
    num_shards: int = Field(default=16, description="连接池分片数量")
    cleanup_interval: float = Field(default=30.0, description="清理间隔（秒）")
    health_check_interval: float = Field(
        default=180.0, description="健康检查间隔（秒）"
    )
    max_idle_time: float = Field(default=300.0, description="最大空闲时间（秒）")
    max_use_count: int = Field(default=1000, description="最大使用次数")
    wait_timeout: float = Field(default=5.0, description="等待超时时间（秒）")

    class Config:
        env_prefix = "CONNECTION_POOL_"


class LoadBalancingConfig(BaseSettings):
    """负载均衡配置"""

    cache_ttl: float = Field(default=30.0, description="缓存生存时间（秒）")
    health_check_timeout: float = Field(default=2.0, description="健康检查超时（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=0.1, description="重试延迟（秒）")
    performance_weight: float = Field(default=0.4, description="性能权重")
    cost_weight: float = Field(default=0.2, description="成本权重")
    success_rate_weight: float = Field(default=0.4, description="成功率权重")

    class Config:
        env_prefix = "LOAD_BALANCING_"


class DatabaseConfig(BaseSettings):
    """数据库配置"""

    pool_size: int = Field(default=20, description="数据库连接池大小")
    max_overflow: int = Field(default=30, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="连接超时（秒）")
    pool_recycle: int = Field(default=3600, description="连接回收时间（秒）")
    query_cache_ttl: float = Field(default=60.0, description="查询缓存生存时间（秒）")
    batch_size: int = Field(default=1000, description="批量操作大小")
    slow_query_threshold: float = Field(default=1.0, description="慢查询阈值（秒）")

    class Config:
        env_prefix = "DATABASE_"


class CachingConfig(BaseSettings):
    """缓存配置"""

    enabled: bool = Field(default=True, description="是否启用缓存")
    cache_type: str = Field(default="redis", description="缓存类型")
    redis_url: str = Field(default="redis://localhost:6379", description="Redis连接URL")
    memory_cache_size: int = Field(default=10000, description="内存缓存大小")
    cache_ttl: int = Field(default=3600, description="缓存生存时间（秒）")
    cache_prefix: str = Field(default="ai_router:", description="缓存键前缀")

    class Config:
        env_prefix = "CACHE_"


class MonitoringConfig(BaseSettings):
    """监控配置"""

    enabled: bool = Field(default=True, description="是否启用监控")
    collection_interval: float = Field(default=1.0, description="指标收集间隔（秒）")
    metrics_retention: int = Field(default=10000, description="指标保留数量")
    alert_enabled: bool = Field(default=True, description="是否启用告警")
    prometheus_enabled: bool = Field(default=True, description="是否启用Prometheus指标")

    # 告警阈值
    cpu_threshold: float = Field(default=80.0, description="CPU使用率告警阈值")
    memory_threshold: float = Field(default=85.0, description="内存使用率告警阈值")
    disk_threshold: float = Field(default=90.0, description="磁盘使用率告警阈值")
    response_time_threshold: float = Field(default=5.0, description="响应时间告警阈值")
    error_rate_threshold: float = Field(default=5.0, description="错误率告警阈值")

    class Config:
        env_prefix = "MONITORING_"


class MicroserviceConfig(BaseSettings):
    """微服务配置"""

    enabled: bool = Field(default=False, description="是否启用微服务架构")
    service_discovery: bool = Field(default=True, description="是否启用服务发现")
    circuit_breaker: bool = Field(default=True, description="是否启用熔断器")
    retry_policy: bool = Field(default=True, description="是否启用重试策略")

    # 服务配置
    gateway_replicas: int = Field(default=2, description="网关副本数")
    loadbalancer_replicas: int = Field(default=3, description="负载均衡器副本数")
    model_manager_replicas: int = Field(default=2, description="模型管理器副本数")
    provider_manager_replicas: int = Field(default=2, description="提供商管理器副本数")

    class Config:
        env_prefix = "MICROSERVICE_"


class PerformanceConfig(BaseSettings):
    """性能配置"""

    optimization_level: OptimizationLevel = Field(
        default=OptimizationLevel.BASIC, description="优化级别"
    )

    # 异步配置
    max_concurrent_requests: int = Field(default=1000, description="最大并发请求数")
    request_timeout: float = Field(default=30.0, description="请求超时时间（秒）")
    max_workers: int = Field(default=4, description="最大工作线程数")

    # 批处理配置
    batch_processing: bool = Field(default=True, description="是否启用批处理")
    batch_size: int = Field(default=100, description="批处理大小")
    batch_timeout: float = Field(default=5.0, description="批处理超时时间（秒）")

    # 预加载配置
    preload_models: bool = Field(default=True, description="是否预加载模型")
    preload_providers: bool = Field(default=True, description="是否预加载提供商")
    warmup_requests: int = Field(default=10, description="预热请求数量")

    class Config:
        env_prefix = "PERFORMANCE_"


class OptimizationSettings(BaseSettings):
    """优化设置主配置"""

    # 优化级别
    level: OptimizationLevel = OptimizationLevel.BASIC

    # 各模块配置
    connection_pool: ConnectionPoolConfig = ConnectionPoolConfig()
    load_balancing: LoadBalancingConfig = LoadBalancingConfig()
    database: DatabaseConfig = DatabaseConfig()
    caching: CachingConfig = CachingConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    microservice: MicroserviceConfig = MicroserviceConfig()
    performance: PerformanceConfig = PerformanceConfig()

    # 环境特定配置
    environment: str = Field(default="production", description="运行环境")
    debug: bool = Field(default=False, description="是否启用调试模式")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_optimization_config(self) -> Dict[str, Any]:
        """获取优化配置"""
        config = {
            "level": self.level,
            "environment": self.environment,
            "debug": self.debug,
            "connection_pool": self.connection_pool.dict(),
            "load_balancing": self.load_balancing.dict(),
            "database": self.database.dict(),
            "caching": self.caching.dict(),
            "monitoring": self.monitoring.dict(),
            "microservice": self.microservice.dict(),
            "performance": self.performance.dict(),
        }

        # 根据优化级别调整配置
        if self.level == OptimizationLevel.ADVANCED:
            config = self._apply_advanced_optimizations(config)
        elif self.level == OptimizationLevel.AGGRESSIVE:
            config = self._apply_aggressive_optimizations(config)

        return config

    def _apply_advanced_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用高级优化"""
        # 增加连接池大小
        config["connection_pool"]["max_pool_size"] = 30
        config["connection_pool"]["num_shards"] = 32

        # 优化数据库配置
        config["database"]["pool_size"] = 30
        config["database"]["max_overflow"] = 50

        # 启用更多监控
        config["monitoring"]["collection_interval"] = 0.5

        return config

    def _apply_aggressive_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用激进优化"""
        # 最大化连接池
        config["connection_pool"]["max_pool_size"] = 50
        config["connection_pool"]["num_shards"] = 64

        # 最大化数据库连接
        config["database"]["pool_size"] = 50
        config["database"]["max_overflow"] = 100

        # 最频繁的监控
        config["monitoring"]["collection_interval"] = 0.1

        # 启用微服务
        config["microservice"]["enabled"] = True

        return config

    def validate_config(self) -> List[str]:
        """验证配置"""
        errors = []

        # 验证连接池配置
        if self.connection_pool.max_pool_size < self.connection_pool.min_pool_size:
            errors.append("最大连接池大小不能小于最小连接池大小")

        if self.connection_pool.num_shards <= 0:
            errors.append("连接池分片数量必须大于0")

        # 验证数据库配置
        if self.database.pool_size <= 0:
            errors.append("数据库连接池大小必须大于0")

        if self.database.batch_size <= 0:
            errors.append("批处理大小必须大于0")

        # 验证监控配置
        if self.monitoring.collection_interval <= 0:
            errors.append("指标收集间隔必须大于0")

        if self.monitoring.metrics_retention <= 0:
            errors.append("指标保留数量必须大于0")

        return errors


# 全局优化配置实例
optimization_settings = OptimizationSettings()


def get_optimization_config() -> OptimizationSettings:
    """获取优化配置实例"""
    return optimization_settings


def get_optimization_config_dict() -> Dict[str, Any]:
    """获取优化配置字典"""
    return optimization_settings.get_optimization_config()


# 配置验证
def validate_optimization_config() -> bool:
    """验证优化配置"""
    errors = optimization_settings.validate_config()
    if errors:
        for error in errors:
            print(f"配置错误: {error}")
        return False
    return True


if __name__ == "__main__":
    # 测试配置
    if validate_optimization_config():
        print("✅ 优化配置验证通过")
        config = get_optimization_config_dict()
        print(f"优化级别: {config['level']}")
        print(f"连接池大小: {config['connection_pool']['max_pool_size']}")
        print(f"数据库连接池: {config['database']['pool_size']}")
    else:
        print("❌ 优化配置验证失败")
