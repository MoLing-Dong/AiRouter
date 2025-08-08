#!/usr/bin/env python3
"""
检查数据库状态脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database_service import db_service

def check_database():
    """检查数据库状态"""
    print("🔍 检查数据库状态...")
    
    try:
        # 检查提供商
        print("\n📊 提供商列表:")
        providers = db_service.get_all_providers()
        for provider in providers:
            print(f"  - {provider.id}: {provider.name} ({provider.provider_type}) - {provider.official_endpoint or provider.third_party_endpoint}")
        
        # 检查模型
        print("\n📊 模型列表:")
        models = db_service.get_all_models()
        for model in models:
            print(f"  - {model.id}: {model.name} (启用: {model.is_enabled})")
        
        # 检查模型-提供商关联
        print("\n📊 模型-提供商关联:")
        for model in models:
            model_providers = db_service.get_model_providers(model.id)
            if model_providers:
                print(f"  - {model.name}:")
                for mp in model_providers:
                    provider = db_service.get_provider_by_id(mp.provider_id)
                    if provider:
                        print(f"    * {provider.name} (模型: {mp.model_name}, 权重: {mp.weight})")
            else:
                print(f"  - {model.name}: 无关联提供商")
        
        # 检查API密钥
        print("\n📊 API密钥:")
        for provider in providers:
            api_keys = db_service.get_provider_api_keys(provider.id)
            if api_keys:
                print(f"  - {provider.name}:")
                for key in api_keys:
                    print(f"    * {key.name} (启用: {key.is_enabled}, 权重: {key.weight})")
            else:
                print(f"  - {provider.name}: 无API密钥")
        
        # 检查模型配置
        print("\n📊 模型配置:")
        configs = db_service.get_all_model_configs_from_db()
        for model_name, config in configs.items():
            print(f"  - {model_name}:")
            for provider in config.get("providers", []):
                print(f"    * {provider['name']} (模型: {provider.get('model', 'N/A')})")
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
