import argparse
import os

from notifications import send_email


def main() -> int:
    parser = argparse.ArgumentParser(description="Envía el resumen del pipeline por Gmail.")
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--job", default=os.getenv("JOB_NAME", "DevOps pipeline"))
    parser.add_argument("--build-number", default=os.getenv("BUILD_NUMBER", "unknown"))
    parser.add_argument("--branch", default=os.getenv("BRANCH_NAME", "unknown"))
    parser.add_argument("--build-url", default=os.getenv("BUILD_URL", "no disponible"))
    parser.add_argument("--commit", default="unknown")
    args = parser.parse_args()

    subject = f"Reporte Jenkins: {args.job} #{args.build_number} - {args.status}"
    body = "\n".join(
        [
            "Reporte de ejecución CI/CD",
            "",
            f"Job: {args.job}",
            f"Build: #{args.build_number}",
            f"Rama: {args.branch}",
            f"Commit: {args.commit}",
            f"Resultado: {args.status}",
            f"Detalle: {args.build_url}",
        ]
    )
    result = send_email(
        recipient=args.recipient,
        subject=subject,
        body=body,
        sender=os.getenv("GMAIL_USER"),
        app_password=os.getenv("GMAIL_APP_PASSWORD"),
    )
    print(result)
    return 0 if result.startswith("Notificación enviada") else 1


if __name__ == "__main__":
    raise SystemExit(main())