# Requirements Document

## Introduction

The Bulk Upload feature extends the existing research paper analyzer to allow authenticated users to select and upload multiple PDF files in a single session. Files are queued and analyzed sequentially (one at a time) to respect Groq API rate limits. A real-time progress UI shows which file is being processed, how many remain, and the per-file outcome. Users may cancel the queue at any point. After the queue finishes — or is cancelled — a summary screen is shown. Partial failures (some files succeed, some fail) are handled gracefully; successful analyses are preserved regardless of other failures.

---

## Glossary

- **Bulk_Upload_Page**: The dedicated page at `/bulk-upload/` where users initiate a multi-file upload session.
- **Upload_Queue**: The ordered, in-memory list of PDF files selected by the user for sequential analysis in a single session.
- **Queue_Item**: A single PDF file entry within the Upload_Queue, carrying its filename, processing status, and result reference.
- **Bulk_Session**: A server-side record that tracks the state of one multi-file upload operation for a given user.
- **Analyzer**: The existing `analyze_document` processing pipeline (Groq LLM + ML fallback) that produces a `Document` and `AnalysisResult` record.
- **Progress_UI**: The client-side interface that displays real-time status of the Upload_Queue.
- **Summary_Screen**: The page or panel shown after the Upload_Queue finishes or is cancelled, listing per-file outcomes.
- **Partial_Failure**: A state where at least one Queue_Item fails analysis while at least one other succeeds.
- **Cancel_Request**: A user-initiated signal to stop processing remaining Queue_Items after the current one completes.

---

## Requirements

### Requirement 1: Multi-File Selection

**User Story:** As a researcher, I want to select multiple PDF files at once from my device, so that I can submit them all for analysis without repeating the upload process for each file.

#### Acceptance Criteria

1. THE Bulk_Upload_Page SHALL provide a file input control that accepts multiple PDF files simultaneously.
2. THE Bulk_Upload_Page SHALL restrict file selection to files with the `.pdf` extension.
3. WHEN a user selects files, THE Bulk_Upload_Page SHALL display the name and size of each selected file before submission.
4. WHEN a user selects files, THE Bulk_Upload_Page SHALL reject any selection that contains more than 10 PDF files and display an error message stating the 10-file limit.
5. WHEN a user selects a file larger than 45 MB, THE Bulk_Upload_Page SHALL mark that file as invalid and display a per-file error indicating the size limit.
6. WHEN a user selects a file that is 0 bytes, THE Bulk_Upload_Page SHALL mark that file as invalid and display a per-file error indicating the file is empty.
7. THE Bulk_Upload_Page SHALL allow the user to remove individual files from the selection before submission.
8. WHEN all selected files are invalid, THE Bulk_Upload_Page SHALL disable the submit button and display a summary error.

---

### Requirement 2: Queue Submission

**User Story:** As a researcher, I want to submit my selected files as a batch, so that the system can process them without requiring me to stay on the page for each individual upload.

#### Acceptance Criteria

1. WHEN a user submits a valid selection of 1–10 PDF files, THE Bulk_Upload_Page SHALL create an Upload_Queue containing one Queue_Item per valid file, ordered by the user's selection order.
2. WHEN the Upload_Queue is created, THE Analyzer SHALL begin processing the first Queue_Item immediately.
3. THE Analyzer SHALL process Queue_Items sequentially; THE Analyzer SHALL NOT begin processing the next Queue_Item until the current one has completed or failed.
4. WHEN a Queue_Item is submitted for analysis, THE Analyzer SHALL reuse the existing single-file analysis pipeline (PDF extraction → Groq LLM → ML fallback → save Document + AnalysisResult).
5. WHEN the Upload_Queue is submitted, THE Bulk_Upload_Page SHALL transition to the Progress_UI without a full page reload.

---

### Requirement 3: Real-Time Progress Display

**User Story:** As a researcher, I want to see which file is currently being analyzed and how many are left, so that I know the system is working and can estimate how long to wait.

#### Acceptance Criteria

1. WHILE the Upload_Queue is processing, THE Progress_UI SHALL display the filename and 1-based position of the Queue_Item currently being analyzed (e.g., "Processing file 2 of 5: paper.pdf").
2. WHILE the Upload_Queue is processing, THE Progress_UI SHALL display the count of completed Queue_Items and the count of remaining Queue_Items.
3. WHILE the Upload_Queue is processing, THE Progress_UI SHALL display a visual progress indicator (e.g., progress bar or spinner) that updates after each Queue_Item completes.
4. WHEN a Queue_Item completes successfully, THE Progress_UI SHALL immediately update to show that file's status as "Success" with a link to its result page (`/result/<document_id>/`).
5. WHEN a Queue_Item fails, THE Progress_UI SHALL immediately update to show that file's status as "Failed" with a brief human-readable error message.
6. THE Progress_UI SHALL update status without requiring a full page reload.

---

### Requirement 4: Cancel Queue

**User Story:** As a researcher, I want to cancel the remaining uploads mid-way, so that I can stop the process if I submitted the wrong files or need to leave.

#### Acceptance Criteria

1. WHILE the Upload_Queue is processing, THE Progress_UI SHALL display a "Cancel" button.
2. WHEN a user clicks "Cancel", THE Bulk_Upload_Page SHALL send a Cancel_Request to the server.
3. WHEN a Cancel_Request is received, THE Analyzer SHALL complete analysis of the Queue_Item currently in progress and SHALL NOT begin processing any subsequent Queue_Items.
4. WHEN a Cancel_Request is received, THE Progress_UI SHALL disable the "Cancel" button and display a "Cancelling…" status until the current Queue_Item finishes.
5. WHEN the current Queue_Item finishes after a Cancel_Request, THE Progress_UI SHALL transition to the Summary_Screen with the status "Cancelled".
6. WHEN the Upload_Queue is cancelled, THE Analyzer SHALL retain all Document and AnalysisResult records that were successfully created before cancellation.

---

### Requirement 5: Per-File Status Tracking

**User Story:** As a researcher, I want to see the individual outcome for each uploaded file, so that I know exactly which papers were analyzed successfully and which ones had problems.

#### Acceptance Criteria

1. THE Progress_UI SHALL display a status row for every Queue_Item in the Upload_Queue.
2. WHEN a Queue_Item has not yet been processed, THE Progress_UI SHALL display its status as "Pending".
3. WHEN a Queue_Item is being processed, THE Progress_UI SHALL display its status as "Processing".
4. WHEN a Queue_Item completes successfully, THE Progress_UI SHALL display its status as "Success" and provide a link to `/result/<document_id>/`.
5. WHEN a Queue_Item fails, THE Progress_UI SHALL display its status as "Failed" and show the reason (e.g., "PDF extraction failed", "Analysis service unavailable").
6. WHEN a Queue_Item is skipped due to cancellation, THE Progress_UI SHALL display its status as "Cancelled".
7. THE Progress_UI SHALL use visually distinct indicators (e.g., color or icon) for each status: Pending, Processing, Success, Failed, Cancelled.

---

### Requirement 6: Partial Failure Handling

**User Story:** As a researcher, I want the system to continue processing remaining files even if one fails, so that a single bad PDF does not block the rest of my batch.

#### Acceptance Criteria

1. WHEN a Queue_Item fails for any reason (extraction error, analysis error, or unexpected exception), THE Analyzer SHALL log the error and mark that Queue_Item as "Failed".
2. WHEN a Queue_Item is marked "Failed", THE Analyzer SHALL proceed to the next Queue_Item in the Upload_Queue without stopping the entire batch.
3. WHEN a Queue_Item fails, THE Analyzer SHALL NOT create a partial Document or AnalysisResult record for that Queue_Item.
4. WHEN at least one Queue_Item succeeds and at least one fails (Partial_Failure), THE Summary_Screen SHALL clearly distinguish successful and failed files.
5. IF all Queue_Items fail, THEN THE Summary_Screen SHALL display a message indicating that no analyses were saved and suggest the user check the files and try again.

---

### Requirement 7: Summary Screen

**User Story:** As a researcher, I want to see a summary of all results after the batch finishes, so that I can quickly navigate to the analyses I care about or understand what went wrong.

#### Acceptance Criteria

1. WHEN the Upload_Queue finishes processing all Queue_Items (or is cancelled), THE Progress_UI SHALL transition to the Summary_Screen.
2. THE Summary_Screen SHALL display the total count of successful analyses, failed analyses, and (if applicable) cancelled Queue_Items.
3. THE Summary_Screen SHALL list every Queue_Item with its final status and, for successful items, a link to `/result/<document_id>/`.
4. THE Summary_Screen SHALL provide a "Go to Library" button that navigates the user to `/library/`.
5. THE Summary_Screen SHALL provide a "Upload More" button that resets the Bulk_Upload_Page to its initial state for a new session.
6. WHERE at least one Queue_Item succeeded, THE Summary_Screen SHALL provide a "View All Results" link that navigates to `/library/` filtered to show only the documents created in that Bulk_Session.

---

### Requirement 8: Authentication and Authorization

**User Story:** As a system administrator, I want bulk upload to enforce the same authentication rules as single upload, so that unauthenticated users cannot submit files for analysis.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to the Bulk_Upload_Page, THE Bulk_Upload_Page SHALL redirect the user to the login page.
2. WHEN an unauthenticated user sends a POST request to the bulk analysis endpoint, THE Analyzer SHALL return an HTTP 401 response.
3. WHEN a Queue_Item is processed, THE Analyzer SHALL associate the resulting Document record with the authenticated user, identical to the single-upload behavior.
4. WHEN a user attempts to query the status of a Bulk_Session that belongs to a different user, THE Bulk_Upload_Page SHALL return an HTTP 403 response.

---

### Requirement 9: Input Validation and Error Handling

**User Story:** As a researcher, I want the system to validate my files before and during processing, so that I receive clear feedback on any issues rather than silent failures.

#### Acceptance Criteria

1. WHEN a user submits a file that does not have a `.pdf` extension, THE Analyzer SHALL reject that Queue_Item with the error "Only PDF files are allowed".
2. WHEN a user submits a file larger than 45 MB, THE Analyzer SHALL reject that Queue_Item with the error "File too large (max 45 MB)".
3. WHEN a user submits a file that is 0 bytes, THE Analyzer SHALL reject that Queue_Item with the error "Uploaded file is empty".
4. WHEN PDF text extraction produces fewer than 30 characters of content, THE Analyzer SHALL mark that Queue_Item as "Failed" with the error "Not enough content extracted from the document".
5. IF the Groq API is unavailable, THEN THE Analyzer SHALL fall back to the ML processor for that Queue_Item and SHALL NOT mark the Queue_Item as "Failed" solely due to Groq unavailability.
6. IF both the Groq API and the ML processor fail for a Queue_Item, THEN THE Analyzer SHALL mark that Queue_Item as "Failed" with the error "Analysis service unavailable".

---

### Requirement 10: Performance and Limits

**User Story:** As a system operator, I want the bulk upload feature to operate within safe resource bounds, so that it does not degrade performance for other users or exhaust API quotas.

#### Acceptance Criteria

1. THE Bulk_Upload_Page SHALL enforce a maximum of 10 PDF files per Upload_Queue submission.
2. THE Analyzer SHALL process Queue_Items sequentially with no concurrent analysis calls within a single Bulk_Session.
3. WHEN a single Queue_Item analysis exceeds 120 seconds, THE Analyzer SHALL mark that Queue_Item as "Failed" with the error "Analysis timed out" and proceed to the next Queue_Item.
4. THE Bulk_Upload_Page SHALL enforce a maximum total upload payload size of 200 MB per submission (sum of all file sizes).
5. WHEN the total payload exceeds 200 MB, THE Bulk_Upload_Page SHALL reject the submission before any files are processed and display an error stating the total size limit.
