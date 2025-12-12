# src/config.py -> 'Configuración GLOBAL (sin credenciales de clientes)'

import os
from .utils import setup_logging

logger = setup_logging()

class Config:
    """
    Gestiona la configuración GLOBAL del lambda.
    
    NOTA IMPORTANTE:
    Las credenciales específicas de cada cliente (tenant_id, client_id, client_secret)
    YA NO se leen de variables de entorno. Ahora vienen de DynamoDB.
    
    Este config solo contiene configuración global del sistema.
    """
    
    def __init__(self):
        # Configuración de DynamoDB
        self.dynamodb_table = os.getenv('DYNAMODB_TABLE', 'MCP_ClientConfigurations')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-2')
        
        # Configuración global
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.lambda_version = os.getenv('LAMBDA_VERSION', '2.0.0-multitenant')
        
        # Webhook URL base (puede ser la misma para todos los clientes)
        # Si cada cliente necesita URL diferente, esto viene de DynamoDB
        self.webhook_url_base = os.getenv('WEBHOOK_URL_BASE')
    
    def validate(self) -> bool:
        """
        Valida configuración global (ya NO valida credenciales de clientes).
        
        Returns:
            bool: True si la configuración global es válida
        """
        # Solo validar configuración global
        if not self.dynamodb_table:
            logger.error("DYNAMODB_TABLE no está configurado")
            return False
        
        logger.info("Configuración global validada exitosamente")
        return True
    
    def get_summary(self) -> dict:
        """
        Retorna un resumen de la configuración global (sin secretos).
        
        Returns:
            dict: Configuraciones resumidas
        """
        return {
            'dynamodb_table': self.dynamodb_table,
            'aws_region': self.aws_region,
            'webhook_url_base': self.webhook_url_base or 'N/A',
            'log_level': self.log_level,
            'lambda_version': self.lambda_version
        }
    
    def log_config(self) -> None:
        """Log de configuración actual"""
        logger.info("Configuración Global:")
        logger.info(f"  DynamoDB Table: {self.dynamodb_table}")
        logger.info(f"  AWS Region: {self.aws_region}")
        logger.info(f"  Webhook URL Base: {self.webhook_url_base or 'N/A'}")
        logger.info(f"  Log Level: {self.log_level}")
        logger.info(f"  Version: {self.lambda_version}")