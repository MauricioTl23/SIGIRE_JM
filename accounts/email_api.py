import os
import requests


def enviar_correo_brevo(destinatario_email, destinatario_nombre, asunto, mensaje):
    """
    Envía un correo electrónico utilizando la API SMTP de Brevo.

    Esta función se usa como servicio auxiliar para mandar correos desde el sistema,
    por ejemplo: credenciales, avisos, notificaciones o mensajes administrativos.

    Parámetros:
    - destinatario_email: correo electrónico del destinatario.
    - destinatario_nombre: nombre del destinatario. Si no se envía, se usa el email.
    - asunto: asunto del correo.
    - mensaje: contenido del correo en texto plano.

    Retorna:
    - La respuesta JSON enviada por Brevo si el correo fue enviado correctamente.

    Excepciones:
    - ValueError: si no existe la API key de Brevo.
    - Exception: si Brevo responde con un error HTTP.
    """

    # Se obtiene la API key desde las variables de entorno.
    # Esta clave NO debe escribirse directamente en el código por seguridad.
    api_key = os.getenv("BREVO_API_KEY")

    # Correo del remitente.
    # Si no existe la variable de entorno, se usa un correo por defecto.
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "secretaria.uejm@gmail.com")

    # Nombre visible del remitente.
    # Si no existe la variable de entorno, se usa "UE Jesús María".
    sender_name = os.getenv("BREVO_SENDER_NAME", "UE Jesús María")

    # Si no existe la API key, se detiene el proceso.
    # Sin esta clave, Brevo no permite enviar correos.
    if not api_key:
        raise ValueError("Falta BREVO_API_KEY en variables de entorno")

    # URL oficial del endpoint SMTP de Brevo para enviar correos.
    url = "https://api.brevo.com/v3/smtp/email"

    # Datos que se enviarán a Brevo.
    # Aquí se define quién envía, quién recibe, el asunto y el mensaje.
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [
            {
                "email": destinatario_email,
                "name": destinatario_nombre or destinatario_email,
            }
        ],
        "subject": asunto,
        "textContent": mensaje,
    }

    # Encabezados de la petición HTTP.
    # Incluyen la API key para autenticar la solicitud ante Brevo.
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    # Se envía la petición POST a Brevo.
    # timeout=20 evita que el sistema quede esperando indefinidamente.
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=20
    )

    # Brevo puede responder con 200, 201 o 202 cuando el envío fue aceptado.
    # Si llega otro código, se considera error.
    if response.status_code not in (200, 201, 202):
        raise Exception(f"Error Brevo {response.status_code}: {response.text}")

    # Se devuelve la respuesta de Brevo en formato JSON.
    return response.json()