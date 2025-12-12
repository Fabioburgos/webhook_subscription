# src/dynamodb_client.py -> 'Cliente para acceder a configuraciones de clientes'

import boto3
from .utils import setup_logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from botocore.exceptions import ClientError

logger = setup_logging()

class DynamoDBClient:
    """
    Cliente para acceder a configuraciones de clientes en DynamoDB.
    
    Tabla: MCP_ClientConfigurations
    Primary Key: subscription_id
    GSI: client-id-index (para buscar por client_id)
    """
    
    def __init__(self, table_name: str = "MCP_ClientConfigurations", region: str = "us-east-2", profile_name: str = None):
        """
        Inicializa el cliente DynamoDB.

        Args:
            table_name: Nombre de la tabla DynamoDB
            region: Región AWS
            profile_name: Perfil AWS a usar (opcional, usa 'default' si no se especifica)
        """
        self.table_name = table_name
        self.region = region

        try:
            # Usar sesión con perfil específico si se proporciona
            if profile_name:
                session = boto3.Session(profile_name=profile_name)
                self.dynamodb = session.resource('dynamodb', region_name=region)
            else:
                self.dynamodb = boto3.resource('dynamodb', region_name=region)

            self.table = self.dynamodb.Table(table_name)
            logger.info(f"DynamoDB client inicializado: {table_name} ({region})")
        except Exception as e:
            logger.error(f"Error inicializando DynamoDB client: {e}")
            raise
    
    def get_all_active_clients(self) -> List[Dict]:
        """
        Obtiene TODOS los clientes activos desde DynamoDB.
        
        Esto es lo que el lambda usa para saber qué clientes procesar.
        
        Returns:
            Lista de configuraciones de clientes activos
        """
        try:
            logger.info("Obteniendo clientes activos desde DynamoDB...")
            
            # Scan con filtro de status = active
            response = self.table.scan(
                FilterExpression = "attribute_exists(#status) AND #status = :status",
                ExpressionAttributeNames = {
                    '#status': 'status'
                },
                ExpressionAttributeValues = {
                    ':status': 'active'
                }
            )
            
            clients = response.get('Items', [])
            
            # Manejar paginación si hay muchos clientes
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression = "attribute_exists(#status) AND #status = :status",
                    ExpressionAttributeNames = {'#status': 'status'},
                    ExpressionAttributeValues = {':status': 'active'},
                    ExclusiveStartKey = response['LastEvaluatedKey']
                )
                clients.extend(response.get('Items', []))
            
            logger.info(f"Encontrados {len(clients)} cliente(s) activo(s)")
            
            # Log de clientes encontrados (sin exponer secrets)
            for client in clients:
                logger.info(f"  - {client.get('client_id')}: {client.get('client_email')}")
            
            return clients
            
        except ClientError as e:
            logger.error(f"Error obteniendo clientes: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado obteniendo clientes: {e}")
            raise
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict]:
        """
        Obtiene un cliente específico por su client_id.
        
        Args:
            client_id: ID del cliente
            
        Returns:
            Configuración del cliente o None si no existe
        """
        try:
            logger.debug(f"Buscando cliente: {client_id}")
            
            # Buscar usando GSI client-id-index
            response = self.table.query(
                IndexName = 'client-id-index',
                KeyConditionExpression = boto3.dynamodb.conditions.Key('client_id').eq(client_id)
            )
            
            items = response.get('Items', [])
            
            if not items:
                logger.warning(f"Cliente no encontrado: {client_id}")
                return None
            
            if len(items) > 1:
                logger.warning(f"Múltiples registros para client_id: {client_id} (usando el primero)")
            
            return items[0]
            
        except ClientError as e:
            logger.error(f"Error buscando cliente {client_id}: {e.response['Error']['Message']}")
            return None
    
    def update_subscription_id(self, old_subscription_id: str, new_subscription_id: str, expiry_datetime: str) -> bool:
        """
        Actualiza el subscription_id de un cliente después de crear/renovar suscripción.
        
        IMPORTANTE: Como subscription_id es la PRIMARY KEY, necesitamos:
        1. Eliminar el item viejo
        2. Crear el item nuevo con el nuevo subscription_id
        
        Args:
            old_subscription_id: Subscription ID actual (puede ser "pending-...")
            new_subscription_id: Nuevo subscription ID de Graph API
            expiry_datetime: Fecha de expiración en formato ISO
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            logger.info(f"Actualizando subscription_id...")
            logger.info(f"  Anterior: {old_subscription_id[:40]}...")
            logger.info(f"  Nuevo: {new_subscription_id[:40]}...")
            
            # 1. Obtener el item completo
            response = self.table.get_item(Key={'subscription_id': old_subscription_id})
            
            if 'Item' not in response:
                logger.error(f"Item no encontrado con subscription_id: {old_subscription_id}")
                return False
            
            item = response['Item']
            
            # 2. Actualizar campos del item
            item['subscription_id'] = new_subscription_id
            item['subscription_expiry'] = expiry_datetime
            item['updated_at'] = self._get_current_timestamp()
            
            # 3. Eliminar item viejo
            self.table.delete_item(Key={'subscription_id': old_subscription_id})
            logger.debug("Item viejo eliminado")
            
            # 4. Crear item nuevo con nuevo subscription_id
            self.table.put_item(Item = item)
            logger.info("Subscription ID actualizado exitosamente")
            
            return True
            
        except ClientError as e:
            logger.error(f"Error actualizando subscription_id: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return False
    
    def update_client_status(self, subscription_id: str, new_status: str) -> bool:
        """
        Actualiza el status de un cliente.
        
        Args:
            subscription_id: ID de la suscripción
            new_status: Nuevo status (active, suspended, expired)
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            logger.info(f"Actualizando status del cliente: {new_status}")
            
            self.table.update_item(
                Key={'subscription_id': subscription_id},
                UpdateExpression = "SET #status = :status, updated_at = :updated",
                ExpressionAttributeNames = {'#status': 'status'},
                ExpressionAttributeValues = {
                    ':status': new_status,
                    ':updated': self._get_current_timestamp()
                }
            )
            
            logger.info(f"Status actualizado a: {new_status}")
            return True
            
        except ClientError as e:
            logger.error(f"Error actualizando status: {e.response['Error']['Message']}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """Obtiene timestamp actual en formato ISO"""
        return datetime.now(timezone.utc).isoformat()