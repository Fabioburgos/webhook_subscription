# Scripts de Gestión de Clientes Multi-Tenant

Scripts para administrar clientes en DynamoDB para el sistema MCP.

## 📁 Archivos

```
scripts/
├── create_table.py          # Crear tabla DynamoDB (1 sola vez)
├── admin_clients.py         # CRUD de clientes (usar frecuentemente)
├── seed_test_clients.py     # Poblar datos de prueba
└── README.md                # Este archivo
```

---

## 🚀 QUICK START (Primeros Pasos)

### 1️⃣ Crear Tabla DynamoDB (1 sola vez)

```bash
cd scripts
python create_table.py
```

**Salida esperada:**
```
✅ Tabla creada exitosamente!
✅ Tabla activa y lista para usar!
```

**Si ya existe:**
```
⚠️  La tabla 'MCP_ClientConfigurations' ya existe
```

---

### 2️⃣ Agregar Tu Primer Cliente

**Opción A: Datos de Prueba (recomendado para testing)**

```bash
python seed_test_clients.py
```

Esto crea 2 clientes de ejemplo:
- `empresa_a` (soporte@empresaa.com)
- `empresa_b` (ayuda@empresab.com)

⚠️ **IMPORTANTE**: Debes actualizar las credenciales después:
```bash
python admin_clients.py update --client-id empresa_a
```

**Opción B: Cliente Real (interactivo)**

```bash
python admin_clients.py add
```

Te preguntará paso a paso:
```
Client ID (ej: cliente_a): mi_empresa
Nombre del Cliente: Mi Empresa S.A.
Email del Cliente: soporte@miempresa.com
Azure Tenant ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Azure Client ID: yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
Azure Client Secret: zzzzzzzzzzzzzzzzzzzz
Schema PostgreSQL: mi_empresa
```

---

### 3️⃣ Verificar Clientes

```bash
python admin_clients.py list
```

**Salida:**
```
CLIENT_ID            EMAIL                          STATUS     SUBSCRIPTION
--------------------------------------------------------------------------------
empresa_a            soporte@empresaa.com           active     sub-empresa-a-inbox-2025...
empresa_b            ayuda@empresab.com             active     sub-empresa-b-inbox-2025...

Total: 2 cliente(s)
```

---

## 📚 COMANDOS DISPONIBLES

### ➕ Agregar Cliente

```bash
python admin_clients.py add
```

**Modo interactivo** - Te pide los datos paso a paso.

**Datos requeridos:**
- Client ID (identificador único)
- Nombre del cliente
- Email institucional
- Credenciales Azure (Tenant ID, Client ID, Secret)
- Schema PostgreSQL

---

### 📋 Listar Clientes

```bash
python admin_clients.py list
```

Muestra tabla con todos los clientes registrados.

---

### 🔍 Ver Detalle de Cliente

```bash
python admin_clients.py get --client-id empresa_a
```

Muestra toda la configuración del cliente en formato JSON.

**Ejemplo de salida:**
```json
{
  "subscription_id": "sub-empresa-a-inbox-20250102",
  "client_id": "empresa_a",
  "client_name": "Empresa A S.A.",
  "client_email": "soporte@empresaa.com",
  "azure_tenant_id": "...",
  "db_config": {
    "schema": "empresa_a"
  },
  "status": "active"
}
```

---

### ✏️ Actualizar Cliente

```bash
python admin_clients.py update --client-id empresa_a
```

Permite actualizar:
- Nombre del cliente
- Email
- Status (active, suspended, expired)

**Ejemplo de sesión:**
```
Actualizar campos (dejar vacío para mantener valor actual):

Nombre [Empresa A S.A.]: 
Email [soporte@empresaa.com]: nuevo-soporte@empresaa.com

Status:
  1. active
  2. suspended
  3. expired
Seleccionar [actual: active]: 1

✅ Cliente actualizado exitosamente!
```

---

### 🗑️ Eliminar Cliente

```bash
python admin_clients.py delete --client-id empresa_a
```

⚠️ **CUIDADO**: Esto elimina PERMANENTEMENTE el cliente de DynamoDB.

Requiere confirmación:
```
⚠️  ¿ELIMINAR ESTE CLIENTE?

Confirmar eliminación (escribir 'DELETE' en mayúsculas): DELETE
```

---

## 🔐 GESTIÓN DE CREDENCIALES

### Credenciales Azure

Cada cliente necesita sus propias credenciales de Azure para acceder a Graph API:

1. **Azure Tenant ID**: ID del tenant de Azure AD del cliente
2. **Azure Client ID**: ID de la aplicación registrada en Azure
3. **Azure Client Secret**: Secret de la aplicación

**¿Dónde obtenerlas?**
- Azure Portal → Azure Active Directory
- App Registrations → Nueva aplicación
- Certificates & Secrets → New client secret

**Permisos requeridos (Graph API):**
- `Mail.Read` (Delegated)
- `Mail.ReadWrite` (Application)
- `MailboxSettings.Read` (Application)

---

### Credenciales PostgreSQL

Cada cliente guarda sus datos en un **schema separado** en PostgreSQL.

**Estructura:**
```
Database: knowledge_base
├── Schema: empresa_a       # Cliente A
│   ├── rag1_documents
│   └── rag2_tickets
├── Schema: empresa_b       # Cliente B
│   ├── rag1_documents
│   └── rag2_tickets
```

**Configuración en DynamoDB:**
```json
"db_config": {
  "host": "postgres-dev.abc123.us-east-1.rds.amazonaws.com",
  "port": 5432,
  "database": "knowledge_base",
  "schema": "empresa_a"
}
```

---

## 🔧 TROUBLESHOOTING

### Error: "Table not found"

**Causa:** Tabla DynamoDB no existe

**Solución:**
```bash
python create_table.py
```

---

### Error: "AccessDeniedException"

**Causa:** Sin permisos para DynamoDB

**Solución:** Agregar política IAM:
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Scan",
    "dynamodb:Query",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/MCP_ClientConfigurations",
    "arn:aws:dynamodb:*:*:table/MCP_ClientConfigurations/index/*"
  ]
}
```

---

### Error: "Client already exists"

**Causa:** Intentas agregar un cliente con `client_id` duplicado

**Solución:**
1. Usar otro `client_id`, o
2. Actualizar el cliente existente:
   ```bash
   python admin_clients.py update --client-id xxx
   ```

---

### No aparecen clientes al listar

**Causa:** DynamoDB vacío

**Solución:**
```bash
# Opción 1: Datos de prueba
python seed_test_clients.py

# Opción 2: Agregar cliente real
python admin_clients.py add
```

---

## 📊 ESTRUCTURA DE CLIENTE EN DYNAMODB

```javascript
{
  // PRIMARY KEY
  "subscription_id": "sub-empresa-a-inbox-20250102",  // PK
  
  // IDENTIFICACIÓN
  "client_id": "empresa_a",                          // Identificador único
  "client_name": "Empresa A S.A.",                   // Nombre para mostrar
  "client_email": "soporte@empresaa.com",            // Email institucional
  
  // CREDENCIALES AZURE
  "azure_tenant_id": "...",                          // Azure AD Tenant
  "azure_client_id": "...",                          // App Registration ID
  "azure_client_secret": "...",                      // Client Secret
  
  // CONFIGURACIÓN BASE DE DATOS
  "db_config": {
    "host": "postgres-dev.xxx.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "database": "knowledge_base",
    "schema": "empresa_a"                            // Schema aislado
  },
  
  // SUBSCRIPTION METADATA
  "subscription_resource": "users/soporte@empresaa.com/messages",
  "subscription_expiry": "2025-01-05T14:30:00Z",
  "webhook_url": "https://api.tudominio.com/webhook",
  
  // ESTADO
  "status": "active",                                // active | suspended | expired
  "created_at": "2025-01-02T10:00:00Z",
  "updated_at": "2025-01-02T10:00:00Z",
  
  // QUOTAS (OPCIONAL)
  "quotas": {
    "max_emails_per_day": 1000,
    "max_file_size_mb": 50
  }
}
```

---

## 🔄 FLUJO DE ONBOARDING DE CLIENTE

### 1. **Preparación (Cliente proporciona datos)**
   - Email institucional donde recibirán notificaciones
   - Credenciales Azure (Tenant ID, Client ID, Secret)
   - Acceso a su Azure AD

### 2. **Agregar Cliente a DynamoDB**
   ```bash
   python admin_clients.py add
   ```

### 3. **Verificar Cliente**
   ```bash
   python admin_clients.py get --client-id nuevo_cliente
   ```

### 4. **Ejecutar Lambda de Suscripción**
   El lambda `dev-webhook-subscription` detectará automáticamente el nuevo cliente y:
   - Se autenticará con sus credenciales Azure
   - Creará su suscripción en Graph API
   - Actualizará el `subscription_id` en DynamoDB

### 5. **Validar Suscripción**
   ```bash
   python admin_clients.py get --client-id nuevo_cliente
   ```
   
   Verificar que `subscription_id` cambió de `pending` a un ID real.

### 6. **Testing**
   - Enviar email de prueba al correo del cliente
   - Verificar que el webhook recibe la notificación
   - Confirmar que el orquestador procesa el email

---

## 🎯 PRÓXIMOS PASOS

Después de configurar clientes:

1. **Modificar `subscription_manager.py`** para leer de DynamoDB
2. **Actualizar handler.py** para iterar sobre clientes
3. **Testing local** con clientes de prueba
4. **Deploy a AWS Lambda**
5. **Monitoreo** vía CloudWatch Logs

---

## 📞 AYUDA

Si tienes problemas:

1. **Verificar tabla existe:**
   ```bash
   aws dynamodb describe-table --table-name MCP_ClientConfigurations
   ```

2. **Listar items:**
   ```bash
   aws dynamodb scan --table-name MCP_ClientConfigurations
   ```

3. **Ver logs detallados:**
   Agregar `--debug` a los scripts (por implementar)

---

## ✅ CHECKLIST

- [ ] Tabla DynamoDB creada
- [ ] Al menos 1 cliente agregado
- [ ] Credenciales Azure validadas
- [ ] Schema PostgreSQL existe
- [ ] Webhook URL configurada
- [ ] Lambda tiene permisos DynamoDB