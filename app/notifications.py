import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(recipient: str, subject: str, body: str, sender: str | None, app_password: str | None) -> str:
    """Envía un correo de texto vía Gmail SMTP con contraseña de aplicación."""
    if not sender or not app_password:
        return "Error: Credenciales de Gmail no configuradas."

    try:
        message = MIMEMultipart()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, [recipient], message.as_string())
        return f"Notificación enviada a {recipient}."
    except Exception as error:
        return f"Error al enviar correo: {error}"