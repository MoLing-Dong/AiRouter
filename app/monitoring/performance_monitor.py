"""
性能监控系统

实时监控系统性能，收集关键指标，提供性能分析和优化建议
"""

import time
import asyncio
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics
from prometheus_client import Counter, Histogram, Gauge, Summary
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


@dataclass
class PerformanceMetric:
    """性能指标数据"""

    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """性能告警"""

    timestamp: float
    metric_name: str
    current_value: float
    threshold: float
    severity: str  # low, medium, high, critical
    message: str


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        # 指标存储
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.alerts: List[PerformanceAlert] = []

        # 监控配置
        self.monitoring_enabled = True
        self.collection_interval = 1.0  # 1秒收集一次
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "response_time": 5.0,
            "error_rate": 5.0,
        }

        # 监控任务
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()

        # Prometheus指标
        self._init_prometheus_metrics()

        # 性能分析器
        self.performance_analyzer = PerformanceAnalyzer()

        # 告警处理器
        self.alert_handler = AlertHandler()

    def _init_prometheus_metrics(self):
        """初始化Prometheus指标"""
        # 系统指标
        self.cpu_gauge = Gauge("system_cpu_usage_percent", "CPU usage percentage")
        self.memory_gauge = Gauge(
            "system_memory_usage_percent", "Memory usage percentage"
        )
        self.disk_gauge = Gauge("system_disk_usage_percent", "Disk usage percentage")

        # 应用指标
        self.request_counter = Counter(
            "app_requests_total", "Total requests", ["endpoint", "method"]
        )
        self.response_time_histogram = Histogram(
            "app_response_time_seconds", "Response time in seconds", ["endpoint"]
        )
        self.error_counter = Counter(
            "app_errors_total", "Total errors", ["endpoint", "error_type"]
        )

        # 业务指标
        self.active_connections_gauge = Gauge(
            "app_active_connections", "Active connections"
        )
        self.queue_size_gauge = Gauge("app_queue_size", "Queue size")
        self.cache_hit_rate_gauge = Gauge("app_cache_hit_rate", "Cache hit rate")

    async def start(self):
        """启动性能监控"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("🚀 Performance monitoring started")

    async def stop(self):
        """停止性能监控"""
        self._stop_event.set()
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("🛑 Performance monitoring stopped")

    async def _monitoring_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                # 收集系统指标
                await self._collect_system_metrics()

                # 收集应用指标
                await self._collect_application_metrics()

                # 分析性能
                await self._analyze_performance()

                # 检查告警
                await self._check_alerts()

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self._record_metric("cpu_usage", cpu_percent, {"type": "system"})
            self.cpu_gauge.set(cpu_percent)

            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self._record_metric("memory_usage", memory_percent, {"type": "system"})
            self.memory_gauge.set(memory_percent)

            # 磁盘使用率
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            self._record_metric("disk_usage", disk_percent, {"type": "system"})
            self.disk_gauge.set(disk_percent)

            # 网络IO
            net_io = psutil.net_io_counters()
            self._record_metric(
                "network_bytes_sent", net_io.bytes_sent, {"type": "system"}
            )
            self._record_metric(
                "network_bytes_recv", net_io.bytes_recv, {"type": "system"}
            )

            # 进程信息
            process = psutil.Process()
            self._record_metric(
                "process_cpu_percent", process.cpu_percent(), {"type": "process"}
            )
            self._record_metric(
                "process_memory_percent", process.memory_percent(), {"type": "process"}
            )

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    async def _collect_application_metrics(self):
        """收集应用指标"""
        try:
            # 这里收集应用特定的指标
            # 例如：连接数、队列大小、缓存命中率等

            # 模拟一些应用指标
            active_connections = len(asyncio.all_tasks())
            self._record_metric(
                "active_connections", active_connections, {"type": "application"}
            )
            self.active_connections_gauge.set(active_connections)

            # 队列大小（如果有的话）
            queue_size = 0  # 这里应该从实际的队列获取
            self._record_metric("queue_size", queue_size, {"type": "application"})
            self.queue_size_gauge.set(queue_size)

        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")

    def _record_metric(self, name: str, value: float, tags: Dict[str, str]):
        """记录指标"""
        metric = PerformanceMetric(timestamp=time.time(), value=value, tags=tags)
        self.metrics[name].append(metric)

    async def _analyze_performance(self):
        """分析性能"""
        try:
            analysis = await self.performance_analyzer.analyze(self.metrics)

            # 记录分析结果
            for metric_name, result in analysis.items():
                if "trend" in result:
                    self._record_metric(
                        f"{metric_name}_trend", result["trend"], {"type": "analysis"}
                    )

                if "anomaly_score" in result:
                    self._record_metric(
                        f"{metric_name}_anomaly",
                        result["anomaly_score"],
                        {"type": "analysis"},
                    )

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")

    async def _check_alerts(self):
        """检查告警"""
        try:
            for metric_name, threshold in self.alert_thresholds.items():
                if metric_name in self.metrics and self.metrics[metric_name]:
                    latest_metric = self.metrics[metric_name][-1]

                    if latest_metric.value > threshold:
                        alert = PerformanceAlert(
                            timestamp=latest_metric.timestamp,
                            metric_name=metric_name,
                            current_value=latest_metric.value,
                            threshold=threshold,
                            severity=self._get_severity(latest_metric.value, threshold),
                            message=f"{metric_name} exceeded threshold: {latest_metric.value:.2f} > {threshold:.2f}",
                        )

                        await self.alert_handler.handle_alert(alert)
                        self.alerts.append(alert)

        except Exception as e:
            logger.error(f"Alert checking failed: {e}")

    def _get_severity(self, value: float, threshold: float) -> str:
        """获取告警严重程度"""
        ratio = value / threshold
        if ratio >= 2.0:
            return "critical"
        elif ratio >= 1.5:
            return "high"
        elif ratio >= 1.2:
            return "medium"
        else:
            return "low"

    def record_request(
        self, endpoint: str, method: str, response_time: float, success: bool
    ):
        """记录请求指标"""
        # Prometheus指标
        self.request_counter.labels(endpoint=endpoint, method=method).inc()
        self.response_time_histogram.labels(endpoint=endpoint).observe(response_time)

        if not success:
            self.error_counter.labels(
                endpoint=endpoint, error_type="request_failed"
            ).inc()

        # 内部指标
        self._record_metric(
            "response_time",
            response_time,
            {"endpoint": endpoint, "method": method, "success": str(success)},
        )

        if not success:
            self._record_metric(
                "error_rate", 1.0, {"endpoint": endpoint, "method": method}
            )

    def get_metrics_summary(
        self, metric_name: str, duration: int = 3600
    ) -> Dict[str, Any]:
        """获取指标摘要"""
        if metric_name not in self.metrics:
            return {}

        cutoff_time = time.time() - duration
        recent_metrics = [
            m for m in self.metrics[metric_name] if m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return {}

        values = [m.value for m in recent_metrics]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "latest": values[-1] if values else 0,
            "trend": self._calculate_trend(values),
        }

    def _calculate_trend(self, values: List[float]) -> float:
        """计算趋势（正值表示上升，负值表示下降）"""
        if len(values) < 2:
            return 0.0

        # 使用线性回归计算趋势
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * v for i, v in enumerate(values))
        x2_sum = sum(i * i for i in range(n))

        try:
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
            return slope
        except ZeroDivisionError:
            return 0.0

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": {},
            "application_metrics": {},
            "alerts": [],
            "recommendations": [],
        }

        # 系统指标摘要
        for metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
            if metric_name in self.metrics:
                report["system_metrics"][metric_name] = self.get_metrics_summary(
                    metric_name, 300
                )  # 5分钟

        # 应用指标摘要
        for metric_name in ["response_time", "active_connections", "queue_size"]:
            if metric_name in self.metrics:
                report["application_metrics"][metric_name] = self.get_metrics_summary(
                    metric_name, 300
                )

        # 告警摘要
        recent_alerts = [
            alert
            for alert in self.alerts
            if alert.timestamp >= time.time() - 3600  # 1小时内的告警
        ]
        report["alerts"] = [
            {
                "timestamp": datetime.fromtimestamp(alert.timestamp).isoformat(),
                "metric": alert.metric_name,
                "severity": alert.severity,
                "message": alert.message,
            }
            for alert in recent_alerts
        ]

        # 性能建议
        report["recommendations"] = self._generate_recommendations()

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        # CPU使用率建议
        cpu_summary = self.get_metrics_summary("cpu_usage", 300)
        if cpu_summary and cpu_summary.get("mean", 0) > 70:
            recommendations.append("CPU使用率较高，建议优化代码或增加CPU资源")

        # 内存使用率建议
        memory_summary = self.get_metrics_summary("memory_usage", 300)
        if memory_summary and memory_summary.get("mean", 0) > 80:
            recommendations.append("内存使用率较高，建议检查内存泄漏或增加内存")

        # 响应时间建议
        response_summary = self.get_metrics_summary("response_time", 300)
        if response_summary and response_summary.get("mean", 0) > 2.0:
            recommendations.append("响应时间较长，建议优化数据库查询或增加缓存")

        # 错误率建议
        error_summary = self.get_metrics_summary("error_rate", 300)
        if error_summary and error_summary.get("mean", 0) > 1.0:
            recommendations.append("错误率较高，建议检查系统日志和错误处理")

        return recommendations


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        self.analysis_cache = {}
        self.cache_ttl = 60.0  # 缓存60秒

    async def analyze(self, metrics: Dict[str, deque]) -> Dict[str, Dict[str, Any]]:
        """分析性能指标"""
        analysis = {}

        for metric_name, metric_queue in metrics.items():
            if not metric_queue:
                continue

            # 检查缓存
            cache_key = f"{metric_name}_{len(metric_queue)}"
            if cache_key in self.analysis_cache:
                cache_entry = self.analysis_cache[cache_key]
                if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                    analysis[metric_name] = cache_entry["data"]
                    continue

            # 执行分析
            result = await self._analyze_metric(metric_name, metric_queue)

            # 缓存结果
            self.analysis_cache[cache_key] = {"timestamp": time.time(), "data": result}

            analysis[metric_name] = result

        return analysis

    async def _analyze_metric(
        self, metric_name: str, metric_queue: deque
    ) -> Dict[str, Any]:
        """分析单个指标"""
        if not metric_queue:
            return {}

        values = [m.value for m in metric_queue]
        timestamps = [m.timestamp for m in metric_queue]

        result = {}

        # 基础统计
        result["count"] = len(values)
        result["min"] = min(values)
        result["max"] = max(values)
        result["mean"] = statistics.mean(values)
        result["median"] = statistics.median(values)

        # 趋势分析
        if len(values) >= 2:
            result["trend"] = self._calculate_trend(values)
            result["trend_direction"] = (
                "increasing"
                if result["trend"] > 0
                else "decreasing" if result["trend"] < 0 else "stable"
            )

        # 异常检测
        if len(values) >= 10:
            result["anomaly_score"] = self._detect_anomalies(values)

        # 周期性分析
        if len(timestamps) >= 20:
            result["periodicity"] = self._detect_periodicity(timestamps, values)

        return result

    def _calculate_trend(self, values: List[float]) -> float:
        """计算趋势"""
        if len(values) < 2:
            return 0.0

        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * v for i, v in enumerate(values))
        x2_sum = sum(i * i for i in range(n))

        try:
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
            return slope
        except ZeroDivisionError:
            return 0.0

    def _detect_anomalies(self, values: List[float]) -> float:
        """检测异常值"""
        if len(values) < 10:
            return 0.0

        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0

        if std_dev == 0:
            return 0.0

        # 计算Z-score
        z_scores = [abs((v - mean) / std_dev) for v in values]
        max_z_score = max(z_scores)

        # 归一化到0-1范围
        return min(max_z_score / 3.0, 1.0)  # 3个标准差为阈值

    def _detect_periodicity(
        self, timestamps: List[float], values: List[float]
    ) -> Dict[str, Any]:
        """检测周期性"""
        if len(timestamps) < 20:
            return {}

        # 简单的周期性检测
        intervals = [
            timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))
        ]
        avg_interval = statistics.mean(intervals)

        # 计算间隔的一致性
        interval_variance = statistics.variance(intervals) if len(intervals) > 1 else 0
        consistency = max(0, 1 - (interval_variance / (avg_interval**2)))

        return {
            "avg_interval": avg_interval,
            "consistency": consistency,
            "is_periodic": consistency > 0.8,
        }


class AlertHandler:
    """告警处理器"""

    def __init__(self):
        self.alert_channels = []
        self.alert_history = []

    async def handle_alert(self, alert: PerformanceAlert):
        """处理告警"""
        # 记录告警历史
        self.alert_history.append(alert)

        # 根据严重程度处理
        if alert.severity in ["high", "critical"]:
            await self._handle_critical_alert(alert)
        elif alert.severity == "medium":
            await self._handle_medium_alert(alert)
        else:
            await self._handle_low_alert(alert)

        # 记录日志
        logger.warning(
            f"Performance alert: {alert.message} (severity: {alert.severity})"
        )

    async def _handle_critical_alert(self, alert: PerformanceAlert):
        """处理严重告警"""
        # 这里可以实现紧急通知逻辑
        # 例如：发送短信、邮件、Slack通知等
        pass

    async def _handle_medium_alert(self, alert: PerformanceAlert):
        """处理中等告警"""
        # 这里可以实现中等优先级通知逻辑
        pass

    async def _handle_low_alert(self, alert: PerformanceAlert):
        """处理低优先级告警"""
        # 这里可以实现低优先级通知逻辑
        pass

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取告警摘要"""
        cutoff_time = time.time() - (hours * 3600)
        recent_alerts = [
            alert for alert in self.alert_history if alert.timestamp >= cutoff_time
        ]

        severity_counts = defaultdict(int)
        for alert in recent_alerts:
            severity_counts[alert.severity] += 1

        return {
            "total_alerts": len(recent_alerts),
            "severity_distribution": dict(severity_counts),
            "recent_alerts": [
                {
                    "timestamp": datetime.fromtimestamp(alert.timestamp).isoformat(),
                    "metric": alert.metric_name,
                    "severity": alert.severity,
                    "message": alert.message,
                }
                for alert in recent_alerts[-10:]  # 最近10个告警
            ],
        }


# 全局性能监控实例
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控实例"""
    return performance_monitor
