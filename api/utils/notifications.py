"""Notification helpers for operational alerts."""

from __future__ import annotations

import os
import smtplib
import urllib.parse
import urllib.request
import json
from email.message import EmailMessage
from typing import Optional


DEFAULT_ALERT_RECIPIENT = 'nathan@hudsonitconsulting.com'


def _send_via_graph(
    *,
    alert_recipient: str,
    patient_name: str,
    appointment_time: str,
    note: Optional[str],
    logger,
) -> bool:
    tenant_id = (os.getenv('GRAPH_TENANT_ID') or os.getenv('AZURE_TENANT_ID') or '').strip()
    client_id = (os.getenv('GRAPH_CLIENT_ID') or os.getenv('AZURE_CLIENT_ID') or '').strip()
    client_secret = (os.getenv('GRAPH_CLIENT_SECRET') or '').strip()
    sender_user = (os.getenv('GRAPH_SENDER_USER') or '').strip()

    if not tenant_id or not client_id or not client_secret or not sender_user:
        logger.info('Graph email not configured; falling back to SMTP if available')
        return False

    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    token_payload = urllib.parse.urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials',
    }).encode('utf-8')

    try:
        token_request = urllib.request.Request(
            token_url,
            data=token_payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST',
        )
        with urllib.request.urlopen(token_request, timeout=10) as token_response:
            token_data = json.loads(token_response.read().decode('utf-8'))
        access_token = token_data.get('access_token', '')
        if not access_token:
            logger.error('Graph email send failed: missing access token in response')
            return False

        body_lines = [
            'Unregistered Check-In:',
            '',
            f'Patient: {patient_name}',
            f'Appointment time: {appointment_time}',
        ]
        if note:
            body_lines.extend(['', f'Note: {note}'])

        graph_payload = {
            'message': {
                'subject': 'Unregistered Check-In Alert',
                'body': {
                    'contentType': 'Text',
                    'content': '\n'.join(body_lines),
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': alert_recipient,
                        }
                    }
                ],
            },
            'saveToSentItems': True,
        }

        graph_request = urllib.request.Request(
            f'https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(sender_user)}/sendMail',
            data=json.dumps(graph_payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )

        with urllib.request.urlopen(graph_request, timeout=10):
            pass

        logger.info('Unregistered check-in alert sent via Microsoft Graph to %s', alert_recipient)
        return True
    except Exception as exc:
        logger.error('Failed to send check-in alert via Microsoft Graph: %s', exc)
        return False


def send_unregistered_checkin_alert(
    *,
    patient_name: str,
    appointment_time: str,
    logger,
    note: Optional[str] = None,
) -> bool:
    """Send unregistered check-in alert email to configured recipient.

    Returns True when sent, False when not sent.
    """
    smtp_host = (os.getenv('SMTP_HOST') or '').strip()
    smtp_port = int((os.getenv('SMTP_PORT') or '587').strip())
    smtp_user = (os.getenv('SMTP_USERNAME') or '').strip()
    smtp_password = os.getenv('SMTP_PASSWORD') or ''
    smtp_from = (os.getenv('SMTP_FROM_EMAIL') or smtp_user or '').strip()
    use_tls = (os.getenv('SMTP_USE_TLS') or 'true').strip().lower() in ('1', 'true', 'yes')
    alert_recipient = (os.getenv('CHECKIN_ALERT_EMAIL') or DEFAULT_ALERT_RECIPIENT).strip()

    if _send_via_graph(
        alert_recipient=alert_recipient,
        patient_name=patient_name,
        appointment_time=appointment_time,
        note=note,
        logger=logger,
    ):
        return True

    if not smtp_host or not smtp_from or not alert_recipient:
        logger.warning('Check-in alert email skipped: SMTP configuration incomplete')
        return False

    message = EmailMessage()
    message['Subject'] = 'Unregistered Check-In Alert'
    message['From'] = smtp_from
    message['To'] = alert_recipient

    body_lines = [
        'Unregistered Check-In:',
        '',
        f'Patient: {patient_name}',
        f'Appointment time: {appointment_time}',
    ]
    if note:
        body_lines.extend(['', f'Note: {note}'])

    message.set_content('\n'.join(body_lines))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        logger.info('Unregistered check-in alert email sent to %s', alert_recipient)
        return True
    except Exception as exc:
        logger.error('Failed to send unregistered check-in alert email: %s', exc)
        return False
