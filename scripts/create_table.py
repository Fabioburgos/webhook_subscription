"""
Script para crear tabla DynamoDB: MCP_ClientConfigurations

Uso:
    python create_table.py

Requiere:
    - AWS credentials configuradas
    - Permisos: dynamodb:CreateTable
"""
import sys
import boto3
from botocore.exceptions import ClientError

# Nombre de la tabla
TABLE_NAME = "MCP_ClientConfigurations"
REGION = "us-east-2"  # Cambiar si usas otra región

def create_table():
    """Crea la tabla DynamoDB con índices"""

    # Usar sesión con perfil 'dev'
    session = boto3.Session(profile_name='dev')
    dynamodb = session.client('dynamodb', region_name=REGION)
    
    try:
        print(f"Creando tabla: {TABLE_NAME} en {REGION}")
        print("-" * 60)
        
        response = dynamodb.create_table(
            TableName=TABLE_NAME,
            
            # KEY SCHEMA
            KeySchema=[
                {
                    'AttributeName': 'subscription_id',  # PK
                    'KeyType': 'HASH'
                }
            ],
            
            # ATTRIBUTE DEFINITIONS
            AttributeDefinitions=[
                {'AttributeName': 'subscription_id', 'AttributeType': 'S'},
                {'AttributeName': 'client_id', 'AttributeType': 'S'},
                {'AttributeName': 'client_email', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'subscription_expiry', 'AttributeType': 'S'}
            ],
            
            # GLOBAL SECONDARY INDEXES
            GlobalSecondaryIndexes=[
                {
                    # GSI-1: Buscar por client_id
                    'IndexName': 'client-id-index',
                    'KeySchema': [
                        {'AttributeName': 'client_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    # GSI-2: Buscar por email
                    'IndexName': 'client-email-index',
                    'KeySchema': [
                        {'AttributeName': 'client_email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    # GSI-3: Buscar por status y expiry (para renovaciones)
                    'IndexName': 'status-expiry-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'subscription_expiry', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            
            # BILLING MODE
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            
            # TAGS
            Tags=[
                {'Key': 'Project', 'Value': 'MCP-Orchestrator'},
                {'Key': 'Environment', 'Value': 'Development'},
                {'Key': 'ManagedBy', 'Value': 'Script'}
            ]
        )
        
        print("Tabla creada exitosamente!")
        print(f"   ARN: {response['TableDescription']['TableArn']}")
        print(f"   Status: {response['TableDescription']['TableStatus']}")
        print()
        print("Esperando a que la tabla esté activa...")
        
        # Esperar a que la tabla esté activa
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(
            TableName=TABLE_NAME,
            WaiterConfig={'Delay': 5, 'MaxAttempts': 10}
        )
        
        print("Tabla activa y lista para usar!")
        print()
        print("Índices creados:")
        print("   1. client-id-index (buscar por client_id)")
        print("   2. client-email-index (buscar por email)")
        print("   3. status-expiry-index (renovaciones automáticas)")
        print()
        print("Próximo paso:")
        print("   python admin_clients.py add")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'ResourceInUseException':
            print(f"La tabla '{TABLE_NAME}' ya existe")
            print()
            print("Opciones:")
            print("  1. Usar la tabla existente (recomendado)")
            print("  2. Eliminar y recrear: aws dynamodb delete-table --table-name {TABLE_NAME}")
            return False
            
        elif error_code == 'LimitExceededException':
            print(f"Error: Límite de tablas alcanzado en la región {REGION}")
            print("   Solución: Eliminar tablas no usadas o usar otra región")
            return False
            
        elif error_code == 'AccessDeniedException':
            print("Error: Sin permisos para crear tabla DynamoDB")
            print("   Requieres permisos: dynamodb:CreateTable")
            print()
            print("   Agrega esta política IAM:")
            print("""
   {
     "Effect": "Allow",
     "Action": [
       "dynamodb:CreateTable",
       "dynamodb:DescribeTable"
     ],
     "Resource": "arn:aws:dynamodb:*:*:table/MCP_ClientConfigurations"
   }
            """)
            return False
        
        else:
            print(f"Error creando tabla: {e.response['Error']['Message']}")
            return False
    
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return False


def verify_table():
    """Verifica que la tabla existe y está activa"""

    # Usar sesión con perfil 'dev'
    session = boto3.Session(profile_name='dev')
    dynamodb = session.client('dynamodb', region_name=REGION)
    
    try:
        response = dynamodb.describe_table(TableName=TABLE_NAME)
        
        status = response['Table']['TableStatus']
        item_count = response['Table']['ItemCount']
        
        print()
        print("Información de la tabla:")
        print(f"   Nombre: {TABLE_NAME}")
        print(f"   Status: {status}")
        print(f"   Items: {item_count}")
        print(f"   Región: {REGION}")
        
        if status == 'ACTIVE':
            print()
            print("Tabla operativa!")
            return True
        else:
            print()
            print(f"Tabla no está activa (status: {status})")
            return False
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Tabla '{TABLE_NAME}' no existe")
            return False
        else:
            print(f"Error verificando tabla: {e.response['Error']['Message']}")
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("  CREAR TABLA DYNAMODB - MCP CLIENT CONFIGURATIONS")
    print("=" * 60)
    print()
    
    # Verificar si ya existe
    print("Verificando si la tabla ya existe...")
    if verify_table():
        print()
        print("La tabla ya está operativa, no es necesario crearla")
        sys.exit(0)
    
    # Crear tabla
    print()
    success = create_table()
    
    if success:
        # Verificar creación
        verify_table()
        sys.exit(0)
    else:
        sys.exit(1)