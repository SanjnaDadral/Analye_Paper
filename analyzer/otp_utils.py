"""
OTP utilities for password reset functionality
"""

import random
import string
import logging
import threading
from datetime import timedelta

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import PasswordResetOTP

logger = logging.getLogger(__name__)


def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))


def _send_email_task(subject, message, from_email, recipient_list):
    """Background thread task to send email"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"OTP email sent successfully to {recipient_list[0]}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {recipient_list[0]}: {str(e)}", exc_info=True)


def _is_email_configured():
    """Check if real SMTP email credentials are configured"""
    host_user = getattr(settings, 'EMAIL_HOST_USER', '')
    host_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
    # Treat as unconfigured if no credentials or using fallback noreply
    if not host_user or not host_pass:
        return False
    if 'noreply' in from_email and not host_user:
        return False
    return True


def send_otp_email(email, otp):
    """Send OTP email - uses real SMTP if configured, else logs for local dev"""
    subject = "PaperAIzer - Password Reset OTP"
    message = f"""Hello,

Your One-Time Password (OTP) for resetting your PaperAIzer password is:

  {otp}

This OTP is valid for 10 minutes. Do not share this with anyone.

If you did not request this, please ignore this email.

Best regards,
PaperAIzer Team"""

    try:
        logger.info(f"Processing OTP email request for {email}")

        if not _is_email_configured():
            # ── LOCAL / STAGING FALLBACK ──
            # No real SMTP configured: print OTP clearly so testers can use it
            sep = "=" * 60
            logger.warning(sep)
            logger.warning(f"  LOCAL OTP SIMULATOR")
            logger.warning(f"  Email : {email}")
            logger.warning(f"  OTP   : {otp}")
            logger.warning(f"  Valid : 10 minutes")
            logger.warning(sep)
            print(f"\n{sep}")
            print(f"  LOCAL OTP SIMULATOR")
            print(f"  Email : {email}")
            print(f"  OTP   : {otp}")
            print(f"  (copy this code to the verify page)")
            print(f"{sep}\n")
            return True  # Simulate success so redirect happens

        # Real SMTP path — send asynchronously so request doesn't block
        from_email = settings.DEFAULT_FROM_EMAIL
        email_thread = threading.Thread(
            target=_send_email_task,
            args=(subject, message, from_email, [email]),
            daemon=True
        )
        email_thread.start()
        return True

    except Exception as e:
        logger.error(f"Failed to process OTP email for {email}: {str(e)}", exc_info=True)
        return False


def create_and_send_otp(email):
    """Create OTP record and trigger delivery. Returns (reset_otp_obj, email_sent_bool)."""
    try:
        # Reuse existing valid OTP to prevent spam
        existing = PasswordResetOTP.objects.filter(
            email=email,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()

        if existing:
            otp = existing.otp
            reset_otp = existing
            logger.info(f"Reusing existing valid OTP for {email}")
        else:
            # Purge old OTPs for this email
            PasswordResetOTP.objects.filter(email=email).delete()

            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=10)
            reset_otp = PasswordResetOTP.objects.create(
                email=email,
                otp=otp,
                expires_at=expires_at
            )
            logger.info(f"Created new OTP for {email}")

        # Always print to server console for easy dev access
        print(f"\n{'='*50}")
        print(f"  OTP FOR {email}: {otp}")
        print(f"{'='*50}\n")

        email_sent = send_otp_email(email, otp)
        return reset_otp, email_sent

    except Exception as e:
        logger.error(f"Error in create_and_send_otp for {email}: {str(e)}", exc_info=True)
        return None, False


def verify_otp(email, otp):
    """Verify OTP code for a given email"""
    try:
        reset_otp = PasswordResetOTP.objects.get(email=email, otp=otp)
        if reset_otp.is_valid():
            return True, reset_otp
        return False, None
    except PasswordResetOTP.DoesNotExist:
        return False, None


def mark_otp_as_used(email, otp):
    """Mark OTP as used after successful reset"""
    try:
        reset_otp = PasswordResetOTP.objects.get(email=email, otp=otp)
        reset_otp.is_used = True
        reset_otp.save()
        return True
    except PasswordResetOTP.DoesNotExist:
        return False