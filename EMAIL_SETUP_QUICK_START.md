# Email Setup - Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Get Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" → "Windows Computer"
3. Copy the 16-character password (with spaces)

### Step 2: Update .env File

```bash
# Copy .env.example to .env (if not already done)
cp .env.example .env
```

Edit `.env`:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=PaperAIzer <your-email@gmail.com>
```

### Step 3: Test Locally

```bash
# Start Django shell
python manage.py shell

# Test email sending
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'This is a test email from PaperAIzer',
    'your-email@gmail.com',
    ['recipient@example.com'],
    fail_silently=False,
)
```

If successful, you'll see: `1` (meaning 1 email sent)

### Step 4: Test Forgot Password Flow

1. Go to http://localhost:8000/forgot-password/
2. Enter your email
3. Check console for OTP
4. Go to http://localhost:8000/verify-otp/
5. Enter OTP
6. Set new password
7. Login with new password

### Step 5: Deploy to Render

1. Go to Render Dashboard
2. Select your service
3. Go to "Environment"
4. Add these variables:
   - `EMAIL_HOST` = `smtp.gmail.com`
   - `EMAIL_PORT` = `587`
   - `EMAIL_USE_TLS` = `True`
   - `EMAIL_HOST_USER` = your Gmail
   - `EMAIL_HOST_PASSWORD` = App password
   - `DEFAULT_FROM_EMAIL` = your email

5. Click "Save"
6. Service will auto-redeploy

---

## ✅ Verification Checklist

- [ ] Email credentials in .env
- [ ] Test email sends successfully
- [ ] Forgot password OTP arrives
- [ ] Can reset password with OTP
- [ ] Contact form saves messages
- [ ] Credentials added to Render
- [ ] Service redeployed on Render

---

## 🔧 Troubleshooting

### "SMTPAuthenticationError"
- Check Gmail app password is correct
- Verify 2FA is enabled on Gmail
- Try generating new app password

### "Connection refused"
- Check EMAIL_HOST and EMAIL_PORT
- Verify firewall allows SMTP
- Check EMAIL_USE_TLS is True

### "Email not received"
- Check spam folder
- Verify recipient email is correct
- Check logs for errors

### "Timeout"
- Increase EMAIL_TIMEOUT in settings.py
- Check internet connection
- Try different email provider

---

## 📧 Email Providers

### Gmail (Recommended)
- Free
- Reliable
- Easy setup
- 500 emails/day limit

### SendGrid
- 100 free emails/day
- Better for production
- More reliable

### AWS SES
- Pay-per-use
- Best for high volume
- More complex setup

---

## 🚀 Production Tips

1. **Use environment variables** - Never hardcode credentials
2. **Monitor email logs** - Check for delivery failures
3. **Set up alerts** - Get notified of email errors
4. **Test regularly** - Verify email still works
5. **Use transactional email service** - For production scale

---

**Setup Time:** ~5 minutes  
**Difficulty:** Easy ⭐
