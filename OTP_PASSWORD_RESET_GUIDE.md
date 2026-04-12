# Gmail OTP Password Reset - Quick Start Guide

## What Was Implemented

Your Paper Analyzer app now has a secure Gmail OTP-based password reset system. Users can reset forgotten passwords by:

1. **Requesting OTP** - Enter email → OTP sent to Gmail
2. **Verifying OTP** - Enter 6-digit code from email
3. **Setting Password** - Create new password with strength validation

## How to Test It

### Step 1: Start the Server

```bash
cd c:\Users\sanjn\paper\paper_analyzer
python manage.py runserver
```

### Step 2: Access the Forgot Password Page

```
http://127.0.0.1:8000/forgot-password/
```

### Step 3: Test the Flow

**Test Case 1: With Valid Email**

1. Enter an email that's registered in the system
2. Click "Send OTP"
3. Check Gmail inbox for OTP email
4. Copy the 6-digit code from email
5. Enter OTP in the verification page
6. Set new password (min 8 characters)
7. Should redirect to login page

**Test Case 2: With Invalid Email**

- Enter an unregistered email
- System shows success message (security feature)
- No email sent if user doesn't exist

**Test Case 3: Wrong OTP**

- Enter incorrect OTP code
- System shows "Invalid or expired OTP" error
- Can try again or request new OTP

**Test Case 4: Expired OTP**

- Wait 10 minutes after OTP is sent
- Try to enter any OTP
- System shows "Invalid or expired OTP" error

## Files Modified

### New Files Created

- ✅ `analyzer/otp_utils.py` - OTP generation and email sending
- ✅ `templates/analyzer/verify_otp.html` - OTP verification page
- ✅ `templates/analyzer/reset_password.html` - New password page

### Files Updated

- ✅ `analyzer/models.py` - Added PasswordResetOTP model
- ✅ `analyzer/views.py` - Updated password reset views (3 views)
- ✅ `analyzer/urls.py` - Added 2 new URL patterns
- ✅ `templates/analyzer/forgot_password.html` - Updated description

### Database Changes

- ✅ Migration applied: `analyzer.0009_passwordresetotp`
- ✅ New table: `analyzer_passwordresetotp`

## Features

### ✅ Security Features

- OTP auto-expires after 10 minutes
- OTP is one-time use only (marked as used)
- Email verification confirms user identity
- Session-based flow prevents unauthorized access
- CSRF protection on all forms
- Password requirements: minimum 8 characters

### ✅ User Experience

- Real-time password strength indicator (Weak/Fair/Good/Strong)
- Show/hide password toggle
- One-click confirmation checkbox
- Only accepts 6 digits in OTP field
- Clear error messages
- Mobile-responsive design

### ✅ Developer Features

- Utility functions for OTP management
- Clean separation of concerns (otp_utils.py)
- Django best practices followed
- Comprehensive error handling
- Logging for debugging

## Email Configuration

The system uses Gmail SMTP which is already configured in `.env`:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=sanjnadadralh1970@gmail.com
EMAIL_HOST_PASSWORD=zniu nevl hzmi xcvx
DEFAULT_FROM_EMAIL=PaperAIzer <noreply@paperyzer.ai>
```

**Note:** These are Gmail SMTP credentials. Make sure to:

1. Use an [App Password](https://myaccount.google.com/apppasswords) (not main Gmail password)
2. Keep credentials secure
3. Never commit to version control

## URL Routes

| URL                 | Purpose                           |
| ------------------- | --------------------------------- |
| `/forgot-password/` | Request OTP (email input)         |
| `/verify-otp/`      | Verify OTP code (OTP input)       |
| `/reset-password/`  | Set new password (password input) |

## Testing the Email Sending

If you want to verify email sending works:

```python
from analyzer.otp_utils import create_and_send_otp

# Test email sending
otp_obj, email_sent = create_and_send_otp('test@example.com')
if email_sent:
    print("✓ Email sent successfully!")
    print(f"OTP: {otp_obj.otp}")
else:
    print("✗ Email failed to send")
```

## Troubleshooting

### OTP Email Not Arriving

1. **Check Email Address** - Make sure user email is correct in database
2. **Check Gmail Settings** - Verify SMTP credentials in `.env`
3. **Check Logs** - Look for email sending errors in console
4. **Use App Password** - Don't use main Gmail password, use [App Password](https://myaccount.google.com/apppasswords)

### OTP Verification Fails

1. **Check Expiration** - OTP expires after 10 minutes
2. **Check Digits** - Must be exactly 6 digits
3. **Check Typos** - Verify you entered the exact code from email

### Password Reset Not Working

1. **Session Check** - Make sure session data exists (`reset_email`, `otp_verified`)
2. **Password Requirements** - Must be 8+ characters and match confirmation
3. **Checkbox** - Must check "I understand" to enable submit button

## Future Improvements

Possible enhancements:

- [x] ✅ Gmail OTP sending
- [ ] SMS OTP as alternative
- [ ] Resend OTP button with rate limiting
- [ ] HTML email templates
- [ ] Multiple device check
- [ ] Save login session after reset
- [ ] Two-factor authentication (2FA)
- [ ] OTP request logging/audit trail

## Support

For issues or questions, refer to:

- `GMAIL_OTP_PASSWORD_RESET.md` - Technical documentation
- `analyzer/otp_utils.py` - OTP utilities source code
- `analyzer/views.py` - View implementations (forgot_password, verify_otp, reset_password)
