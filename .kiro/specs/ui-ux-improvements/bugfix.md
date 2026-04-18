# Bugfix Requirements Document

## Introduction

The PaperAIzer Django app has several pages with broken, incomplete, or poor UX that need to be fixed and improved. Specifically:

1. **Login page** — currently regressed to a bare-bones unstyled form (the polished version was commented out and replaced with a minimal card). The login flow also requires a password, with no passwordless option despite the app already having OTP infrastructure.
2. **Register page** — functional but lacks a passwordless/OTP-based registration path.
3. **Dashboard** — works but lacks richer stats visualization and activity charts.
4. **User Profile** — is a stub; the view has a `# TODO: Update profile logic` comment and the template renders read-only info with no editing capability, no bio field, and no profile picture support.
5. **Contact Us page** — already has a good design but the form returns a raw JSON response instead of a proper user-facing success/error state, and there is no confirmation email sent to the submitter.

The fix uses the bug condition methodology: for each area, the bug condition C(X) identifies the broken/poor state, the property P defines the correct improved behavior, and ¬C(X) identifies what must be preserved.

---

## Bug Analysis

### Current Behavior (Defect)

**Login / Register — Passwordless**

1.1 WHEN a user visits the login page THEN the system renders a minimal unstyled card (the polished template was commented out and replaced with a stripped-down version lacking branding, icons, and visual hierarchy).

1.2 WHEN a user wants to log in without a password THEN the system provides no such option; the only path is email + password via `EmailLoginForm`, even though `PasswordResetOTP` / `create_and_send_otp` / `verify_otp` already exist in `otp_utils.py`.

1.3 WHEN a user wants to register without setting a password THEN the system forces them to enter and confirm a password via `CustomRegistrationForm`, with no OTP-based alternative.

1.4 WHEN the login form is submitted with invalid credentials THEN the system shows a plain red `<div class="error">` with no icon or styled alert component, inconsistent with the rest of the app.

**Dashboard**

1.5 WHEN a user views the dashboard THEN the system shows a placeholder text "Activity visualization will appear as you analyze more papers." in the "Efficiency Over Time" section instead of an actual chart or meaningful visualization.

1.6 WHEN a user has analyzed papers THEN the system does not show a plagiarism distribution breakdown (low / medium / high) in a visual format, only raw numbers in the Quick Stats sidebar.

1.7 WHEN a user views the dashboard header THEN the system shows `user.username` (which is the email address, since username is set to email on registration) instead of `user.first_name`, making the greeting look like "Hello, user@example.com!".

**User Profile**

1.8 WHEN a user visits the profile page THEN the system renders a read-only view with no way to edit name, email, bio, or upload a profile picture; the view's POST handler is a no-op (`pass`).

1.9 WHEN a user has no profile picture THEN the system shows only the first letter of `user.username` (which is an email address), so the avatar displays an email character rather than a name initial.

1.10 WHEN a user wants to add a bio or additional profile information THEN the system has no such field in the `User` model or any related profile model, and the template has no input for it.

**Contact Us**

1.11 WHEN a user submits the contact form successfully THEN the system returns a raw `JsonResponse` and the page relies entirely on client-side JS to display the toast; if JS fails or is slow, the user sees no feedback.

1.12 WHEN a user submits the contact form THEN the system does not send a confirmation email to the submitter acknowledging receipt of their message.

---

### Expected Behavior (Correct)

**Login / Register — Passwordless**

2.1 WHEN a user visits the login page THEN the system SHALL render a polished, branded login card (matching the commented-out design) with the PaperAIzer logo, gradient background, icon-prefixed inputs, and a "Forgot password?" link.

2.2 WHEN a user chooses "Sign in with Email OTP" on the login page THEN the system SHALL send a 6-digit OTP to the provided email using the existing `create_and_send_otp` function, store the email in session, and redirect to an OTP verification step that logs the user in upon successful verification — without requiring a password.

2.3 WHEN a user chooses "Register with Email OTP" on the register page THEN the system SHALL send an OTP to the provided email, verify it, and create the account (name + email only, no password required), setting `set_unusable_password()` on the new user.

2.4 WHEN the login or register form is submitted with invalid data THEN the system SHALL display a styled alert with an icon, consistent with the existing alert components used elsewhere in the app.

**Dashboard**

2.5 WHEN a user views the dashboard "Efficiency Over Time" section THEN the system SHALL render a bar or line chart (using Chart.js, which is already available via CDN) showing papers analyzed per month for the last 6 months.

2.6 WHEN a user has plagiarism check data THEN the system SHALL display a donut/pie chart showing the distribution of low (<25%), medium (25–50%), and high (>50%) similarity scores alongside the existing numeric stats.

2.7 WHEN a user views the dashboard header greeting THEN the system SHALL display `user.first_name` (falling back to the part of the email before `@`) instead of the raw `user.username` email address.

**User Profile**

2.8 WHEN a user visits the profile page THEN the system SHALL render an editable form allowing them to update their first name, last name, email, and bio; submitting the form SHALL save the changes and show a success message.

2.9 WHEN a user uploads a profile picture on the profile page THEN the system SHALL save the image to a `UserProfile` model (a `OneToOneField` to `User`) and display it as the avatar throughout the app.

2.10 WHEN a user has no profile picture THEN the system SHALL display the initial of `user.first_name` (not `user.username`) in the avatar placeholder.

2.11 WHEN a user updates their email on the profile page THEN the system SHALL also update `user.username` to keep them in sync (since username equals email in this app), and validate that the new email is not already taken.

**Contact Us**

2.12 WHEN a user submits the contact form successfully THEN the system SHALL send a confirmation email to the submitter's address acknowledging receipt, in addition to saving the `ContactMessage` to the database.

2.13 WHEN a user submits the contact form THEN the system SHALL continue to return a `JsonResponse` so the existing JS toast notification works, but SHALL also set a Django `messages` success flag as a fallback for non-JS environments.

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user logs in with email + password via the standard form THEN the system SHALL CONTINUE TO authenticate them using `EmailOrUsernameModelBackend` and redirect to the dashboard.

3.2 WHEN a user resets their password via the existing forgot-password OTP flow THEN the system SHALL CONTINUE TO work exactly as before (the `forgot_password` → `verify_otp` → `reset_password` URL chain must remain intact and functional).

3.3 WHEN a user registers with name, email, password1, and password2 via the standard form THEN the system SHALL CONTINUE TO create their account and log them in, redirecting to the dashboard.

3.4 WHEN a user views the dashboard THEN the system SHALL CONTINUE TO display total papers, average plagiarism, unique keywords, this-month count, recent activity list, and top keywords.

3.5 WHEN a user views the library, upload, compare, or result pages THEN the system SHALL CONTINUE TO function without any regression from profile or auth changes.

3.6 WHEN a user submits the contact form THEN the system SHALL CONTINUE TO save the `ContactMessage` record to the database with name, email, subject, message, and `is_read=False`.

3.7 WHEN a user views their profile THEN the system SHALL CONTINUE TO show their recent papers list and quick-action links to the library, compare, and upload pages.

3.8 WHEN the `UserProfile` model is introduced THEN the system SHALL CONTINUE TO work for existing users who do not yet have a `UserProfile` row, by creating one on-demand (get_or_create pattern).

---

## Bug Condition Pseudocode

```pascal
// ── Bug Condition 1: Login page regression ──────────────────────────────────
FUNCTION isBugCondition_LoginUI(request)
  INPUT: HTTP GET request to /login/
  OUTPUT: boolean
  RETURN template rendered is the stripped-down card (no branding, no icons)
END FUNCTION

// Property: Fix Checking
FOR ALL request WHERE isBugCondition_LoginUI(request) DO
  response ← login_view'(request)
  ASSERT response contains branded PaperAIzer header AND gradient background
         AND icon-prefixed inputs AND "Sign in with OTP" option
END FOR

// ── Bug Condition 2: No passwordless login path ──────────────────────────────
FUNCTION isBugCondition_NoOTPLogin(user_action)
  INPUT: user_action = "wants to log in without a password"
  OUTPUT: boolean
  RETURN no OTP login URL exists AND login form requires password field
END FUNCTION

// Property: Fix Checking
FOR ALL user_action WHERE isBugCondition_NoOTPLogin(user_action) DO
  result ← otp_login_flow'(email)
  ASSERT OTP sent via create_and_send_otp(email)
         AND session['otp_login_email'] set
         AND on valid OTP → user logged in without password
END FOR

// Preservation
FOR ALL request WHERE NOT isBugCondition_NoOTPLogin(request) DO
  ASSERT login_view(request) = login_view'(request)  // password login unchanged
END FOR

// ── Bug Condition 3: Profile page is a stub ──────────────────────────────────
FUNCTION isBugCondition_ProfileStub(request)
  INPUT: POST request to /profile/
  OUTPUT: boolean
  RETURN profile view POST handler does `pass` (no-op)
END FUNCTION

// Property: Fix Checking
FOR ALL request WHERE isBugCondition_ProfileStub(request) DO
  result ← profile'(request)
  ASSERT user.first_name, user.last_name, user.email updated in DB
         AND UserProfile.bio, UserProfile.avatar saved
         AND success message shown
END FOR

// Preservation
FOR ALL request WHERE NOT isBugCondition_ProfileStub(request) DO
  ASSERT profile(request) = profile'(request)  // GET still renders profile page
END FOR

// ── Bug Condition 4: Dashboard greeting shows email as name ──────────────────
FUNCTION isBugCondition_DashboardGreeting(user)
  INPUT: User object
  OUTPUT: boolean
  RETURN user.first_name = "" AND user.username = user.email
         AND dashboard renders user.username in greeting
END FUNCTION

// Property: Fix Checking
FOR ALL user WHERE isBugCondition_DashboardGreeting(user) DO
  response ← dashboard'(request)
  ASSERT greeting contains user.first_name OR email_prefix(user.email)
         AND NOT raw email address
END FOR

// ── Bug Condition 5: No confirmation email on contact submit ─────────────────
FUNCTION isBugCondition_NoContactEmail(contact_submission)
  INPUT: valid ContactMessage form POST
  OUTPUT: boolean
  RETURN no confirmation email sent to submitter
END FUNCTION

// Property: Fix Checking
FOR ALL submission WHERE isBugCondition_NoContactEmail(submission) DO
  result ← contact'(request)
  ASSERT ContactMessage saved in DB
         AND confirmation email sent to submission.email
         AND JsonResponse({'success': True}) returned
END FOR

// Preservation
FOR ALL submission WHERE NOT isBugCondition_NoContactEmail(submission) DO
  ASSERT contact(submission) saves ContactMessage  // DB save unchanged
END FOR
```
