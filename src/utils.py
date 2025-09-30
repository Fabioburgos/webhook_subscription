# src/utils.py -> 'Utilidades y Helpers'

import os
import sys
import logging
from typing import Optional
from datetime import datetime, timezone

def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configura el sistema de logging para lambda.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado.
    """
    # Obtener nivel desde variable de entorno o parámetro
    log_level = level or os.getenv('LOG_LEVEL', 'INFO').upper()

    # Configurar formato
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Configurar logging
    logging.basicConfig(
        level = getattr(logging, log_level.upper()),
        format = log_format,
        stream = sys.stdout
    )

    # Obtener logger principal
    logger = logging.getLogger('subscription_renewal')

    # Configurar loggers de terceros
    requests_logger = logging.getLogger('requests')
    requests_logger.setLevel(logging.WARNING)
    
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.WARNING)
    
    logger.info(f"Logging configurado en nivel: {log_level}")
    
    return logger

def get_utc_timestamp() -> str:
    """
    Obtiene timestamp UTC actual en formato ISO.
    
    Returns:
        str: Timestamp en formato ISO.
    """
    try:
        return datetime.now(timezone.utc).isoformat()
    except ImportError:
        return datetime.utcnow().isoformat() + 'Z' # Fallback para versiones anteriores de Python
    
def safe_get_nested(data: dict, keys: list, default=None):
    """
    Obtiene valores anidados de un diccionario de forma segura.
    
    Args:
        data: Diccionario fuente.
        keys: Lista de claves para navegar.
        default: Valor por defecto si no se encuentra.
        
    Returns:
        Valor encontrado o default.
    """
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError, AttributeError):
        return default

def format_subscription_info(subscription: dict) -> str:
    """
    Formatea información de suscripción para logging.
    
    Args:
        subscription: Diccionario con datos de suscripción.
        
    Returns:
        str: Información formateada.
    """
    sub_id = subscription.get('id', 'N/A')[:20]
    resource = subscription.get('resource', 'N/A')
    client_state = subscription.get('clientState', 'N/A')
    expiration = subscription.get('expirationDateTime', 'N/A')
    
    # Determinar tipo
    if 'inbox' in resource.lower():
        sub_type = 'INBOX'
    elif 'hil' in resource.lower() or 'hil' in client_state.lower():
        sub_type = 'HIL'
    else:
        sub_type = 'OTHER'
    
    return f"[{sub_type}] {sub_id}... (expira: {expiration})"

def calculate_next_renewal_time(hours_before_expiry: int = 12) -> datetime:
    """
    Calcula el próximo tiempo de renovación.
    
    Args:
        hours_before_expiry: Horas antes del vencimiento para renovar.
        
    Returns:
        datetime: Próximo tiempo de renovación.
    """
    try:
        # Suscripciones duran ~3 días, renovar 12 horas antes
        from datetime import timedelta
        next_renewal = datetime.now(timezone.utc) + timedelta(days = 2, hours = 12)
        return next_renewal
    except ImportError:
        from datetime import timedelta
        next_renewal = datetime.utcnow() + timedelta(days = 2, hours = 12)
        return next_renewal

def is_subscription_expired(expiration_str: str, buffer_hours: int = 2) -> bool:
    """
    Verifica si una suscripción está próxima a expirar.
    
    Args:
        expiration_str: Fecha de expiración en formato ISO.
        buffer_hours: Horas de buffer para considerar "próximo a expirar".
        
    Returns:
        bool: True si está próxima a expirar.
    """
    try:
        # Parse de fecha de expiración
        if expiration_str.endswith('Z'):
            expiration_str = expiration_str[:-1] + '+00:00'
        
        expiration_date = datetime.fromisoformat(expiration_str)
        
        # Tiempo actual
        try:
            now = datetime.now(timezone.utc)
        except ImportError:
            now = datetime.utcnow().replace(tzinfo = timezone.utc)
        
        # Verificar si expira en las próximas X horas
        from datetime import timedelta
        time_until_expiry = expiration_date - now
        
        return time_until_expiry <= timedelta(hours=buffer_hours)
        
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error verificando expiración: {e}")
        # En caso de error, asumir que necesita renovación
        return True
    
class LambdaResponse:
    """ Helper para generar respuestas consistentes de Lambda. """

    @staticmethod
    def success(data: Optional[dict] = None, status_code: int = 200) -> dict:
        """Genera respuesta exitosa"""
        body = {
            'success': True,
            'timestamp': get_utc_timestamp()
        }
        if data:
            # Evitar sobreescribir campos críticos
            for k, v in data.items():
                if k not in ('success', 'timestamp'):
                    body[k] = v

        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'X-Lambda-Function': 'subscription-renewal'
            },
            'body': body
        }

    @staticmethod
    def error(error_message: str, details: Optional[dict] = None, status_code: int = 500) -> dict:
        """Genera respuesta de error"""
        body = {
            'success': False,
            'error': error_message,
            'timestamp': get_utc_timestamp()
        }

        if details:
            body['details'] = details

        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'X-Lambda-Function': 'subscription-renewal'
            },
            'body': body
        }