"""
模型能力管理模块
提供模型能力的增删改查功能
"""

import time
from typing import Dict, List, Any, Optional
from fastapi import HTTPException
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class CapabilityService:
    """模型能力管理服务"""
    
    def __init__(self):
        """初始化能力管理服务"""
        pass
    
    def get_all_capabilities(self) -> Dict[str, Any]:
        """
        获取所有可用能力
        
        Returns:
            能力列表响应
        """
        try:
            capabilities = db_service.get_all_capabilities()
            
            return {
                "object": "list",
                "data": capabilities,
                "total_capabilities": len(capabilities),
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Get all capabilities failed: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Get all capabilities failed: {str(e)}"
            )
    
    def get_model_capabilities(self, model_name: str) -> Dict[str, Any]:
        """
        获取指定模型的能力
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型能力信息
        """
        try:
            # 获取模型对象
            model = db_service.get_model_by_name(model_name)
            if not model:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Model does not exist: {model_name}"
                )
            
            # 获取模型能力
            capabilities = db_service.get_model_capabilities(model.id)
            
            return {
                "model_name": model_name,
                "model_id": model.id,
                "capabilities": capabilities,
                "capabilities_count": len(capabilities),
                "timestamp": time.time(),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get model capabilities failed: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Get model capabilities failed: {str(e)}"
            )
    
    def add_model_capability(self, model_name: str, capability_name: str) -> Dict[str, Any]:
        """
        为模型添加能力
        
        Args:
            model_name: 模型名称
            capability_name: 能力名称
            
        Returns:
            操作结果
        """
        try:
            # 获取模型对象
            model = db_service.get_model_by_name(model_name)
            if not model:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Model does not exist: {model_name}"
                )
            
            # 添加能力
            success = db_service.add_model_capability(model.id, capability_name)
            
            if success:
                return {
                    "message": f"Capability {capability_name} added to model {model_name}",
                    "model_name": model_name,
                    "capability_name": capability_name,
                    "timestamp": time.time(),
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to add capability {capability_name} to model {model_name}",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Add model capability failed: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Add model capability failed: {str(e)}"
            )
    
    def remove_model_capability(self, model_name: str, capability_name: str) -> Dict[str, Any]:
        """
        从模型移除能力
        
        Args:
            model_name: 模型名称
            capability_name: 能力名称
            
        Returns:
            操作结果
        """
        try:
            # 获取模型对象
            model = db_service.get_model_by_name(model_name)
            if not model:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Model does not exist: {model_name}"
                )
            
            # 移除能力
            success = db_service.remove_model_capability(model.id, capability_name)
            
            if success:
                return {
                    "message": f"Capability {capability_name} removed from model {model_name}",
                    "model_name": model_name,
                    "capability_name": capability_name,
                    "timestamp": time.time(),
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to remove capability {capability_name} from model {model_name}",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Remove model capability failed: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Remove model capability failed: {str(e)}"
            )
    
    def get_capability_stats(self) -> Dict[str, Any]:
        """
        获取能力统计信息
        
        Returns:
            能力统计信息
        """
        try:
            all_capabilities = db_service.get_all_capabilities()
            
            # 统计能力使用情况
            capability_usage = {}
            for cap in all_capabilities:
                cap_name = cap['capability_name']
                capability_usage[cap_name] = {
                    "name": cap_name,
                    "description": cap.get('description', ''),
                    "usage_count": 0,  # 这里可以扩展统计实际使用次数
                    "models": []  # 这里可以扩展统计使用该能力的模型
                }
            
            return {
                "total_capabilities": len(all_capabilities),
                "capabilities": list(capability_usage.values()),
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Get capability stats failed: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Get capability stats failed: {str(e)}"
            )


# 全局能力管理服务实例
capability_service = CapabilityService()
