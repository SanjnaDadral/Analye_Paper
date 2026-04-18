# Requirements Document

## Introduction

The Share Link feature allows authenticated users of the research paper analyzer to generate shareable URLs for their analysis results. Currently, the result page at `/result/<document_id>/` requires authentication, making it impossible to share findings with colleagues, supervisors, or reviewers who do not have accounts.

This feature introduces a `ShareLink` model that maps a unique token to an `AnalysisResult`. Share links can be public (anyone with the link can view) or password-protected. Owners can set an optional expiry date and revoke a link at any time. Visitors accessing a shared link see a read-only view of the analysis (title, summary, keywords, methodology, authors, year) but cannot use Q&A or export functionality, which remain login-only features. Every access to a valid shared link increments a view counter so owners can track engagement.

---

## Glossary

- **Share_Link_System**: The Django subsystem responsible for creating, validating, serving, and revoking share links.
- **ShareLink**: A database record that associates a unique token with an `AnalysisResult` and stores access-control metadata (password hash, expiry, active flag, view count).
- **Token**: A cryptographically random, URL-safe string (minimum 32 characters) that uniquely identifies a `ShareLink`.
- **Owner**: The authenticated `User` who owns the `Document` and `AnalysisResult` associated with a `ShareLink`.
- **Visitor**: Any HTTP client (authenticated or not) that accesses a shared link URL.
- **Public_Link**: A `ShareLink` with no password requirement.
- **Password_Protected_Link**: A `ShareLink` that requires a correct password before the analysis is displayed.
- **Expiry_Date**: An optional UTC datetime after which a `ShareLink` is no longer valid.
- **View_Count**: An integer stored on `ShareLink` that is incremented each time a Visitor successfully views the shared analysis.
- **Read_Only_View**: The shared analysis page that displays title, summary, keywords, methodology, authors, and publication year, but omits Q&A and export controls.
- **Revocation**: The act of an Owner setting a `ShareLink` to inactive, permanently preventing further access via that token.
- **Share_Management_Page**: An authenticated page listing all `ShareLink` records for a given `Document`, allowing the Owner to create, inspect, and revoke links.

---

## Requirements

### Requirement 1: Share Link Creation

**User Story:** As an Owner, I want to generate a shareable link for one of my analysis results, so that I can send it to colleagues who do not have an account.

#### Acceptance Criteria

1. WHEN an Owner submits a valid create-share-link request for a `Document` they own, THE `Share_Link_System` SHALL create a `ShareLink` record with a unique `Token` and return the full shareable URL.
2. THE `Share_Link_System` SHALL generate each `Token` using a cryptographically secure random source with a minimum length of 32 URL-safe characters.
3. WHEN two create-share-link requests are made for the same `Document`, THE `Share_Link_System` SHALL produce two `ShareLink` records with distinct `Token` values.
4. WHEN an Owner submits a create-share-link request for a `Document` they do not own, THE `Share_Link_System` SHALL return an HTTP 403 response and SHALL NOT create a `ShareLink` record.
5. WHEN an unauthenticated client submits a create-share-link request, THE `Share_Link_System` SHALL return an HTTP 401 response and SHALL NOT create a `ShareLink` record.
6. THE `Share_Link_System` SHALL set the `ShareLink` active flag to `True` upon creation.

---

### Requirement 2: Public and Password-Protected Links

**User Story:** As an Owner, I want to choose whether my share link is open to anyone or requires a password, so that I can control who can view my analysis.

#### Acceptance Criteria

1. WHEN an Owner creates a `ShareLink` without providing a password, THE `Share_Link_System` SHALL create a `Public_Link` that grants access to any Visitor who presents the correct `Token`.
2. WHEN an Owner creates a `ShareLink` with a non-empty password, THE `Share_Link_System` SHALL create a `Password_Protected_Link` and SHALL store a bcrypt hash of the password — never the plaintext password.
3. WHEN a Visitor accesses a `Password_Protected_Link` without submitting a password, THE `Share_Link_System` SHALL display a password prompt and SHALL NOT render the analysis content.
4. WHEN a Visitor submits an incorrect password for a `Password_Protected_Link`, THE `Share_Link_System` SHALL display an error message and SHALL NOT render the analysis content.
5. WHEN a Visitor submits the correct password for a `Password_Protected_Link`, THE `Share_Link_System` SHALL render the `Read_Only_View` and SHALL increment the `View_Count`.
6. THE `Share_Link_System` SHALL accept passwords between 4 and 128 characters in length.

---

### Requirement 3: Expiry Date

**User Story:** As an Owner, I want to set an optional expiry date on a share link, so that access automatically ends after a deadline.

#### Acceptance Criteria

1. WHEN an Owner creates a `ShareLink` with a future `Expiry_Date`, THE `Share_Link_System` SHALL store that date and enforce it on every subsequent access attempt.
2. WHEN a Visitor accesses a `ShareLink` whose `Expiry_Date` is in the past, THE `Share_Link_System` SHALL return an HTTP 410 (Gone) response and SHALL NOT render the analysis content.
3. WHEN an Owner creates a `ShareLink` without specifying an `Expiry_Date`, THE `Share_Link_System` SHALL create the link with no expiry, remaining valid until explicitly revoked.
4. WHEN an Owner provides an `Expiry_Date` that is in the past at creation time, THE `Share_Link_System` SHALL reject the request with a validation error and SHALL NOT create the `ShareLink`.
5. THE `Share_Link_System` SHALL evaluate expiry using UTC timestamps to ensure consistent behaviour across time zones.

---

### Requirement 4: Link Revocation

**User Story:** As an Owner, I want to revoke a share link at any time, so that I can immediately stop others from accessing my analysis.

#### Acceptance Criteria

1. WHEN an Owner submits a revoke request for a `ShareLink` they own, THE `Share_Link_System` SHALL set the `ShareLink` active flag to `False` and SHALL return an HTTP 200 response.
2. WHEN a Visitor accesses a revoked `ShareLink` (active flag is `False`), THE `Share_Link_System` SHALL return an HTTP 410 (Gone) response and SHALL NOT render the analysis content.
3. WHEN an Owner submits a revoke request for a `ShareLink` they do not own, THE `Share_Link_System` SHALL return an HTTP 403 response and SHALL NOT modify the `ShareLink`.
4. THE `Share_Link_System` SHALL treat revocation as permanent; a revoked `ShareLink` SHALL NOT be reactivated through any user-facing action.
5. WHEN an Owner deletes the parent `Document`, THE `Share_Link_System` SHALL cascade-delete all associated `ShareLink` records.

---

### Requirement 5: Read-Only Shared View

**User Story:** As a Visitor, I want to view the analysis result via a share link, so that I can read the findings without needing an account.

#### Acceptance Criteria

1. WHEN a Visitor accesses a valid, active, non-expired `ShareLink`, THE `Share_Link_System` SHALL render the `Read_Only_View` containing the paper title, summary, keywords, methodology, authors, and publication year.
2. THE `Read_Only_View` SHALL NOT include Q&A controls, export buttons, feedback forms, or any other feature that requires authentication.
3. THE `Read_Only_View` SHALL display a visible notice informing the Visitor that the view is read-only and that full features require an account.
4. WHEN a Visitor accesses a `ShareLink` with an invalid or non-existent `Token`, THE `Share_Link_System` SHALL return an HTTP 404 response.
5. THE `Read_Only_View` SHALL be accessible without the Visitor being authenticated.
6. THE `Read_Only_View` SHALL NOT expose the `document_id` or any internal database identifier in the rendered HTML or HTTP response.

---

### Requirement 6: View Count Tracking

**User Story:** As an Owner, I want to see how many times my share link has been viewed, so that I can gauge interest in my analysis.

#### Acceptance Criteria

1. WHEN a Visitor successfully views the `Read_Only_View` for a `ShareLink`, THE `Share_Link_System` SHALL increment the `View_Count` for that `ShareLink` by exactly 1.
2. THE `Share_Link_System` SHALL NOT increment the `View_Count` when a Visitor is denied access due to an incorrect password, expired link, or revoked link.
3. THE `Share_Link_System` SHALL NOT increment the `View_Count` when the Owner themselves views the shared link while authenticated.
4. THE `Share_Link_System` SHALL display the current `View_Count` to the Owner on the `Share_Management_Page`.
5. WHEN the `View_Count` is incremented concurrently by multiple Visitors, THE `Share_Link_System` SHALL use a database-level atomic increment to prevent lost updates.

---

### Requirement 7: Share Management Page

**User Story:** As an Owner, I want a dedicated page to manage all share links for a document, so that I can see their status, view counts, and revoke them when needed.

#### Acceptance Criteria

1. WHEN an Owner navigates to the `Share_Management_Page` for a `Document` they own, THE `Share_Link_System` SHALL display all `ShareLink` records for that `Document`, including token preview, creation date, expiry date, active status, and `View_Count`.
2. WHEN an Owner navigates to the `Share_Management_Page` for a `Document` they do not own, THE `Share_Link_System` SHALL return an HTTP 403 response.
3. THE `Share_Management_Page` SHALL provide a form to create a new `ShareLink` with optional password and optional `Expiry_Date` fields.
4. THE `Share_Management_Page` SHALL provide a revoke action for each active `ShareLink`.
5. WHEN an Owner copies a share link from the `Share_Management_Page`, THE `Share_Link_System` SHALL provide the full absolute URL including scheme and host.
6. THE `Share_Management_Page` SHALL indicate whether each `ShareLink` is a `Public_Link` or `Password_Protected_Link` without revealing the stored password hash.

---

### Requirement 8: Token Uniqueness and Integrity

**User Story:** As a system operator, I want share link tokens to be unique and tamper-resistant, so that Visitors cannot guess or forge valid links.

#### Acceptance Criteria

1. THE `Share_Link_System` SHALL enforce a unique database constraint on the `Token` field of the `ShareLink` model.
2. WHEN a token collision is detected during creation, THE `Share_Link_System` SHALL regenerate a new `Token` and retry, up to 5 attempts, before returning an HTTP 500 error.
3. THE `Share_Link_System` SHALL use `secrets.token_urlsafe(32)` or an equivalent source providing at least 256 bits of entropy for token generation.
4. FOR ALL generated tokens, the `Share_Link_System` SHALL produce tokens that contain only URL-safe characters (alphanumeric, `-`, `_`) requiring no percent-encoding in URLs.

---

### Requirement 9: URL Structure

**User Story:** As a system operator, I want share links to follow a clean, predictable URL pattern, so that they are easy to share and do not expose internal identifiers.

#### Acceptance Criteria

1. THE `Share_Link_System` SHALL serve shared analysis views at the URL pattern `/share/<token>/`.
2. THE `Share_Link_System` SHALL serve the `Share_Management_Page` at the URL pattern `/share/manage/<document_id>/`.
3. THE `Share_Link_System` SHALL serve the create-share-link endpoint at `POST /share/create/<document_id>/`.
4. THE `Share_Link_System` SHALL serve the revoke endpoint at `POST /share/revoke/<token>/`.
5. WHEN a `Token` contains characters outside the URL-safe set, THE `Share_Link_System` SHALL reject the request with an HTTP 400 response without querying the database.
