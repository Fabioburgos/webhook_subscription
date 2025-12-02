# src/config.py -> 'Configuración y variables de entorno'

import os
from .utils import setup_logging

logger = setup_logging()

class Config:
    """ Gestiona la configuración del lambda desde variables de entorno. """

    def __init__(self):
        # Microsoft Graph API Credentials
        self.tenant_id = os.getenv('MS_TENANT_ID')
        self.client_id = os.getenv('MS_CLIENT_ID')
        self.client_secret = os.getenv('MS_CLIENT_SECRET')

        # Target configuration
        self.target_user_email = os.getenv('TARGET_USER_EMAIL')

        # WEBHOOK URLS - Solo INBOX activo
        # -----------------------------------------------------------------
        # URL para notificaciones de INBOX
        self.webhook_url_inbox = os.getenv('WEBHOOK_URL_INBOX')

        # HIL deshabilitado (ya no se usa)
        # self.webhook_url_hil = os.getenv('WEBHOOK_URL_HIL')
        # -----------------------------------------------------------------

        # Optional configurations
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.lambda_version = os.getenv('LAMBDA_VERSION', '1.0.0')

        # HIL configuration (for reference)
        self.hil_forward_email = os.getenv('HIL_FORWARD_TO_EMAIL')
    
    def validate(self) -> bool:
        """
        Valida que todas las configuraciones requeridas estén presentes.

        Returns:
            bool: True si la configuración es válida.
        """
        required_fields = {
            'MS_TENANT_ID': self.tenant_id,
            'MS_CLIENT_ID': self.client_id,
            'MS_CLIENT_SECRET': self.client_secret,
            'TARGET_USER_EMAIL': self.target_user_email,
            # Solo validar INBOX (HIL deshabilitado)
            'WEBHOOK_URL_INBOX': self.webhook_url_inbox
        }

        missing_fields = []

        for field_name, field_value in required_fields.items():
            if not field_value:
                missing_fields.append(field_name)

        if missing_fields:
            logger.error(f"Variables de entorno faltantes: {', '.join(missing_fields)}")
            return False

        # Validaciones adicionales
        if not self._validate_email(self.target_user_email):
            logger.error(f"Email objetivo inválido: {self.target_user_email}")
            return False

        # Validar URL de INBOX
        if not self._validate_url(self.webhook_url_inbox):
            logger.error(f"URL de webhook INBOX inválida: {self.webhook_url_inbox}")
            return False

        logger.info("Configuración validada exitosamente")
        return True
    
    def _validate_email(self, email: str) -> bool:
        """
        Valida formato básico de email.
        """
        return '@' in email and '.' in email.split('@')[-1]
    
    def _validate_url(self, url: str) -> bool:
        """
        Valida formato básico de URL.
        """
        # Incluir tanto http como https
        return (url.startswith("http://") or url.startswith("https://")) and len(url) > 10

    def get_summary(self) -> dict:
        """
        Retorna un resumen de la configuración (sin secretos).

        Returns:
            dict: Configuraciones resumidas.
        """
        return {
            'tenant_id': self.tenant_id,
            'client_id': self.client_id,
            'client_secret_set': bool(self.client_secret),
            'target_user_email': self.target_user_email,
            # Solo INBOX activo
            'webhook_url_inbox': self.webhook_url_inbox,
            'hil_forward_email': self.hil_forward_email,
            'log_level': self.log_level,
            'lambda_version': self.lambda_version
        }
    
    def log_config(self) -> None:
        """
        Log de configuración actual (sin secretos).
        """
        logger.info("Configuración actual:")
        logger.info(f"Tenant: {self.tenant_id}")
        logger.info(f"Client: {self.client_id}")
        logger.info(f"Usuario objetivo: {self.target_user_email}")
        # Solo INBOX activo
        logger.info(f"Webhook URL INBOX: {self.webhook_url_inbox}")
        logger.info(f"HIL forward: {self.hil_forward_email or 'No configurado'}")
        logger.info(f"Log Level: {self.log_level}")