"""Email notification system using SendGrid."""
import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent


def _get_client():
    """Get SendGrid client, or None if not configured."""
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        return None
    return SendGridAPIClient(api_key)


def send_email(to_email, subject, html_body, text_body=None):
    """Send an email via SendGrid. Falls back to logging in dev."""
    from_email = os.environ.get('NOTIFICATION_FROM_EMAIL', 'support@maiatech.ai')
    from_name = os.environ.get('NOTIFICATION_FROM_NAME', 'Vilora')

    client = _get_client()
    if not client:
        sys.stderr.write(f"[Vilora] SendGrid not configured. Email to {to_email}: {subject}\n")
        sys.stderr.write(f"[Vilora] Body preview: {html_body[:200]}\n")
        return False

    message = Mail(
        from_email=Email(from_email, from_name),
        to_emails=To(to_email),
        subject=subject,
        html_content=HtmlContent(html_body)
    )

    if text_body:
        message.add_content(Content("text/plain", text_body))

    try:
        response = client.send(message)
        sys.stderr.write(f"[Vilora] Email sent to {to_email}: {subject} (status {response.status_code})\n")
        return response.status_code in (200, 201, 202)
    except Exception as e:
        sys.stderr.write(f"[Vilora] Email send failed to {to_email}: {e}\n")
        return False


def send_invite_email(to_email, creator_name, topic, join_link, personal_message=None):
    """Send a branded session invite email."""
    subject = f"{creator_name} invited you to a conversation on Vilora"

    message_section = ""
    if personal_message:
        message_section = f"""
        <div style="background:#F7F8F7;border-radius:8px;padding:16px;margin:20px 0;">
            <p style="margin:0;color:#555550;font-size:14px;font-style:italic;">"{personal_message}"</p>
            <p style="margin:8px 0 0;color:#888780;font-size:12px;">{creator_name}</p>
        </div>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0;padding:0;background:#F7F8F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F8F7;padding:40px 20px;">
            <tr><td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#FFFFFF;border-radius:8px;overflow:hidden;">
                    <!-- Header -->
                    <tr><td style="padding:32px 32px 24px;text-align:center;">
                        <img src="https://www.vilora.ai/static/img/email-logo.png" alt="Vilora" width="160" style="display:block;margin:0 auto;">
                    </td></tr>

                    <!-- Body -->
                    <tr><td style="padding:0 32px 32px;">
                        <h2 style="font-size:18px;font-weight:500;color:#2C2C2A;margin:0 0 8px;">You've been invited to a conversation</h2>
                        <p style="color:#555550;font-size:15px;line-height:1.6;margin:0 0 16px;">
                            <strong>{creator_name}</strong> would like to have a conversation with you on Vilora, an AI-powered platform for productive dialogue.
                        </p>

                        <div style="background:#E1F5EE;border-radius:8px;padding:16px;margin:16px 0;">
                            <p style="margin:0;color:#085041;font-size:14px;font-weight:500;">Topic</p>
                            <p style="margin:4px 0 0;color:#2C2C2A;font-size:15px;">{topic}</p>
                        </div>

                        {message_section}

                        <div style="text-align:center;margin:28px 0;">
                            <a href="{join_link}" style="display:inline-block;padding:14px 32px;background:#1D9E75;color:#ffffff;text-decoration:none;border-radius:8px;font-size:16px;font-weight:500;">Join the conversation</a>
                        </div>

                        <div style="border-top:1px solid #E2E0D8;padding-top:20px;margin-top:20px;">
                            <p style="color:#888780;font-size:13px;line-height:1.6;margin:0;">
                                <strong>What to expect:</strong> Vilora is an AI facilitator that helps people have productive conversations,
                                whether you're working through a challenge, brainstorming, or making a decision together.
                                Your conversation is shared only with the other participants. Vilora does not share your information with anyone else.
                            </p>
                        </div>
                    </td></tr>

                    <!-- Footer -->
                    <tr><td style="padding:20px 32px;background:#F7F8F7;border-top:1px solid #E2E0D8;">
                        <p style="margin:0;color:#888780;font-size:12px;text-align:center;">Vilora | Strength through dialogue</p>
                        <p style="margin:4px 0 0;color:#888780;font-size:10px;text-align:center;">AI-powered mediation, collaboration, brainstorming, and decision-making</p>
                        <p style="margin:8px 0 0;color:#888780;font-size:11px;text-align:left;">
                            You received this because {creator_name} invited you. If this wasn't meant for you, you can safely ignore it.
                        </p>
                    </td></tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """

    text_body = (
        f"{creator_name} invited you to a conversation on Vilora.\n\n"
        f"Topic: {topic}\n\n"
        f"{f'Message: {personal_message}\n\n' if personal_message else ''}"
        f"Join here: {join_link}\n\n"
        f"Vilora is an AI-powered platform for productive dialogue. "
        f"Your conversation is shared only with participants.\n\n"
        f"Vilora | Strength through dialogue\n"
        f"AI-powered mediation, collaboration, brainstorming, and decision-making"
    )

    return send_email(to_email, subject, html_body, text_body)


def send_nudge_email(to_email, nudger_name, recipient_name, topic, session_link):
    """Send a friendly nudge email to remind a participant to respond."""
    subject = f"{nudger_name} is waiting for you on Vilora"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0;padding:0;background:#F7F8F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F8F7;padding:40px 20px;">
            <tr><td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#FFFFFF;border-radius:8px;overflow:hidden;">
                    <tr><td style="padding:32px 32px 24px;text-align:center;">
                        <img src="https://www.vilora.ai/static/img/email-logo.png" alt="Vilora" width="160" style="display:block;margin:0 auto;">
                    </td></tr>
                    <tr><td style="padding:0 32px 32px;">
                        <h2 style="font-size:18px;font-weight:500;color:#2C2C2A;margin:0 0 16px;">Hey {recipient_name}, your conversation is waiting</h2>
                        <p style="color:#555550;font-size:15px;line-height:1.6;">
                            <strong>{nudger_name}</strong> wanted to check in. Your conversation about
                            <strong>{topic}</strong> has new activity and they'd love to hear your thoughts.
                        </p>
                        <p style="color:#555550;font-size:15px;line-height:1.6;">
                            No pressure. Just a friendly reminder that the conversation is there whenever you're ready.
                        </p>
                        <div style="text-align:center;margin:28px 0;">
                            <a href="{session_link}" style="display:inline-block;padding:14px 32px;background:#1D9E75;color:#ffffff;text-decoration:none;border-radius:8px;font-size:16px;font-weight:500;">Continue the conversation</a>
                        </div>
                    </td></tr>
                    <tr><td style="padding:20px 32px;background:#F7F8F7;border-top:1px solid #E2E0D8;">
                        <p style="margin:0;color:#888780;font-size:12px;text-align:center;">Vilora | Strength through dialogue</p>
                        <p style="margin:4px 0 0;color:#888780;font-size:10px;text-align:center;">AI-powered mediation, collaboration, brainstorming, and decision-making</p>
                    </td></tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """

    text_body = (
        f"Hey {recipient_name},\n\n"
        f"{nudger_name} wanted to check in. Your conversation about \"{topic}\" "
        f"has new activity and they'd love to hear your thoughts.\n\n"
        f"Continue here: {session_link}\n\n"
        f"No pressure. Just a friendly reminder.\n\n"
        f"Vilora | Strength through dialogue\n"
        f"AI-powered mediation, collaboration, brainstorming, and decision-making"
    )

    return send_email(to_email, subject, html_body, text_body)


def send_password_reset_email(to_email, display_name, reset_link):
    """Send a branded password reset email."""
    subject = "Password Reset - Vilora"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0;padding:0;background:#F7F8F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F8F7;padding:40px 20px;">
            <tr><td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#FFFFFF;border-radius:8px;overflow:hidden;">
                    <tr><td style="padding:32px 32px 24px;text-align:center;">
                        <img src="https://www.vilora.ai/static/img/email-logo.png" alt="Vilora" width="160" style="display:block;margin:0 auto;">
                    </td></tr>
                    <tr><td style="padding:0 32px 32px;">
                        <h2 style="font-size:18px;font-weight:500;color:#2C2C2A;margin:0 0 16px;">Password Reset</h2>
                        <p style="color:#555550;font-size:15px;line-height:1.6;">Hi {display_name},</p>
                        <p style="color:#555550;font-size:15px;line-height:1.6;">You requested a password reset for your Vilora account.</p>
                        <div style="text-align:center;margin:28px 0;">
                            <a href="{reset_link}" style="display:inline-block;padding:14px 32px;background:#1D9E75;color:#ffffff;text-decoration:none;border-radius:8px;font-size:16px;font-weight:500;">Reset Password</a>
                        </div>
                        <p style="color:#888780;font-size:13px;line-height:1.6;">Or copy this link: {reset_link}</p>
                        <p style="color:#888780;font-size:13px;line-height:1.6;">This link expires in 1 hour. If you didn't request this, you can safely ignore this email.</p>
                    </td></tr>
                    <tr><td style="padding:20px 32px;background:#F7F8F7;border-top:1px solid #E2E0D8;text-align:center;">
                        <p style="margin:0;color:#888780;font-size:12px;">Vilora | Strength through dialogue</p>
                        <p style="margin:4px 0 0;color:#888780;font-size:10px;">AI-powered mediation, collaboration, brainstorming, and decision-making</p>
                    </td></tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """

    text_body = (
        f"Hi {display_name},\n\n"
        f"You requested a password reset for your Vilora account.\n\n"
        f"Reset your password: {reset_link}\n\n"
        f"This link expires in 1 hour. If you didn't request this, ignore this email.\n\n"
        f"Vilora"
    )

    return send_email(to_email, subject, html_body, text_body)
