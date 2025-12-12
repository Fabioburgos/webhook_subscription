"""
Admin Script: Gestión de Clientes en DynamoDB

Uso:
    python admin_clients.py add                    # Agregar cliente interactivamente
    python admin_clients.py list                   # Listar todos los clientes
    python admin_clients.py get --client-id ID     # Ver detalle de un cliente
    python admin_clients.py update --client-id ID  # Actualizar cliente
    python admin_clients.py delete --client-id ID  # Eliminar cliente

Requiere:
    - boto3
    - AWS credentials configuradas
"""
import sys
import json
import boto3
import argparse
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta

TABLE_NAME = "MCP_ClientConfigurations"
REGION = "us-east-2"

class ClientAdmin:
    """Administrador de clientes en DynamoDB"""
    
    def __init__(self):
        # Usar sesión con perfil 'dev'
        session = boto3.Session(profile_name='dev')
        self.dynamodb = session.resource('dynamodb', region_name=REGION)
        self.table = self.dynamodb.Table(TABLE_NAME)
    
    def add_client(self, interactive=True):
        """Agrega un nuevo cliente"""
        
        print("=" * 60)
        print("  AGREGAR NUEVO CLIENTE")
        print("=" * 60)
        print()
        
        if interactive:
            # Modo interactivo
            print("Ingresa los datos del cliente:")
            print()
            
            client_id = input("Client ID (ej: cliente_a): ").strip()
            client_name = input("Nombre del Cliente (ej: Empresa A S.A.): ").strip()
            client_email = input("Email del Cliente (ej: soporte@empresaa.com): ").strip()
            
            print()
            print("Credenciales Azure (Graph API):")
            azure_tenant_id = input("Azure Tenant ID: ").strip()
            azure_client_id = input("Azure Client ID: ").strip()
            azure_client_secret = input("Azure Client Secret: ").strip()
            
            print()
            print("Configuración Base de Datos:")
            db_schema = input(f"Schema PostgreSQL (default: {client_id}): ").strip() or client_id
            
            print()
            webhook_url = input("Webhook URL (default: auto): ").strip() or "https://ro7ft46i7d.execute-api.us-east-2.amazonaws.com/dev/dev-orchestrator-agent"
            
        else:
            # Modo programático (para scripts)
            raise NotImplementedError("Modo no interactivo aún no implementado")
        
        # Generar subscription_id temporal (se actualizará después)
        subscription_id = f"sub-{client_id}-pending-{datetime.now().strftime('%Y%m%d')}"
        
        # Calcular fecha de expiración (3 días desde ahora)
        expiry_date = datetime.now(timezone.utc) + timedelta(days=3)
        
        # Construir item
        item = {
            "subscription_id": subscription_id,
            "client_id": client_id,
            "client_name": client_name,
            "client_email": client_email,
            
            # Credenciales Azure
            "azure_tenant_id": azure_tenant_id,
            "azure_client_id": azure_client_id,
            "azure_client_secret": azure_client_secret,  # TODO: Mover a Secrets Manager
            
            # Configuración BD (Aurora DSQL)
            "db_config": {
                "host": "2ntlcxcmjgkalxoysmnqswrgsi.dsql.us-east-2.on.aws",
                "port": 5432,
                "database": "postgres",  # Aurora DSQL usa 'postgres' como DB por defecto
                "schema": db_schema
            },
            
            # Subscription metadata
            "subscription_resource": f"users/{client_email}/messages",
            "subscription_expiry": expiry_date.isoformat(),
            "webhook_url": webhook_url,
            
            # Estado
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            
            # Quotas (opcional)
            "quotas": {
                "max_emails_per_day": 1000,
                "max_file_size_mb": 50
            }
        }
        
        # Mostrar resumen
        print()
        print("=" * 60)
        print("  RESUMEN DEL CLIENTE")
        print("=" * 60)
        print(json.dumps(item, indent=2, default=str))
        print()
        
        confirm = input("¿Guardar este cliente? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Cancelado")
            return False
        
        # Guardar en DynamoDB
        try:
            self.table.put_item(Item=item)
            print()
            print("Cliente agregado exitosamente!")
            print(f"   Client ID: {client_id}")
            print(f"   Subscription ID (temporal): {subscription_id}")
            print()
            print("Nota: El subscription_id se actualizará automáticamente")
            print("   cuando el lambda de renovación ejecute.")
            return True
            
        except ClientError as e:
            print(f"Error guardando cliente: {e.response['Error']['Message']}")
            return False
    
    def list_clients(self):
        """Lista todos los clientes"""
        
        try:
            response = self.table.scan()
            items = response.get('Items', [])
            
            if not items:
                print("No hay clientes registrados")
                print()
                print("Agregar cliente:")
                print("python admin_clients.py add")
                return
            
            print()
            print("=" * 100)
            print(f"CLIENTES REGISTRADOS ({len(items)})")
            print("=" * 100)
            print()
            
            # Tabla de clientes
            print(f"{'CLIENT_ID':<20} {'EMAIL':<30} {'STATUS':<10} {'SUBSCRIPTION':<30}")
            print("-" * 100)
            
            for item in items:
                client_id = item.get('client_id', 'N/A')
                email = item.get('client_email', 'N/A')
                status = item.get('status', 'N/A')
                sub_id = item.get('subscription_id', 'N/A')
                
                # Truncar subscription_id para mostrar
                sub_display = sub_id[:27] + "..." if len(sub_id) > 30 else sub_id
                
                print(f"{client_id:<20} {email:<30} {status:<10} {sub_display:<30}")
            
            print()
            print(f"Total: {len(items)} cliente(s)")
            print()
            
        except ClientError as e:
            print(f"Error listando clientes: {e.response['Error']['Message']}")
    
    def get_client(self, client_id):
        """Obtiene detalle de un cliente"""
        
        try:
            # Buscar por client_id usando GSI
            response = self.table.query(
                IndexName='client-id-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('client_id').eq(client_id)
            )
            
            items = response.get('Items', [])
            
            if not items:
                print(f"Cliente no encontrado: {client_id}")
                return None
            
            item = items[0]
            
            print()
            print("=" * 60)
            print(f"  DETALLE DEL CLIENTE: {client_id}")
            print("=" * 60)
            print()
            print(json.dumps(item, indent=2, default=str))
            print()
            
            return item
            
        except ClientError as e:
            print(f"Error obteniendo cliente: {e.response['Error']['Message']}")
            return None
    
    def update_client(self, client_id):
        """Actualiza un cliente existente"""
        
        # Primero obtener el cliente actual
        current = self.get_client(client_id)
        if not current:
            return False
        
        print()
        print("Actualizar campos (dejar vacío para mantener valor actual):")
        print()
        
        # Campos actualizables
        client_name = input(f"Nombre [{current.get('client_name')}]: ").strip()
        client_email = input(f"Email [{current.get('client_email')}]: ").strip()
        
        # Status
        print()
        print("Status:")
        print("  1. active")
        print("  2. suspended")
        print("  3. expired")
        status_choice = input(f"Seleccionar [actual: {current.get('status')}]: ").strip()
        
        status_map = {"1": "active", "2": "suspended", "3": "expired"}
        new_status = status_map.get(status_choice, current.get('status'))
        
        # Construir update expression
        update_expr_parts = []
        expr_attr_values = {}
        expr_attr_names = {}
        
        if client_name:
            update_expr_parts.append("#cn = :cn")
            expr_attr_values[":cn"] = client_name
            expr_attr_names["#cn"] = "client_name"
        
        if client_email:
            update_expr_parts.append("client_email = :ce")
            expr_attr_values[":ce"] = client_email
        
        if new_status != current.get('status'):
            update_expr_parts.append("#st = :st")
            expr_attr_values[":st"] = new_status
            expr_attr_names["#st"] = "status"
        
        # Siempre actualizar updated_at
        update_expr_parts.append("updated_at = :ua")
        expr_attr_values[":ua"] = datetime.now(timezone.utc).isoformat()
        
        if not update_expr_parts:
            print("No hay cambios para guardar")
            return False
        
        update_expression = "SET " + ", ".join(update_expr_parts)
        
        print()
        print("Actualizando...")
        
        try:
            update_args = {
                'Key': {'subscription_id': current['subscription_id']},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expr_attr_values
            }
            
            if expr_attr_names:
                update_args['ExpressionAttributeNames'] = expr_attr_names
            
            self.table.update_item(**update_args)
            
            print("Cliente actualizado exitosamente!")
            print()
            
            # Mostrar cliente actualizado
            self.get_client(client_id)
            return True
            
        except ClientError as e:
            print(f"Error actualizando cliente: {e.response['Error']['Message']}")
            return False
    
    def delete_client(self, client_id):
        """Elimina un cliente"""
        
        # Obtener cliente
        client = self.get_client(client_id)
        if not client:
            return False
        
        print()
        print("¿ELIMINAR ESTE CLIENTE?")
        print()
        confirm = input("Confirmar eliminación (escribir 'DELETE' en mayúsculas): ").strip()
        
        if confirm != "DELETE":
            print("Cancelado")
            return False
        
        try:
            self.table.delete_item(
                Key={'subscription_id': client['subscription_id']}
            )
            
            print()
            print("Cliente eliminado exitosamente")
            return True
            
        except ClientError as e:
            print(f"Error eliminando cliente: {e.response['Error']['Message']}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description = "Administrador de Clientes MCP",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
        Ejemplos:
        python admin_clients.py add                    # Agregar cliente
        python admin_clients.py list                   # Listar clientes
        python admin_clients.py get --client-id xyz    # Ver detalle
        python admin_clients.py update --client-id xyz # Actualizar
        python admin_clients.py delete --client-id xyz # Eliminar
        """
    )
    
    parser.add_argument(
        'command',
        choices = ['add', 'list', 'get', 'update', 'delete'],
        help = 'Comando a ejecutar'
    )
    
    parser.add_argument(
        '--client-id',
        help = 'ID del cliente (requerido para get, update, delete)'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.command in ['get', 'update', 'delete'] and not args.client_id:
        print(f"Error: --client-id es requerido para comando '{args.command}'")
        sys.exit(1)
    
    # Crear admin
    admin = ClientAdmin()
    
    # Ejecutar comando
    try:
        if args.command == 'add':
            success = admin.add_client()
            sys.exit(0 if success else 1)
        
        elif args.command == 'list':
            admin.list_clients()
            sys.exit(0)
        
        elif args.command == 'get':
            client = admin.get_client(args.client_id)
            sys.exit(0 if client else 1)
        
        elif args.command == 'update':
            success = admin.update_client(args.client_id)
            sys.exit(0 if success else 1)
        
        elif args.command == 'delete':
            success = admin.delete_client(args.client_id)
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print()
        print("Cancelado por usuario")
        sys.exit(1)


if __name__ == "__main__":
    main()