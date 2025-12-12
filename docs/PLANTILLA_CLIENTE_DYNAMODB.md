# PLANTILLA PARA AGREGAR CLIENTE EN DYNAMODB

## Instrucciones

1. **Ir a AWS Console → DynamoDB**
2. **Tables → MCP_ClientConfigurations**
3. **Actions → Create item**
4. **Cambiar de Form a JSON** (toggle en la esquina superior derecha)
5. **Copiar y pegar esta plantilla**
6. **Reemplazar los valores** según el cliente
7. **Create item**

---

## Plantilla JSON (Copiar desde aquí ↓)

```json
{
  "subscription_id": "pending-NOMBRE_CLIENTE-20250102",
  "client_id": "NOMBRE_CLIENTE",
  "client_name": "Nombre Completo de la Empresa S.A.",
  "client_email": "soporte@empresa.com",
  "azure_tenant_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "azure_client_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
  "azure_client_secret": "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
  "db_config": {
    "host": "postgres-dev.abc123.us-east-2.rds.amazonaws.com",
    "port": 5432,
    "database": "knowledge_base",
    "schema": "NOMBRE_CLIENTE"
  },
  "subscription_resource": "users/soporte@empresa.com/messages",
  "subscription_expiry": "2025-01-01T00:00:00Z",
  "webhook_url": "https://api.tudominio.com/webhook",
  "status": "active",
  "created_at": "2025-01-02T10:00:00Z",
  "updated_at": "2025-01-02T10:00:00Z",
  "quotas": {
    "max_emails_per_day": 1000,
    "max_file_size_mb": 50
  }
}
```

---

## Campos a Reemplazar

### subscription_id
**Formato:** `pending-NOMBRE_CLIENTE-YYYYMMDD`
**Ejemplo:** `pending-empresa_a-20250102`
**Nota:** Esto es temporal. El lambda lo actualizará automáticamente con el ID real de Graph API.

### client_id
**Descripción:** Identificador único del cliente (sin espacios, lowercase)
**Ejemplo:** `empresa_a`, `mi_empresa`, `cliente_xyz`
**Reglas:** 
- Solo letras minúsculas, números y guiones bajos
- Debe ser único en toda la tabla
- Se usará como nombre del schema en PostgreSQL

### client_name
**Descripción:** Nombre completo de la empresa para mostrar
**Ejemplo:** `Empresa A S.A.`, `Mi Empresa Ltd.`

### client_email
**Descripción:** Email institucional del cliente donde recibirá notificaciones
**Ejemplo:** `soporte@empresaa.com`, `ayuda@miempresa.com`
**IMPORTANTE:** Este email debe estar registrado en el Azure AD del cliente

### azure_tenant_id
**Descripción:** ID del tenant de Azure AD del cliente
**¿Dónde obtenerlo?**
- Azure Portal → Azure Active Directory → Overview
- Copiar "Tenant ID"
**Formato:** `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`

### azure_client_id
**Descripción:** ID de la aplicación registrada en Azure AD
**¿Dónde obtenerlo?**
- Azure Portal → Azure Active Directory → App registrations
- Seleccionar la app → Overview
- Copiar "Application (client) ID"
**Formato:** `11111111-2222-3333-4444-555555555555`

### azure_client_secret
**Descripción:** Secret de la aplicación de Azure
**¿Dónde obtenerlo?**
- Azure Portal → Azure Active Directory → App registrations
- Seleccionar la app → Certificates & secrets
- New client secret → Copiar el VALUE (no el ID)
**IMPORTANTE:** Guárdalo de inmediato, solo se muestra una vez

### db_config.host
**Descripción:** Hostname del servidor PostgreSQL
**Ejemplo:** `postgres-dev.abc123.us-east-1.rds.amazonaws.com`
**Obtener:** AWS Console → RDS → Databases → Endpoint

### db_config.schema
**Descripción:** Nombre del schema en PostgreSQL para este cliente
**Recomendación:** Usar el mismo valor de `client_id`
**Ejemplo:** Si `client_id` es `empresa_a`, schema es `empresa_a`

### webhook_url
**Descripción:** URL del orquestador que recibirá notificaciones
**Ejemplo:** `https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook`
**Obtener:** AWS Console → API Gateway → Tu API → Endpoint

### status
**Valores válidos:**
- `active` - Cliente activo (default)
- `suspended` - Cliente suspendido temporalmente
- `expired` - Cliente inactivo

**Usar:** `active` para clientes nuevos

### created_at / updated_at
**Formato:** ISO 8601 con timezone UTC
**Ejemplo:** `2025-01-02T10:00:00Z`
**Recomendación:** Usar la fecha/hora actual

---

## Ejemplo Completo con Datos Reales

```json
{
  "subscription_id": "pending-acme_corp-20250102",
  "client_id": "acme_corp",
  "client_name": "ACME Corporation S.A.",
  "client_email": "soporte@acmecorp.com",
  "azure_tenant_id": "12345678-1234-1234-1234-123456789012",
  "azure_client_id": "87654321-4321-4321-4321-210987654321",
  "azure_client_secret": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "db_config": {
    "host": "postgres-prod.xyz789.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "database": "knowledge_base",
    "schema": "acme_corp"
  },
  "subscription_resource": "users/soporte@acmecorp.com/messages",
  "subscription_expiry": "2025-01-05T00:00:00Z",
  "webhook_url": "https://xyz123.execute-api.us-east-1.amazonaws.com/prod/webhook",
  "status": "active",
  "created_at": "2025-01-02T14:30:00Z",
  "updated_at": "2025-01-02T14:30:00Z",
  "quotas": {
    "max_emails_per_day": 1000,
    "max_file_size_mb": 50
  }
}
```

---

## Validación Después de Agregar

### 1. Verificar que el cliente aparece en DynamoDB
**AWS Console → DynamoDB → Tables → MCP_ClientConfigurations → Explore items**

### 2. Ejecutar el lambda manualmente (opcional)
**AWS Console → Lambda → dev-webhook-subscription → Test**

Esto forzará que el lambda:
- Lea el cliente nuevo
- Cree la suscripción en Graph API
- Actualice el subscription_id en DynamoDB

### 3. Verificar que subscription_id cambió
**Volver a DynamoDB y verificar que `subscription_id` ya no es "pending-..."**
Debería ser algo como: `sub-usuarios/soporte@acme.com/messages/...`

---

## Checklist para Agregar Cliente Nuevo

- [ ] Obtener credenciales Azure del cliente (Tenant ID, Client ID, Secret)
- [ ] Verificar que el email está registrado en su Azure AD
- [ ] Copiar plantilla JSON
- [ ] Reemplazar TODOS los campos marcados con MAYÚSCULAS
- [ ] Verificar que `client_id` es único
- [ ] Crear item en DynamoDB
- [ ] (Opcional) Ejecutar lambda manualmente para forzar suscripción
- [ ] Verificar que `subscription_id` se actualizó
- [ ] Enviar email de prueba para validar flujo completo

---

## Notas Importantes

**Seguridad:**
- El `azure_client_secret` se guarda en texto plano en DynamoDB
- **TODO:** Migrar a AWS Secrets Manager para producción
- Por ahora está OK para desarrollo/testing

**subscription_id inicial:**
- Siempre usar formato `pending-NOMBRE-FECHA`
- El lambda lo detectará y creará la suscripción
- Después se actualizará con el ID real

**Schema PostgreSQL:**
- Debe coincidir con `client_id`
- El sistema creará el schema automáticamente si no existe
- Usa Row-Level Security para aislamiento de datos

**Webhook URL:**
- Debe ser la misma para TODOS los clientes (por ahora)
- El orquestador diferenciará clientes por `subscription_id`
- Más adelante podemos usar URLs diferentes por cliente si es necesario