# handler.py -> 'Lambda handler principal (MULTI-TENANT)'

import json
from typing import Dict, Any
from datetime import datetime
from src.utils import setup_logging
from src.dynamodb_client import DynamoDBClient
from src.subscription_manager import MultiTenantSubscriptionManager

logger = setup_logging()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal del lambda para renovar suscripciones automáticamente.
    
    MULTI-TENANT VERSION:
    - Lee TODOS los clientes activos desde DynamoDB
    - Procesa cada cliente con SUS credenciales
    - Crea/renueva suscripciones según sea necesario
    - Actualiza DynamoDB con subscription_ids reales

    Args:
        event: Evento de EventBridge (cada 2 días)
        context: Contexto de Lambda
    
    Returns:
        Dict con el resultado de la ejecución
    """
    try:
        logger.info("="*60)
        logger.info("LAMBDA MULTI-TENANT SUBSCRIPTION MANAGER")
        logger.info("="*60)
        logger.info(f"Evento recibido: {json.dumps(event, default = str)}")
        logger.info("")
        
        # Crear instancia del gestor multi-tenant
        manager = MultiTenantSubscriptionManager()
        
        # Procesar TODOS los clientes
        results = manager.process_all_subscriptions()
        
        # Preparar respuesta
        success = results.get('success', False)
        status_code = 200 if success else 500
        
        logger.info("")
        logger.info("="*60)
        logger.info(f"PROCESO COMPLETADO - Success: {success}")
        logger.info("="*60)
        
        return {
            "statusCode": status_code,
            "body": json.dumps({
                "success": success,
                "results": results,
                "timestamp": datetime.now().isoformat(),
                "execution_id": context.aws_request_id if hasattr(context, 'aws_request_id') else 'unknown'
            }, default = str)
        }
    
    except Exception as e:
        logger.exception(f"Error crítico en lambda_handler: {str(e)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": f"Error crítico: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "execution_id": getattr(context, 'aws_request_id', 'unknown')
            })
        }

def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler para verificación de salud del lambda.
    """
    try:
        # Verificar conexión a DynamoDB
        db_client = DynamoDBClient()
        clients = db_client.get_all_active_clients()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "dynamodb_connection": "OK",
                "active_clients": len(clients)
            })
        }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        }