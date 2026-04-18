# Requirements Document

## Introduction

The Paper Annotations feature allows authenticated users of the research paper analyzer to attach personal notes to any analyzed paper. Each note has a title and body text, supports pinning to the top, and displays creation and edit timestamps. Notes are private to the owning user and are rendered in a dedicated section on the paper's result page (`/result/<document_id>/`). Users can create multiple notes per paper, and can edit or delete any note they own.

---

## Glossary

- **Annotation**: A user-authored note attached to a specific analyzed paper (Document). Contains a title, body text, a pinned flag, and timestamps.
- **Annotation_System**: The Django backend subsystem responsible for creating, reading, updating, and deleting Annotations.
- **Result_Page**: The Django view rendered at `/result/<document_id>/` that displays the analysis of a single Document.
- **Authenticated_User**: A Django user who has successfully logged in and whose session is active.
- **Document**: An analyzed research paper stored in the `Document` model, identified by `document_id`.
- **Pin**: A boolean flag on an Annotation that causes it to appear before non-pinned Annotations in the display order.
- **Annotation_Form**: The UI form on the Result_Page used to create or edit an Annotation.

---

## Requirements

### Requirement 1: Create an Annotation

**User Story:** As an Authenticated_User, I want to add a note with a title and body to an analyzed paper, so that I can record my personal observations about the paper.

#### Acceptance Criteria

1. WHEN an Authenticated_User submits the Annotation_Form with a non-empty title and non-empty body for a valid Document, THE Annotation_System SHALL create and persist a new Annotation linked to that Document and that user.
2. WHEN an Annotation is created, THE Annotation_System SHALL record the creation timestamp as the current UTC datetime.
3. IF an Authenticated_User submits the Annotation_Form with an empty title, THEN THE Annotation_System SHALL reject the submission and return a validation error indicating the title is required.
4. IF an Authenticated_User submits the Annotation_Form with an empty body, THEN THE Annotation_System SHALL reject the submission and return a validation error indicating the body is required.
5. IF an unauthenticated user attempts to create an Annotation, THEN THE Annotation_System SHALL return an HTTP 401 response and redirect the user to the login page.
6. THE Annotation_System SHALL allow an Authenticated_User to create more than one Annotation for the same Document.
7. WHEN an Annotation is created successfully, THE Annotation_System SHALL return the updated Annotations list for the Document without requiring a full page reload.

---

### Requirement 2: Display Annotations on the Result Page

**User Story:** As an Authenticated_User, I want to see all my notes for a paper on its result page, so that I can review my observations in context.

#### Acceptance Criteria

1. WHEN an Authenticated_User visits the Result_Page for a Document, THE Result_Page SHALL display a dedicated Annotations section containing all Annotations owned by that user for that Document.
2. WHILE an Authenticated_User has at least one pinned Annotation for a Document, THE Result_Page SHALL display all pinned Annotations before all non-pinned Annotations in the Annotations section.
3. WHILE an Authenticated_User has no pinned Annotations for a Document, THE Result_Page SHALL display Annotations ordered by creation timestamp descending.
4. WHEN displaying an Annotation, THE Result_Page SHALL show the Annotation title, body text, creation timestamp, and last-edited timestamp.
5. WHEN an Annotation has never been edited, THE Result_Page SHALL display only the creation timestamp and omit the last-edited timestamp.
6. WHEN an Authenticated_User visits the Result_Page for a Document that has no Annotations, THE Result_Page SHALL display an empty-state message in the Annotations section indicating no notes have been added yet.
7. THE Result_Page SHALL display Annotations belonging only to the currently authenticated user and SHALL NOT display Annotations belonging to other users.

---

### Requirement 3: Edit an Annotation

**User Story:** As an Authenticated_User, I want to edit the title or body of an existing note, so that I can correct or update my observations.

#### Acceptance Criteria

1. WHEN an Authenticated_User submits an edit for an Annotation they own with a non-empty title and non-empty body, THE Annotation_System SHALL update the Annotation's title and body and record the current UTC datetime as the updated timestamp.
2. IF an Authenticated_User submits an edit with an empty title, THEN THE Annotation_System SHALL reject the update and return a validation error indicating the title is required.
3. IF an Authenticated_User submits an edit with an empty body, THEN THE Annotation_System SHALL reject the update and return a validation error indicating the body is required.
4. IF an Authenticated_User attempts to edit an Annotation they do not own, THEN THE Annotation_System SHALL return an HTTP 403 response.
5. IF an unauthenticated user attempts to edit an Annotation, THEN THE Annotation_System SHALL return an HTTP 401 response.
6. WHEN an Annotation is updated successfully, THE Annotation_System SHALL return the updated Annotation data without requiring a full page reload.

---

### Requirement 4: Delete an Annotation

**User Story:** As an Authenticated_User, I want to delete a note I no longer need, so that I can keep my annotations relevant.

#### Acceptance Criteria

1. WHEN an Authenticated_User requests deletion of an Annotation they own, THE Annotation_System SHALL permanently remove the Annotation from the database.
2. IF an Authenticated_User attempts to delete an Annotation they do not own, THEN THE Annotation_System SHALL return an HTTP 403 response and leave the Annotation unchanged.
3. IF an unauthenticated user attempts to delete an Annotation, THEN THE Annotation_System SHALL return an HTTP 401 response.
4. WHEN an Annotation is deleted successfully, THE Annotation_System SHALL return a success response and remove the Annotation from the displayed list without requiring a full page reload.

---

### Requirement 5: Pin and Unpin an Annotation

**User Story:** As an Authenticated_User, I want to pin important notes to the top of the Annotations section, so that I can quickly find my most relevant observations.

#### Acceptance Criteria

1. WHEN an Authenticated_User pins an Annotation they own, THE Annotation_System SHALL set the Annotation's pinned flag to true and persist the change.
2. WHEN an Authenticated_User unpins an Annotation they own, THE Annotation_System SHALL set the Annotation's pinned flag to false and persist the change.
3. IF an Authenticated_User attempts to pin or unpin an Annotation they do not own, THEN THE Annotation_System SHALL return an HTTP 403 response.
4. WHEN an Annotation's pinned flag is toggled successfully, THE Annotation_System SHALL return the updated pinned state without requiring a full page reload.
5. THE Annotation_System SHALL allow an Authenticated_User to pin more than one Annotation per Document simultaneously.
6. WHILE multiple Annotations are pinned for the same Document, THE Result_Page SHALL display pinned Annotations ordered by creation timestamp descending among themselves.

---

### Requirement 6: Annotation Privacy and Ownership

**User Story:** As an Authenticated_User, I want my notes to be private, so that other users cannot read or modify my personal observations.

#### Acceptance Criteria

1. THE Annotation_System SHALL associate every Annotation with exactly one Authenticated_User at creation time.
2. WHEN any read, update, delete, or pin operation is requested for an Annotation, THE Annotation_System SHALL verify that the requesting user is the owner of that Annotation before performing the operation.
3. IF a user requests an Annotation owned by a different user, THEN THE Annotation_System SHALL return an HTTP 403 response regardless of the operation type.
4. THE Annotation_System SHALL filter all Annotation queries by the authenticated user's identity so that database queries never return Annotations belonging to other users.

---

### Requirement 7: Annotation Timestamps

**User Story:** As an Authenticated_User, I want to see when each note was created and last edited, so that I can track the history of my observations.

#### Acceptance Criteria

1. THE Annotation_System SHALL record a `created_at` timestamp (UTC) automatically when an Annotation is first persisted.
2. THE Annotation_System SHALL record an `updated_at` timestamp (UTC) automatically whenever an Annotation's title, body, or pinned flag is modified.
3. WHEN an Annotation has the same `created_at` and `updated_at` value, THE Result_Page SHALL display only the creation timestamp.
4. WHEN an Annotation's `updated_at` differs from its `created_at`, THE Result_Page SHALL display both the creation timestamp and the last-edited timestamp.
5. THE Result_Page SHALL display timestamps in a human-readable format showing at minimum the date and time to the minute.

---

### Requirement 8: Annotation Data Integrity

**User Story:** As a system operator, I want Annotations to be safely stored and consistently validated, so that data quality is maintained.

#### Acceptance Criteria

1. THE Annotation_System SHALL enforce a maximum title length of 255 characters and reject submissions that exceed this limit with a descriptive validation error.
2. THE Annotation_System SHALL enforce a maximum body length of 10,000 characters and reject submissions that exceed this limit with a descriptive validation error.
3. WHEN the Document associated with an Annotation is deleted, THE Annotation_System SHALL cascade-delete all Annotations linked to that Document.
4. WHEN the User associated with an Annotation is deleted, THE Annotation_System SHALL cascade-delete all Annotations owned by that user.
5. THE Annotation_System SHALL use CSRF protection on all state-changing endpoints (create, update, delete, pin/unpin).
