# src/subscription_manager.py -> 'Gestor de suscripciones'

import json
import base64
import requests
from .config import Config
from .utils import setup_logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

logger = setup_logging()

class SubscriptionManager:
    """ Gestiona las suscripciones de webhook de Microsoft Graph. """

    def __init__(self, config: Config):
        self.config = config
        self.access_token: Optional[str] = None
        self.base_url = "https://graph.microsoft.com/v1.0"

    def get_access_token(self) -> bool:
        """
        Obtiene un token de acceso usando Client Credentials Flow.

        Returns:
            bool: True si se obtuvo el token correctamente, False en caso contrario.
        """
        token_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.config.client_id,
            "scope": 'https://graph.microsoft.com/.default',
            'client_secret': self.config.client_secret,
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(token_url, data = data, timeout = 30)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")

            # Log de permisos (DEBUGGING)
            if self.access_token:
                self._log_token_permissions()
            
            logger.info("Token de acceso obtenido correctamente")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo token: {e}")
            return False
        
    def _log_token_permissions(self) -> None:
        """
        Log de permisos del token (para debugging)
        """
        try:
            token_parts = self.access_token.split('.')
            if len(token_parts) > 1:
                payload = token_parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                token_info = json.loads(decoded)
                roles = token_info.get('roles', [])
                logger.info(f"Permisos activos: {', '.join(roles)}")
        except Exception:
            logger.debug("No se pudieron decodificar los permisos del token")

    def _make_graph_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Hace una petición a Microsoft Graph API.

        Args:
            endpoint: Endpoint de la API.
            method: Método HTTP.
            data: Datos para POST/PATCH.
            params: Parámetros de query.

        Returns:
            Dict con la respuesta o None si hay error.
        """
        if not self.access_token:
            logger.error("No hay token de acceso disponible")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}/{endpoint}"

        try:
            if method.upper() == 'POST':
                response = requests.post(url, headers = headers, json = data, params = params, timeout = 30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers = headers, params = params, timeout = 30)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers = headers, json = data, params = params, timeout = 30)
            else:
                response = requests.get(url, headers = headers, params = params, timeout = 30)

            if response.status_code in [200, 201, 204]:
                try:
                    return response.json()
                except:
                    return {"success": True}
            else:
                logger.error(f'Error en petición: {response.status_code} - {response.text}')
                return None
                
        except Exception as e:
            logger.error(f'Excepción en petición: {str(e)}')
            return None
    
    def list_existing_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Lista las suscripciones existentes.
        
        Returns:
            List de suscripciones existentes.
        """
        logger.info("Obteniendo suscripciones existentes...")

        subscriptions_data = self._make_graph_request("/subscriptions")

        if subscriptions_data and 'value' in subscriptions_data:
            subscriptions = subscriptions_data['value']
            logger.info(f"Suscripciones encontradas: {len(subscriptions)}")

            for i, sub in enumerate(subscriptions, 1):
                resource = sub.get('resource', 'N/A')
                client_state = sub.get('clientState', 'N/A')
                expiration = sub.get('expirationDateTime', 'N/A')

                # Determinar tipo
                if 'inbox' in resource.lower():
                    sub_type = 'INBOX'
                elif 'hil' in resource.lower() or 'hil' in client_state.lower():
                    sub_type = 'HIL'
                else:
                    sub_type = 'OTHER'
                
                logger.info(f'{i}. [{sub_type}] ID: {sub.get("id", "N/A")[:20]}...')
                logger.info(f'Expira: {expiration}')

            return subscriptions
        
        else:
            logger.info("No hay suscripciones existentes.")
            return []
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """
        Elimina una suscripción.

        Args:
            subscription_id: ID de la suscripción.

        Returns:
            bool: True si se eliminó exitosamente.
        """
        logger.info(f"Eliminando suscripción...")

        result = self._make_graph_request(f"/subscriptions/{subscription_id}", "DELETE")

        if result is not None:
            logger.info(f"Suscripción eliminada exitosamente")
            return True
        else:
            logger.error(f"Error al eliminar suscripción")
            return False
    
    def create_inbox_subscription(self) -> Optional[Dict[str, Any]]:
        """
        Crea una nueva suscripción para INBOX

        Returns:
            Dict con la información de la suscripción o None si falla.
        """
        logger.info("Creando suscripción INBOX...")
        
        # Calcular expiración (máximo 4230 minutos para empresarial)
        try:
            expiration = datetime.now(timezone.utc) + timedelta(days=2, hours=23)
        
        except ImportError:
            expiration = datetime.utcnow() + timedelta(days=2, hours=23)
        
        expiration_str = expiration.strftime('%Y-%m-%dT%H:%M:%S.0000000Z')
        
        webhook_data = {
            "changeType": "created",  
            "notificationUrl": self.config.webhook_url,
            "resource": f"users/{self.config.target_user_email}/mailFolders/inbox/messages",
            "expirationDateTime": expiration_str,
            "clientState": "InboxSecretState123"
        }

        logger.info(f"Configurando suscripción INBOX que expira: {expiration_str}")

        result = self._make_graph_request("/subscriptions", "POST", webhook_data)

        if result and 'id' in result:
            logger.info(f"Suscripción INBOX creada: {result.get('id')}")
            return result
        else:
            logger.error("Error al crear suscripción INBOX")
            return None
    
    def get_or_create_hil_folder(self) -> Optional[str]:
        """
        Obtiene o crea la carpeta HIL.

        Returns:
            str: ID de la carpeta HIL o None si falla.
        """
        try:
            logger.info("Verificando carpeta HIL...")

            folders_data = self._make_graph_request(f'/users/{self.config.target_user_email}/mailFolders')

            if not folders_data or 'value' not in folders_data:
                logger.error("No se pudieron obtener las carpetas")
                return None
            
            # Buscar carpeta HIL
            for folder in folders_data['value']:
                folder_name = (folder.get('displayName') or '').lower()

                if folder_name == 'hil':
                    folder_id = folder.get('id')
                    logger.info(f'Carpeta HIL encontrada: {folder_id}')
                    return folder_id
            
            # Si no existe, crearla
            logger.info("Creando carpeta HIL...")
            create_data = {"displayName": "HIL"}

            result = self._make_graph_request(f'/users/{self.config.target_user_email}/mailFolders', 'POST', create_data)

            if result and 'id' in result:
                folder_id = result['id']
                logger.info(f'Carpeta HIL creada: {folder_id}')
                return folder_id
            else:
                logger.error("Error creando carpeta HIL")
                return None
        
        except Exception as e:
            logger.error(f"Error con carpeta HIL: {str(e)}")
            return None
    
    def create_hil_subscription(self) -> Optional[Dict[str, Any]]:
        """
        Crea una nueva suscripción para HIL.

        Returns:
            Dict con la información de la suscripción o None si falla.
        """
        logger.info("Creando suscripción HIL...")

        # Obtener / crear carpeta HIL
        hil_folder_id = self.get_or_create_hil_folder()
        if not hil_folder_id:
            logger.error("No se pudo obtener o crear la carpeta HIL")
            return None
        
        # Calcular expiración
        try:
            from datetime import timezone
            expiration = datetime.now(timezone.utc) + timedelta(days=2, hours=23)
        except ImportError:
            expiration = datetime.utcnow() + timedelta(days=2, hours=23)
        
        expiration_str = expiration.strftime('%Y-%m-%dT%H:%M:%S.0000000Z')
        
        webhook_data = {
            "changeType": "created",
            "notificationUrl": self.config.webhook_url,
            "resource": f"users/{self.config.target_user_email}/mailFolders/{hil_folder_id}/messages",
            "expirationDateTime": expiration_str,
            "clientState": "HILSecretState456"
        }

        logger.info(f"Configurando suscripción HIL que expira: {expiration_str}")

        result = self._make_graph_request('/subscriptions', 'POST', webhook_data)
        
        if result and 'id' in result:
            logger.info(f'Suscripción HIL creada: {result.get("id")}')
            return result
        else:
            logger.error('Error creando suscripción HIL')
            return None
    
    def process_subscriptions(self) -> Dict[str, Any]:
        """
        Procesa todas las suscripciones: lista, elimina expiradas y crea nuevas.

        Returns:
            Dict con el resultado del procesamiento.
        """
        results = {
            "success": True,
            "existing_subscriptions": 0,
            "deleted_subscriptions": 0,
            "created_subscriptions": 0,
            "errors": []
        }

        try:
            # 1. Listar suscripciones existentes
            existing_subs = self.list_existing_subscriptions()
            results["existing_subscriptions"] = len(existing_subs)

            # 2. Eliminar suscripciones existentes (para renovar)
            deleted_count = 0
            for sub in existing_subs:
                subscription_id = sub.get('id')  # Corregido: era Subscription_id

                if subscription_id:
                    if self.delete_subscription(subscription_id):
                        deleted_count += 1
                    else:
                        results["errors"].append(f"Error eliminando suscripción {subscription_id}")

            results["deleted_subscriptions"] = deleted_count

            # 3. Crear nueva suscripción INBOX
            inbox_result = self.create_inbox_subscription()
            if inbox_result:
                results['created_subscriptions'] += 1
            else:
                results['errors'].append('Error creando suscripción INBOX')
                results['success'] = False
            
            # 4. Crear nueva suscripción HIL
            hil_result = self.create_hil_subscription()
            if hil_result:
                results['created_subscriptions'] += 1
            else:
                results['errors'].append('Error creando suscripción HIL')
                results['success'] = False
            
            logger.info(f'Procesamiento completado:')
            logger.info(f'Existentes: {results["existing_subscriptions"]}')
            logger.info(f'Eliminadas: {results["deleted_subscriptions"]}')
            logger.info(f'Creadas: {results["created_subscriptions"]}')
            logger.info(f'Errores: {len(results["errors"])}')
            
            return results
            
        except Exception as e:
            logger.error(f'Error en procesamiento: {str(e)}')
            results['success'] = False
            results['errors'].append(f'Error crítico: {str(e)}')
            return results