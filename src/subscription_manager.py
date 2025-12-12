# src/subscription_manager.py -> 'Gestor de suscripciones multi-tenant'

import requests
from typing import Dict, Any
from .dynamodb_client import DynamoDBClient
from datetime import datetime, timezone, timedelta
from .utils import setup_logging, is_subscription_expired

logger = setup_logging()

class MultiTenantSubscriptionManager:
    """
    Gestor de suscripciones para MÚLTIPLES clientes.
    
    FLUJO (Reconciliation Loop):
    1. Leer TODOS los clientes activos de DynamoDB
    2. Para CADA cliente:
       a. Autenticarse con SUS credenciales Azure
       b. Verificar si tiene suscripción activa en Graph API
       c. Si NO tiene o está expirada → crear/renovar
       d. Actualizar DynamoDB con subscription_id real
    
    Este lambda es IDEMPOTENTE - ejecutarlo múltiples veces converge al mismo estado.
    """
    
    def __init__(self):
        """Inicializa el gestor multi-tenant"""
        self.db_client = DynamoDBClient()
        self.graph_api_base = "https://graph.microsoft.com/v1.0"
        logger.info("MultiTenantSubscriptionManager inicializado")
    
    def process_all_subscriptions(self) -> Dict[str, Any]:
        """
        Procesa suscripciones para TODOS los clientes activos.
        
        Este es el método principal que llama el lambda handler.
        
        Returns:
            Dict con resultados del procesamiento
        """
        logger.info("="*60)
        logger.info("INICIANDO PROCESAMIENTO MULTI-TENANT")
        logger.info("="*60)
        
        results = {
            'success': True,
            'total_clients': 0,
            'processed': [],
            'failed': [],
            'skipped': []
        }
        
        try:
            # 1. Obtener TODOS los clientes activos
            clients = self.db_client.get_all_active_clients()
            results['total_clients'] = len(clients)
            
            if not clients:
                logger.warning("No hay clientes activos en DynamoDB")
                results['success'] = False
                results['message'] = "No hay clientes activos"
                return results
            
            logger.info(f"\nProcesando {len(clients)} cliente(s)...\n")
            
            # 2. Procesar CADA cliente
            for idx, client_config in enumerate(clients, 1):
                client_id = client_config.get('client_id', 'unknown')
                
                logger.info(f"{'='*60}")
                logger.info(f"CLIENTE {idx}/{len(clients)}: {client_id}")
                logger.info(f"{'='*60}")
                
                try:
                    result = self._process_client_subscription(client_config)
                    
                    if result['action'] == 'created' or result['action'] == 'renewed':
                        results['processed'].append({
                            'client_id': client_id,
                            'action': result['action'],
                            'subscription_id': result.get('subscription_id', 'N/A')[:40]
                        })
                        logger.info(f"Cliente {client_id}: {result['action']}")
                        
                    elif result['action'] == 'skipped':
                        results['skipped'].append({
                            'client_id': client_id,
                            'reason': result.get('reason', 'N/A')
                        })
                        logger.info(f"⏭Cliente {client_id}: {result['reason']}")
                    
                except Exception as e:
                    logger.error(f"Error procesando cliente {client_id}: {e}")
                    results['failed'].append({
                        'client_id': client_id,
                        'error': str(e)
                    })
                    results['success'] = False
                
                logger.info("")  # Línea en blanco entre clientes
            
            # 3. Resumen final
            logger.info("="*60)
            logger.info("RESUMEN DE PROCESAMIENTO")
            logger.info("="*60)
            logger.info(f"Total clientes: {results['total_clients']}")
            logger.info(f"Procesados: {len(results['processed'])}")
            logger.info(f"Saltados: {len(results['skipped'])}")
            logger.info(f"Fallidos: {len(results['failed'])}")
            logger.info("="*60)
            
            return results
            
        except Exception as e:
            logger.error(f"Error crítico en procesamiento: {e}", exc_info=True)
            results['success'] = False
            results['error'] = str(e)
            return results
    
    def _process_client_subscription(self, client_config: Dict) -> Dict[str, Any]:
        """
        Procesa la suscripción de UN cliente específico.
        
        Lógica:
        1. Autenticarse con credenciales del cliente
        2. Verificar si tiene suscripción en Graph API
        3. Si NO tiene o está expirada → crear/renovar
        4. Actualizar DynamoDB con subscription_id real
        
        Args:
            client_config: Configuración del cliente desde DynamoDB
            
        Returns:
            Dict con resultado del procesamiento
        """
        client_id = client_config.get('client_id')
        client_email = client_config.get('client_email')
        current_sub_id = client_config.get('subscription_id')
        
        logger.info(f"Cliente: {client_id}")
        logger.info(f"Email: {client_email}")
        logger.info(f"Subscription ID actual: {current_sub_id[:40]}...")
        
        # 1. Obtener token de acceso con credenciales del cliente
        logger.info("Obteniendo token de acceso...")
        access_token = self._get_access_token_for_client(client_config)
        
        if not access_token:
            raise Exception("No se pudo obtener token de acceso")
        
        logger.info("Token obtenido")
        
        # 2. Verificar si necesita suscripción nueva
        needs_subscription = self._needs_subscription(
            current_sub_id,
            client_config.get('subscription_expiry')
        )
        
        if not needs_subscription:
            logger.info("Suscripción vigente, no requiere renovación")
            return {
                'action': 'skipped',
                'reason': 'Suscripción aún vigente'
            }
        
        # 3. Crear suscripción en Graph API
        logger.info("Creando suscripción en Graph API...")
        subscription_data = self._create_subscription_in_graph(
            access_token,
            client_email,
            client_config.get('webhook_url')
        )
        
        if not subscription_data:
            raise Exception("No se pudo crear suscripción en Graph API")
        
        new_sub_id = subscription_data['id']
        expiry_date = subscription_data['expirationDateTime']
        
        logger.info("Suscripción creada:")
        logger.info(f"   ID: {new_sub_id[:40]}...")
        logger.info(f"   Expira: {expiry_date}")
        
        # 4. Actualizar DynamoDB
        logger.info("Actualizando DynamoDB...")
        success = self.db_client.update_subscription_id(
            old_subscription_id = current_sub_id,
            new_subscription_id = new_sub_id,
            expiry_datetime = expiry_date
        )
        
        if not success:
            logger.warning("No se pudo actualizar DynamoDB (pero suscripción sí se creó)")
        else:
            logger.info("DynamoDB actualizado")
        
        action = 'created' if 'pending' in current_sub_id else 'renewed'
        
        return {
            'action': action,
            'subscription_id': new_sub_id,
            'expiry': expiry_date
        }
    
    def _get_access_token_for_client(self, client_config: Dict) -> str:
        """
        Obtiene token de acceso para un cliente específico.
        
        Usa las credenciales Azure del cliente (tenant_id, client_id, client_secret).
        
        Args:
            client_config: Configuración del cliente
            
        Returns:
            Access token o None si falla
        """
        tenant_id = client_config.get('azure_tenant_id')
        client_id = client_config.get('azure_client_id')
        client_secret = client_config.get('azure_client_secret')
        
        if not all([tenant_id, client_id, client_secret]):
            logger.error("Credenciales Azure incompletas")
            return None
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            response = requests.post(token_url, data = token_data, timeout = 10)
            response.raise_for_status()
            
            token_response = response.json()
            access_token = token_response.get('access_token')
            
            if not access_token:
                logger.error("No se recibió access_token en la respuesta")
                return None
            
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo token: {e}")
            return None
    
    def _needs_subscription(self, subscription_id: str, expiry_str: str) -> bool:
        """
        Determina si un cliente necesita nueva suscripción.
        
        Casos:
        - subscription_id es "pending-..." → SÍ necesita (cliente nuevo)
        - subscription_id expira en < 12 horas → SÍ necesita (renovar)
        - subscription_id vigente → NO necesita
        
        Args:
            subscription_id: ID de suscripción actual
            expiry_str: Fecha de expiración en formato ISO
            
        Returns:
            True si necesita nueva suscripción
        """
        # Caso 1: Cliente nuevo (pending)
        if 'pending' in subscription_id.lower():
            logger.info("Cliente nuevo detectado (subscription_id='pending')")
            return True
        
        # Caso 2: Verificar expiración
        if not expiry_str:
            logger.warning("Sin fecha de expiración, asumiendo que necesita renovación")
            return True
        
        try:
            # Verificar si expira pronto (buffer de 12 horas)
            if is_subscription_expired(expiry_str, buffer_hours=12):
                logger.info("Suscripción próxima a expirar, renovando...")
                return True
            else:
                logger.info(f"Suscripción vigente hasta: {expiry_str}")
                return False
                
        except Exception as e:
            logger.warning(f"Error verificando expiración: {e}, asumiendo renovación necesaria")
            return True
    
    def _create_subscription_in_graph(self, access_token: str, user_email: str, webhook_url: str) -> Dict:
        """
        Crea una suscripción en Microsoft Graph API.
        
        Args:
            access_token: Token de acceso del cliente
            user_email: Email del usuario a suscribir
            webhook_url: URL del webhook para notificaciones
            
        Returns:
            Datos de la suscripción creada o None si falla
        """
        url = f"{self.graph_api_base}/subscriptions"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Calcular fecha de expiración (3 días desde ahora)
        expiration_datetime = datetime.now(timezone.utc) + timedelta(days = 3)
        expiration_iso = expiration_datetime.isoformat().replace('+00:00', 'Z')
        
        payload = {
            "changeType": "created",
            "notificationUrl": webhook_url,
            "resource": f"users/{user_email}/messages",
            "expirationDateTime": expiration_iso,
            "clientState": f"mcp-{user_email.split('@')[0]}"  # Estado para validación
        }
        
        try:
            logger.debug(f"Payload: {payload}")
            
            response = requests.post(url, headers = headers, json = payload, timeout = 30)
            response.raise_for_status()
            
            subscription_data = response.json()
            
            logger.info(f"Suscripción creada exitosamente")
            
            return subscription_data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP creando suscripción: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'N/A'}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red creando suscripción: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return None