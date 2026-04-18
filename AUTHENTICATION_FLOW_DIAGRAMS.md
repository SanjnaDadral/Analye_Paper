# Authentication & Email Flow Diagrams

---

## 1. Login Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      LOGIN FLOW                             │
└─────────────────────────────────────────────────────────────┘

User visits /login/
        ↓
Is user authenticated?
        ├─ YES → Redirect to /dashboard/
        └─ NO → Show login form
                ↓
        User enters email/username + password
                ↓
        Submit form (POST /login/)
                ↓
        EmailOrUsernameModelBackend validates
                ├─ VALID → Create session
                │          ↓
                │          Redirect to /dashboard/
                │          ↓
                │          ✅ SUCCESS
                │
                └─ INVALID → Show error message
                             ↓
                             Reload login form

Database Queries:
- SELECT * FROM auth_user WHERE email = ? OR username = ?
- Verify password hash
- Create session record
```

---

## 2. Registration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   REGISTRATION FLOW                         │
└─────────────────────────────────────────────────────────────┘

User visits /register/
        ↓
Is user authenticated?
        ├─ YES → Redirect to /dashboard/
        └─ NO → Show registration form
                ↓
        User enters name, email, password
                ↓
        Submit form (POST /register/)
                ↓
        Validate form data
        ├─ Email format valid?
        ├─ Password strong enough?
        └─ Passwords match?
                ↓
        Check if email already exists
        ├─ EXISTS → Show error "Email already registered"
        │           ↓
        │           Reload form
        │
        └─ NOT EXISTS → Create user
                        ├─ Hash password
                        ├─ Save to database
                        └─ Create session
                           ↓
                           Auto-login user
                           ↓
                           Redirect to /dashboard/
                           ↓
                           ✅ SUCCESS

Database Queries:
- SELECT * FROM auth_user WHERE email = ?
- INSERT INTO auth_user (username, email, password, ...)
- Create session record
```

---

## 3. Forgot Password & OTP Flow

```
┌─────────────────────────────────────────────────────────────┐
│              FORGOT PASSWORD & OTP FLOW                     │
└─────────────────────────────────────────────────────────────┘

User visits /forgot-password/
        ↓
User enters email
        ↓
Submit form (POST /forgot-password/)
        ↓
Check if email exists in database
        ├─ NOT EXISTS → Show error "No account found"
        │               ↓
        │               Reload form
        │
        └─ EXISTS → Generate OTP
                    ├─ Check for existing valid OTP
                    │  ├─ EXISTS → Reuse it
                    │  └─ NOT EXISTS → Generate new 6-digit OTP
                    │
                    ├─ Set expiry to NOW + 10 minutes
                    ├─ Save to PasswordResetOTP table
                    └─ Send email with OTP
                       ├─ SMTP connection to Gmail
                       ├─ Send email
                       └─ Log result
                           ↓
                    Email sent successfully?
                    ├─ YES → Store email in session
                    │        ↓
                    │        Redirect to /verify-otp/
                    │        ↓
                    │        Show "OTP sent to your email"
                    │
                    └─ NO → Show error "Could not send OTP"
                            ↓
                            Reload form

Database Queries:
- SELECT * FROM auth_user WHERE email = ?
- SELECT * FROM analyzer_passwordresetotp WHERE email = ? AND is_used = False
- INSERT INTO analyzer_passwordresetotp (email, otp, expires_at, ...)
- UPDATE analyzer_passwordresetotp SET is_used = True
```

---

## 4. OTP Verification Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  OTP VERIFICATION FLOW                      │
└─────────────────────────────────────────────────────────────┘

User visits /verify-otp/
        ↓
Is email in session?
        ├─ NO → Show error "Invalid request"
        │       ↓
        │       Redirect to /forgot-password/
        │
        └─ YES → Show OTP verification form
                 ↓
        User enters 6-digit OTP
                 ↓
        Submit form (POST /verify-otp/)
                 ↓
        Query database for OTP record
        ├─ NOT FOUND → Show error "Invalid OTP"
        │              ↓
        │              Reload form
        │
        └─ FOUND → Check if OTP is valid
                   ├─ Is OTP already used?
                   │  ├─ YES → Show error "OTP already used"
                   │  │        ↓
                   │  │        Reload form
                   │  │
                   │  └─ NO → Check if OTP expired
                   │          ├─ YES → Show error "OTP expired"
                   │          │        ↓
                   │          │        Reload form
                   │          │
                   │          └─ NO → OTP is valid!
                   │                  ├─ Mark OTP as used
                   │                  ├─ Set session flag: otp_verified = True
                   │                  ├─ Store email in session
                   │                  └─ Redirect to /reset-password/
                   │                     ↓
                   │                     ✅ SUCCESS

Database Queries:
- SELECT * FROM analyzer_passwordresetotp WHERE email = ? AND otp = ?
- UPDATE analyzer_passwordresetotp SET is_used = True WHERE id = ?
```

---

## 5. Reset Password Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 RESET PASSWORD FLOW                         │
└─────────────────────────────────────────────────────────────┘

User visits /reset-password/
        ↓
Is otp_verified flag set in session?
        ├─ NO → Show error "Invalid request"
        │       ↓
        │       Redirect to /forgot-password/
        │
        └─ YES → Show password reset form
                 ↓
        User enters new password (twice)
                 ↓
        Submit form (POST /reset-password/)
                 ↓
        Validate passwords
        ├─ Passwords match?
        ├─ Password strong enough?
        └─ Not same as old password?
                ↓
        Get user from database using email
                ↓
        Update user password
        ├─ Hash new password
        ├─ Save to database
        └─ Clear session flags
                ↓
        Show success message
                ↓
        Redirect to /login/
                ↓
        ✅ SUCCESS - User can now login with new password

Database Queries:
- SELECT * FROM auth_user WHERE email = ?
- UPDATE auth_user SET password = ? WHERE id = ?
```

---

## 6. Contact Form Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  CONTACT FORM FLOW                          │
└─────────────────────────────────────────────────────────────┘

User visits /contact/
        ↓
Show contact form
        ↓
User fills in:
├─ Name
├─ Email
├─ Subject (optional)
└─ Message
        ↓
Submit form (POST /contact/)
        ↓
Validate required fields
├─ Name present?
├─ Email present?
└─ Message present?
        ├─ MISSING → Return JSON error
        │            ↓
        │            Show error message to user
        │
        └─ ALL PRESENT → Save to database
                         ├─ INSERT INTO analyzer_contactmessage
                         ├─ Set is_read = False
                         └─ Log submission
                            ↓
                    Save successful?
                    ├─ YES → Return JSON success
                    │        ↓
                    │        Show success message
                    │        ↓
                    │        Clear form
                    │        ↓
                    │        ✅ SUCCESS
                    │
                    └─ NO → Return JSON error
                            ↓
                            Show error message

Database Queries:
- INSERT INTO analyzer_contactmessage (name, email, subject, message, is_read, created_at)
- SELECT * FROM analyzer_contactmessage (for admin review)
```

---

## 7. Email Sending Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  EMAIL SENDING FLOW                         │
└─────────────────────────────────────────────────────────────┘

Trigger: OTP requested
        ↓
Call send_otp_email(email, otp)
        ↓
Prepare email content
├─ Subject: "PaperAIzer - Password Reset OTP"
├─ Body: Include OTP and 10-minute expiry notice
└─ From: DEFAULT_FROM_EMAIL
        ↓
Connect to SMTP server
├─ Host: smtp.gmail.com
├─ Port: 587
├─ Use TLS: True
└─ Authenticate with EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
        ↓
Connection successful?
        ├─ NO → Log error
        │       ↓
        │       Return False
        │       ↓
        │       Show error to user
        │
        └─ YES → Send email
                 ├─ SMTP.sendmail()
                 └─ Wait for response
                    ↓
                    Email sent successfully?
                    ├─ YES → Log success
                    │        ↓
                    │        Return True
                    │        ↓
                    │        Show success message
                    │
                    └─ NO → Log error
                            ↓
                            Return False
                            ↓
                            Show error to user

SMTP Configuration:
- EMAIL_HOST = smtp.gmail.com
- EMAIL_PORT = 587
- EMAIL_USE_TLS = True
- EMAIL_HOST_USER = your-email@gmail.com
- EMAIL_HOST_PASSWORD = your-app-password
- EMAIL_TIMEOUT = 10 seconds
```

---

## 8. Complete Authentication Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│            COMPLETE AUTHENTICATION LIFECYCLE                │
└─────────────────────────────────────────────────────────────┘

NEW USER:
┌─────────────────────────────────────────────────────────────┐
│ 1. REGISTRATION                                             │
│    /register/ → Create account → Auto-login → /dashboard/  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. NORMAL LOGIN                                             │
│    /login/ → Enter credentials → /dashboard/               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. FORGOT PASSWORD (if needed)                              │
│    /forgot-password/ → Request OTP → Email sent            │
│    /verify-otp/ → Enter OTP → Verify                       │
│    /reset-password/ → Set new password → /login/           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. LOGIN WITH NEW PASSWORD                                  │
│    /login/ → Enter new credentials → /dashboard/           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. CONTACT FORM (optional)                                  │
│    /contact/ → Submit message → Saved to database          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. LOGOUT                                                   │
│    /logout/ → Session cleared → /login/                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE SCHEMA                          │
└─────────────────────────────────────────────────────────────┘

auth_user (Django built-in)
├─ id (PK)
├─ username (unique)
├─ email (unique)
├─ password (hashed)
├─ first_name
├─ last_name
├─ is_active
├─ is_staff
├─ is_superuser
├─ last_login
└─ date_joined

analyzer_passwordresetotp
├─ id (PK)
├─ email (FK to auth_user)
├─ otp (6 digits)
├─ expires_at (datetime)
├─ is_used (boolean)
└─ created_at (datetime)

analyzer_contactmessage
├─ id (PK)
├─ name (varchar)
├─ email (email)
├─ subject (varchar)
├─ message (text)
├─ is_read (boolean)
└─ created_at (datetime)

django_session
├─ session_key (PK)
├─ session_data (text)
└─ expire_date (datetime)
```

---

## 10. Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  ERROR HANDLING FLOW                        │
└─────────────────────────────────────────────────────────────┘

Error Occurs
        ↓
Catch Exception
        ↓
Log Error Details
├─ Error message
├─ Stack trace
├─ User email (if available)
└─ Timestamp
        ↓
Determine Error Type
        ├─ User Error (validation) → Show user-friendly message
        ├─ System Error (database) → Show generic error + log
        └─ Email Error (SMTP) → Retry or show error
        ↓
Return Response
├─ HTML: Render error template
├─ JSON: Return error JSON
└─ Redirect: Redirect to error page
        ↓
User sees error message
        ↓
User can retry or contact support

Common Errors:
- "Email already registered" → User error
- "Invalid OTP" → User error
- "OTP expired" → User error
- "Database connection failed" → System error
- "Email not sent" → Email error
- "SMTP authentication failed" → Email error
```

---

## Summary

All flows are:
- ✅ Secure (password hashing, CSRF protection)
- ✅ User-friendly (clear error messages)
- ✅ Logged (all actions logged for debugging)
- ✅ Validated (input validation at every step)
- ✅ Efficient (minimal database queries)

---

**Generated:** April 18, 2026
