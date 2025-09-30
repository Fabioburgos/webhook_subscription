# handler.py -> 'Lambda handler principal'

import os
import json
from typing import Dict, Any
from datetime import datetime
from src.config import Config
from src.utils import setup_logging
from src.subscription_manager import SubscriptionManager

logger = setup_logging()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal del lambda para renovar suscripciones automáticamente.

    Args:
        event: Evento de EventBridge.
        context: Contexto de Lambda.
    
    Returns:
        Dict con el resultado de la ejecución.
    """
    try:
        logger.info("Iniciando renovación automática de suscripciones")
        logger.info(f"Evento recibido: {json.dumps(event, default = str)}")

        # Validar configuración
        config = Config()
        if not config.validate():
            logger.error("Configuración inválida")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Configuración inválida",
                    "timestamp": datetime.now().isoformat()
                })
            }
        
        # Crear instancia del gestor de suscripciones con el objeto config
        subscription_manager = SubscriptionManager(config)

        # Obtener token de acceso
        logger.info("Obteniendo token de acceso...")
        if not subscription_manager.get_access_token():
            logger.error("Error obteniendo token de acceso")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Error de autenticación",
                    "timestamp": datetime.now().isoformat()
                })
            }
        
        # Procesar suscripciones
        results = subscription_manager.process_subscriptions()

        # Preparar respuesta
        success = results['success']
        status_code = 200 if success else 500

        logger.info(f"Proceso completado con éxito: {success}")

        return {
            "statusCode": status_code,
            "body": json.dumps({
                "success": success,
                "results": results,
                "timestamp": datetime.now().isoformat(),
                "execution_id": context.aws_request_id if hasattr(context, 'aws_request_id') else 'unknown'
            }, default=str)
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
        config = Config()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "config_valid": config.validate(),
                "version": os.getenv("LAMBDA_VERSION", "1.0.0")
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