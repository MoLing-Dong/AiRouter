from typing import Dict, Any, Optional
from app.services.database_service import db_service


class ModelDatabaseService:
    """模型数据库服务 - 专门处理与数据库相关的操作"""

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """从数据库获取所有模型配置"""
        try:
            return db_service.get_all_model_configs_from_db()
        except Exception as e:
            print(f"从数据库获取模型配置失败: {e}")
            return {}

    def get_api_key_for_provider(self, provider_name: str) -> str:
        """根据提供商名称获取API密钥（优先从数据库获取）"""
        # 首先尝试从数据库获取
        api_key = self._get_api_key_from_database(provider_name)
        if api_key:
            return api_key

        # 如果数据库中没有，则从settings获取（作为备用）
        return self._get_api_key_from_settings(provider_name)

    def _get_api_key_from_database(self, provider_name: str) -> str:
        """从数据库获取提供商的最佳API密钥"""
        try:
            # 根据提供商名称获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                print(f"警告: 数据库中未找到提供商: {provider_name}")
                return ""

            # 获取最佳API密钥
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                print(f"警告: 提供商 {provider_name} 没有可用的API密钥")
                return ""

            return api_key_obj.api_key

        except Exception as e:
            print(f"从数据库获取API密钥失败: {provider_name} - {e}")
            return ""

    def _get_api_key_from_settings(self, provider_name: str) -> str:
        """从settings获取API密钥（备用方案）"""
        try:
            from config.settings import settings

            # 尝试从settings获取API密钥
            api_key_attr = f"{provider_name.upper().replace('-', '_')}_API_KEY"
            api_key = getattr(settings, api_key_attr, "")

            if not api_key:
                # 尝试其他常见的API密钥属性名
                common_attrs = [
                    f"{provider_name.upper()}_API_KEY",
                    f"{provider_name.replace('-', '_').upper()}_API_KEY",
                    f"{provider_name.replace('-', '').upper()}_API_KEY",
                ]

                for attr in common_attrs:
                    api_key = getattr(settings, attr, "")
                    if api_key:
                        break

            return api_key

        except Exception as e:
            print(f"从settings获取API密钥失败: {provider_name} - {e}")
            return ""

    def get_provider_by_name(self, provider_name: str):
        """根据名称获取提供商"""
        return db_service.get_provider_by_name(provider_name)

    def get_best_api_key(self, provider_id: int):
        """获取最佳API密钥"""
        return db_service.get_best_api_key(provider_id)
