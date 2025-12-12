"""
Seed Script: Poblar DynamoDB con clientes de prueba

Uso:
    python seed_test_clients.py

Crea 2 clientes de prueba:
    - Cliente A: empresa_a
    - Cliente B: empresa_b
"""
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta

TABLE_NAME = "MCP_ClientConfigurations"
REGION = "us-east-2"

def create_test_clients():
    """Crea 2 clientes de prueba en DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    # Fecha de expiración (3 días desde ahora)
    expiry_date = datetime.now(timezone.utc) + timedelta(days=3)
    
    # CLIENTE A
    client_a = {
        "subscription_id": f"sub-empresa-a-inbox-{datetime.now().strftime('%Y%m%d%H%M')}",
        "client_id": "empresa_a",
        "client_name": "Empresa A S.A.",
        "client_email": "soporte@empresaa.com",
        
        # Credenciales Azure (REEMPLAZAR CON REALES)
        "azure_tenant_id": "aaaaaaaa-bbbb-cccc-dddd-111111111111",
        "azure_client_id": "11111111-2222-3333-4444-555555555555",
        "azure_client_secret": "SECRET_CLIENTE_A_AQUI",  # ⚠️  CAMBIAR
        
        # Configuración BD
        "db_config": {
            "host": "postgres-dev.abc123.us-east-2.rds.amazonaws.com",  # ⚠️  CAMBIAR
            "port": 5432,
            "database": "knowledge_base",
            "schema": "empresa_a"
        },
        
        # Subscription metadata
        "subscription_resource": "users/soporte@empresaa.com/messages",
        "subscription_expiry": expiry_date.isoformat(),
        "webhook_url": "https://api.tudominio.com/webhook",  # ⚠️  CAMBIAR
        
        # Estado
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        
        # Quotas
        "quotas": {
            "max_emails_per_day": 1000,
            "max_file_size_mb": 50
        }
    }
    
    # CLIENTE B
    client_b = {
        "subscription_id": f"sub-empresa-b-inbox-{datetime.now().strftime('%Y%m%d%H%M')}",
        "client_id": "empresa_b",
        "client_name": "Empresa B Ltd.",
        "client_email": "ayuda@empresab.com",
        
        # Credenciales Azure (REEMPLAZAR CON REALES)
        "azure_tenant_id": "bbbbbbbb-cccc-dddd-eeee-222222222222",
        "azure_client_id": "22222222-3333-4444-5555-666666666666",
        "azure_client_secret": "SECRET_CLIENTE_B_AQUI",  # ⚠️  CAMBIAR
        
        # Configuración BD
        "db_config": {
            "host": "postgres-dev.abc123.us-east-2.rds.amazonaws.com",  # ⚠️  CAMBIAR
            "port": 5432,
            "database": "knowledge_base",
            "schema": "empresa_b"
        },
        
        # Subscription metadata
        "subscription_resource": "users/ayuda@empresab.com/messages",
        "subscription_expiry": expiry_date.isoformat(),
        "webhook_url": "https://api.tudominio.com/webhook",  # ⚠️  CAMBIAR
        
        # Estado
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        
        # Quotas
        "quotas": {
            "max_emails_per_day": 500,
            "max_file_size_mb": 50
        }
    }
    
    print("=" * 60)
    print("  POBLAR CLIENTES DE PRUEBA")
    print("=" * 60)
    print()
    
    # Guardar Cliente A
    try:
        print(f"Guardando Cliente A: {client_a['client_id']}")
        table.put_item(Item=client_a)
        print(f"Email: {client_a['client_email']}")
        print(f"Schema DB: {client_a['db_config']['schema']}")
        
    except ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")
    
    print()
    
    # Guardar Cliente B
    try:
        print(f"Guardando Cliente B: {client_b['client_id']}")
        table.put_item(Item=client_b)
        print(f"Email: {client_b['client_email']}")
        print(f"Schema DB: {client_b['db_config']['schema']}")
        
    except ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")
    
    print()
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print()
    print("Clientes de prueba creados")
    print()
    print("IMPORTANTE: Actualizar las siguientes variables:")
    print()
    print("   1. azure_client_secret (para ambos clientes)")
    print("   2. db_config.host (servidor PostgreSQL)")
    print("   3. webhook_url (URL del orquestador)")
    print()
    print("Actualizar con:")
    print("   python admin_clients.py update --client-id empresa_a")
    print("   python admin_clients.py update --client-id empresa_b")
    print()
    print("Verificar con:")
    print("   python admin_clients.py list")
    print()


if __name__ == "__main__":
    create_test_clients()