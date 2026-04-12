"""
OTP utilities for password reset functionality
"""

import random
import string
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetOTP

logger = logging.getLogger(__name__)


def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(email, otp):
    """Send OTP to user's email"""
    subject = "PaperAIzer - Password Reset OTP"
    message = f"""
    Hello,

    Your One-Time Password (OTP) for resetting your PaperAIzer password is:

    {otp}

    This OTP is valid for 10 minutes. Please do not share this code with anyone.

    If you didn't request a password reset, please ignore this email.

    Best regards,
    PaperAIzer Team
    """
    
    try:
        logger.info(f"Attempting to send OTP email to {email}")
        from_email = f"PaperAIzer <{settings.EMAIL_HOST_USER}>" if settings.EMAIL_HOST_USER else settings.DEFAULT_FROM_EMAIL
        send_mail(
            subject,
            message,
            from_email,
            [email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {email}: {str(e)}", exc_info=True)
        return False


def create_and_send_otp(email):
    """Create a new OTP record and send it to the email"""
    # Check for existing unexpired OTP first to prevent race conditions if user clicks multiple times
    existing = PasswordResetOTP.objects.filter(email=email, is_used=False, expires_at__gt=timezone.now()).order_by('-created_at').first()
    
    if existing:
        otp = existing.otp
        reset_otp = existing
    else:
        # Delete any expired logic
        PasswordResetOTP.objects.filter(email=email, is_used=False).delete()
        
        # Generate OTP
        otp = generate_otp()
        
        # Calculate expiration time (10 minutes)
        expires_at = timezone.now() + timedelta(minutes=10)
        
        # Create OTP record
        reset_otp = PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
            expires_at=expires_at
        )

    # FOR DEVELOPMENT: Print the OTP to the console so we can use it without checking email
    print(f"\n{'='*40}")
    print(f"🔑 OTP FOR {email} IS: {otp}")
    print(f"{'='*40}\n")
    
    # Send email
    email_sent = send_otp_email(email, otp)
    
    return reset_otp, email_sent


def verify_otp(email, otp):
    """Verify if the provided OTP is valid for the given email"""
    try:
        reset_otp = PasswordResetOTP.objects.get(email=email, otp=otp)
        
        if reset_otp.is_valid():
            return True, reset_otp
        else:
            return False, None
    except PasswordResetOTP.DoesNotExist:
        return False, None


def mark_otp_as_used(email, otp):
    """Mark the OTP as used after successful verification"""
    try:
        reset_otp = PasswordResetOTP.objects.get(email=email, otp=otp)
        reset_otp.is_used = True
        reset_otp.save()
        return True
    except PasswordResetOTP.DoesNotExist:
        return False
