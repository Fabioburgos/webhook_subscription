# Documentación: Lambda de Suscripción de Webhooks

## 1. Propósito y Funcionamiento General

El proyecto **business_webhook_subscription** consiste en una función AWS Lambda multi-tenant diseñada para gestionar y renovar automáticamente las suscripciones a webhooks de la API de Microsoft Graph. Su objetivo principal es asegurar la continuidad de las notificaciones de eventos (como la recepción de nuevos correos) para múltiples clientes, evitando la expiración de las suscripciones.

La Lambda se ejecuta de forma programada (a través de Amazon EventBridge) y realiza las siguientes acciones para cada cliente activo registrado en una tabla de DynamoDB:

1.  **Autenticación**: Obtiene un token de acceso a la API de Microsoft Graph utilizando las credenciales específicas del cliente (ID de tenant, ID de cliente y secreto de cliente de Azure).
2.  **Verificación de Suscripción**: Comprueba el estado de la suscripción de webhook actual.
3.  **Creación o Renovación**: Si la suscripción no existe, está pendiente de creación inicial o próxima a expirar (generalmente dentro de las siguientes 12 horas), la función crea una nueva suscripción con una validez extendida (típicamente 3 días).
4.  **Actualización de Estado**: Guarda en DynamoDB el ID y la nueva fecha de expiración de la suscripción recién creada.

El sistema está diseñado para ser **idempotente**, lo que significa que ejecuciones repetidas no generan suscripciones duplicadas ni efectos adversos.

## 2. Flujo de Creación Automática de Suscripciones

El proceso de creación y renovación de suscripciones es completamente automático y sigue estos pasos:

1.  **Disparo Programado (Trigger)**: Una regla de **Amazon EventBridge** invoca la función Lambda (`handler.py`) en un intervalo recurrente (ej. cada 2 días).
2.  **Obtención de Clientes Activos**: La función consulta la tabla de DynamoDB (por defecto, `MCP_ClientConfigurations`) para obtener una lista de todos los clientes con estado `active`. Esta operación es gestionada por `src/dynamodb_client.py`.
3.  **Procesamiento por Cliente**: El sistema itera sobre cada cliente de la lista.
4.  **Lógica de Renovación**: Para cada cliente, el `SubscriptionManager` (`src/subscription_manager.py`) determina si es necesario crear una nueva suscripción. Esto ocurre si:
    *   El `subscription_id` tiene un valor temporal como `pending-CLIENTE-FECHA`, indicando una configuración inicial.
    *   La fecha de expiración (`subscription_expiry`) está a menos de 12 horas en el futuro.
5.  **Creación de la Suscripción**: Si se requiere una nueva suscripción, se envía una petición `POST` al endpoint `/subscriptions` de la API de Microsoft Graph. La petición incluye:
    *   `changeType`: `created` (para notificar nuevos correos).
    *   `notificationUrl`: El endpoint del webhook del cliente donde se recibirán las notificaciones.
    *   `resource`: El recurso a monitorizar (ej. `users/{user-id}/mailFolders('inbox')/messages`).
    *   `expirationDateTime`: La nueva fecha de expiración.
6.  **Actualización en DynamoDB**: Una vez que Microsoft Graph confirma la creación, la función actualiza el registro del cliente en DynamoDB con el nuevo `subscription_id` y `subscription_expiry`. Como el `subscription_id` es la clave primaria de la tabla, esta actualización se realiza eliminando el registro antiguo y creando uno nuevo con la información actualizada.

## 3. Configuraciones Necesarias

Para que la Lambda funcione correctamente, se requieren dos tipos de configuraciones: variables de entorno para la configuración global y un registro por cliente en DynamoDB.

### 3.1. Variables de Entorno

Estas variables se definen en la configuración de la función Lambda y son gestionadas por `src/config.py`:

| Variable              | Descripción                                                              | Valor por Defecto          |
| --------------------- | ------------------------------------------------------------------------ | -------------------------- |
| `DYNAMODB_TABLE`      | Nombre de la tabla en DynamoDB que almacena la configuración de clientes. | `MCP_ClientConfigurations` |
| `AWS_REGION`          | Región de AWS donde se encuentra la tabla de DynamoDB.                   | `us-east-2`                |
| `LOG_LEVEL`           | Nivel de logging de la aplicación (INFO, DEBUG, etc.).                   | `INFO`                     |
| `LAMBDA_VERSION`      | Versión de la función Lambda (utilizada para logging).                   | `N/A`                      |
| `WEBHOOK_URL_BASE`    | URL base para los webhooks (aunque la URL final se toma de DynamoDB).    | `N/A`                      |

### 3.2. Configuración de Clientes en DynamoDB

Cada cliente requiere un ítem en la tabla de DynamoDB con la siguiente estructura (ver `docs/PLANTILLA_CLIENTE_DYNAMODB.md`):

-   `subscription_id` (String, **Clave Primaria**): ID único de la suscripción de Graph. Para clientes nuevos, se usa un placeholder como `pending-NOMBRE_CLIENTE-FECHA`.
-   `client_id` (String, **Índice Secundario Global**): Identificador único y legible para el cliente.
-   `azure_tenant_id` (String): ID del tenant de Azure del cliente.
-   `azure_client_id` (String): ID de la aplicación de Azure registrada.
-   `azure_client_secret` (String): Secreto de la aplicación de Azure.
-   `target_user_email` (String): Correo del usuario cuya bandeja de entrada se monitorizará.
-   `webhook_notification_url` (String): URL del endpoint que recibirá las notificaciones de Microsoft Graph.
-   `status` (String): Estado del cliente (`active` para ser procesado, `suspended` para ser ignorado).
-   `subscription_expiry` (String): Fecha y hora de expiración de la suscripción en formato ISO 8601.

## 4. Interacción con DynamoDB

La interacción con DynamoDB está centralizada en la clase `DynamoDBClient` (`src/dynamodb_client.py`). Esta clase abstrae las operaciones de lectura y escritura.

-   **Lectura**: El método `get_active_clients` es el punto de entrada principal. Escanea la tabla de DynamoDB y devuelve todos los ítems cuyo atributo `status` es `active`.
-   **Actualización**: La actualización de una suscripción es una operación crítica. Dado que el `subscription_id` (la clave primaria) cambia con cada renovación, no se puede hacer una actualización simple. El proceso es:
    1.  Se obtiene el registro completo del cliente usando el `subscription_id` antiguo.
    2.  Se elimina el ítem antiguo de la tabla.
    3.  Se crea un nuevo ítem con los mismos datos del cliente, pero con el `subscription_id` y `subscription_expiry` nuevos.

## 5. Endpoint del API Gateway

Es fundamental aclarar que **este proyecto no implementa el endpoint del API Gateway que recibe las notificaciones de Microsoft Graph**.

El rol de esta Lambda es únicamente **crear y mantener las suscripciones**. La URL a la que Microsoft Graph envía las notificaciones (`notificationUrl`) es un dato que se configura por cliente en la tabla de DynamoDB. Dicho endpoint es parte de otro servicio o sistema, que debe estar preparado para:

1.  Responder al `POST` de validación que Microsoft Graph envía al crear la suscripción.
2.  Recibir y procesar las notificaciones de eventos (nuevos correos) en formato JSON.

## 6. Ejemplo de Payload de Microsoft Graph

Cuando ocurre un evento (ej. llega un nuevo correo), Microsoft Graph envía una notificación al `notificationUrl` con un payload similar al siguiente. Este es un ejemplo para una notificación de un nuevo mensaje:

```json
{
  "value": [
    {
      "subscriptionId": "a3b4c5d6-e7f8-90g1-h2i3-j4k5l6m7n8o9",
      "subscriptionExpirationDateTime": "2026-01-12T10:00:00.000Z",
      "changeType": "created",
      "resource": "users('user-id-example')/messages('message-id-example')",
      "resourceData": {
        "@odata.type": "#Microsoft.Graph.Message",
        "@odata.id": "users('user-id-example')/messages('message-id-example')",
        "id": "AAMkAGVmMDEzMTM4LTZmYWUtNDdkNC1hMDZiLTU1OGY5OTZhYmY4OABGAAAAAAAiQ8W967B7TKBjgx9rVEURBwB-f_9j3_9dSKO6_9j3_9dSAAAAAAEMAAB-f_9j3_9dSKO6_9j3_9dSAAAy_9j3AAA=",
        "createdDateTime": "2026-01-09T15:30:00Z",
        "lastModifiedDateTime": "2026-01-09T15:30:00Z"
      },
      "clientState": "secretClientValue",
      "tenantId": "tenant-id-example"
    }
  ]
}
```

El servicio receptor debe usar el `resource` y el `id` del mensaje para luego hacer una petición adicional a la API de Graph y obtener el contenido completo del correo si es necesario.
