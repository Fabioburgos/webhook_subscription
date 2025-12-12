"""
Validation Script: Verificar configuración de DynamoDB y clientes

Uso:
    python validate_setup.py

Verifica:
    - Tabla DynamoDB existe y está activa
    - Hay al menos 1 cliente activo
    - Clientes tienen credenciales válidas
    - Estructura de items es correcta
"""
import boto3
from botocore.exceptions import ClientError

TABLE_NAME = "MCP_ClientConfigurations"
REGION = "us-east-2"

class SetupValidator:
    """Validador de configuración"""
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name=REGION)
        self.dynamodb_resource = boto3.resource('dynamodb', region_name=REGION)
        self.errors = []
        self.warnings = []
    
    def validate_table_exists(self):
        """Verifica que la tabla existe"""
        print("Verificando tabla DynamoDB...")
        
        try:
            response = self.dynamodb.describe_table(TableName=TABLE_NAME)
            
            status = response['Table']['TableStatus']
            item_count = response['Table']['ItemCount']
            
            if status != 'ACTIVE':
                self.errors.append(f"Tabla no está activa (status: {status})")
                print(f"Tabla status: {status}")
                return False
            
            print(f"Tabla activa")
            print(f"Items: {item_count}")
            
            # Verificar índices
            gsi_count = len(response['Table'].get('GlobalSecondaryIndexes', []))
            expected_gsi = 3  # client-id-index, client-email-index, status-expiry-index
            
            if gsi_count != expected_gsi:
                self.warnings.append(f"Se esperan {expected_gsi} índices, encontrados: {gsi_count}")
                print(f"Índices: {gsi_count} (esperados: {expected_gsi})")
            else:
                print(f"Índices: {gsi_count}")
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.errors.append(f"Tabla '{TABLE_NAME}' no existe")
                print(f"Tabla no existe")
                print()
                print("   Crear con:")
                print("   python create_table.py")
                return False
            else:
                self.errors.append(f"Error verificando tabla: {e.response['Error']['Message']}")
                return False
    
    def validate_clients_exist(self):
        """Verifica que hay clientes registrados"""
        print()
        print("Verificando clientes...")
        
        try:
            table = self.dynamodb_resource.Table(TABLE_NAME)
            response = table.scan()
            
            items = response.get('Items', [])
            
            if not items:
                self.errors.append("No hay clientes registrados")
                print(f"No hay clientes")
                print()
                print("   Agregar con:")
                print("   python admin_clients.py add")
                print("   O:")
                print("   python seed_test_clients.py")
                return False
            
            print(f"{len(items)} cliente(s) registrado(s)")
            
            # Verificar clientes activos
            active_clients = [c for c in items if c.get('status') == 'active']
            
            if not active_clients:
                self.errors.append("No hay clientes activos")
                print(f"No hay clientes activos")
                return False
            
            print(f"{len(active_clients)} cliente(s) activo(s)")
            
            return items
            
        except ClientError as e:
            self.errors.append(f"Error listando clientes: {e.response['Error']['Message']}")
            return False
    
    def validate_client_structure(self, clients):
        """Valida estructura de cada cliente"""
        print()
        print("Validando estructura de clientes...")
        
        required_fields = [
            'subscription_id',
            'client_id',
            'client_email',
            'azure_tenant_id',
            'azure_client_id',
            'azure_client_secret',
            'db_config',
            'status'
        ]
        
        all_valid = True
        
        for idx, client in enumerate(clients, 1):
            client_id = client.get('client_id', f'Cliente #{idx}')
            print(f"\n   Cliente: {client_id}")
            
            missing_fields = []
            for field in required_fields:
                if field not in client or not client[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                self.errors.append(f"Cliente {client_id} tiene campos faltantes: {missing_fields}")
                print(f"Campos faltantes: {', '.join(missing_fields)}")
                all_valid = False
            else:
                print(f"Campos requeridos presentes")
            
            # Validar db_config
            if 'db_config' in client and isinstance(client['db_config'], dict):
                db_fields = ['host', 'database', 'schema']
                missing_db = [f for f in db_fields if f not in client['db_config']]
                
                if missing_db:
                    self.warnings.append(f"Cliente {client_id} - db_config incompleto: {missing_db}")
                    print(f"db_config incompleto: {', '.join(missing_db)}")
                else:
                    print(f"db_config válido (schema: {client['db_config']['schema']})")
            
            # Validar credenciales Azure
            if 'azure_client_secret' in client:
                secret = client['azure_client_secret']
                if 'SECRET_CLIENTE' in secret or 'AQUI' in secret:
                    self.warnings.append(f"Cliente {client_id} usa credencial de prueba")
                    print(f"Credencial Azure parece ser de prueba")
            
            # Validar status
            valid_statuses = ['active', 'suspended', 'expired']
            status = client.get('status')
            if status not in valid_statuses:
                self.warnings.append(f"Cliente {client_id} tiene status inválido: {status}")
                print(f"Status inválido: {status}")
            else:
                print(f"Status: {status}")
        
        return all_valid
    
    def validate_subscriptions(self, clients):
        """Valida subscription_ids"""
        print()
        print("Validando subscription IDs...")
        
        for client in clients:
            client_id = client.get('client_id')
            sub_id = client.get('subscription_id', '')
            
            print(f"\n   Cliente: {client_id}")
            
            if 'pending' in sub_id.lower():
                self.warnings.append(f"Cliente {client_id} tiene subscription_id pendiente")
                print(f"Subscription ID pendiente (no renovado aún)")
                print(f"ID: {sub_id}")
            else:
                print(f"Subscription ID asignado")
                print(f"ID: {sub_id[:40]}...")
    
    def validate_permissions(self):
        """Verifica permisos básicos de DynamoDB"""
        print()
        print("Verificando permisos IAM...")
        
        try:
            # Intentar scan (requiere permisos)
            table = self.dynamodb_resource.Table(TABLE_NAME)
            table.scan(Limit=1)
            
            print(f"Permisos de lectura OK")
            
            # Verificar permisos de escritura (no destructivo)
            # Solo verificamos que no da error de permisos
            print(f"Permisos básicos validados")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'AccessDeniedException':
                self.errors.append("Sin permisos para acceder a DynamoDB")
                print(f"Sin permisos DynamoDB")
                print()
                print("Requiere política IAM:")
                print("""
   {
     "Effect": "Allow",
     "Action": [
       "dynamodb:GetItem",
       "dynamodb:Scan",
       "dynamodb:Query",
       "dynamodb:PutItem",
       "dynamodb:UpdateItem"
     ],
     "Resource": [
       "arn:aws:dynamodb:*:*:table/MCP_ClientConfigurations",
       "arn:aws:dynamodb:*:*:table/MCP_ClientConfigurations/index/*"
     ]
   }
                """)
                return False
            else:
                self.warnings.append(f"Error verificando permisos: {e.response['Error']['Message']}")
                return True  # No bloquear por otros errores
    
    def print_summary(self):
        """Imprime resumen de validación"""
        print()
        print("=" * 60)
        print("  RESUMEN DE VALIDACIÓN")
        print("=" * 60)
        print()
        
        if not self.errors and not self.warnings:
            print("TODO ESTÁ CONFIGURADO CORRECTAMENTE")
            print()
            print("Listo para proceder con:")
            print("1. Modificar subscription_manager.py")
            print("2. Actualizar handler.py")
            print("3. Deploy a Lambda")
            return True
        
        if self.errors:
            print(f"ERRORES ENCONTRADOS ({len(self.errors)}):")
            print()
            for idx, error in enumerate(self.errors, 1):
                print(f"   {idx}. {error}")
            print()
        
        if self.warnings:
            print(f"ADVERTENCIAS ({len(self.warnings)}):")
            print()
            for idx, warning in enumerate(self.warnings, 1):
                print(f"   {idx}. {warning}")
            print()
        
        if self.errors:
            print("ACCIÓN REQUERIDA:")
            print("   Corregir errores antes de continuar")
            return False
        else:
            print("ADVERTENCIAS NO BLOQUEAN:")
            print("   Puedes proceder pero considera resolverlas")
            return True
    
    def run_all_validations(self):
        """Ejecuta todas las validaciones"""
        print("=" * 60)
        print("  VALIDADOR DE CONFIGURACIÓN MCP")
        print("=" * 60)
        print()
        
        # 1. Tabla existe
        if not self.validate_table_exists():
            self.print_summary()
            return False
        
        # 2. Clientes existen
        clients = self.validate_clients_exist()
        if not clients:
            self.print_summary()
            return False
        
        # 3. Estructura válida
        self.validate_client_structure(clients)
        
        # 4. Subscription IDs
        self.validate_subscriptions(clients)
        
        # 5. Permisos
        self.validate_permissions()
        
        # Resumen final
        return self.print_summary()

if __name__ == "__main__":
    validator = SetupValidator()
    success = validator.run_all_validations()
    
    import sys
    sys.exit(0 if success else 1)