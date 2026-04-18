# Requirements Document

## Introduction

The Analysis History feature adds versioning to the research paper analyzer. Currently, re-analyzing a document overwrites the single `AnalysisResult` record tied to that document via a one-to-one relationship. This feature preserves every analysis run as a numbered version (v1, v2, v3, …), lets users browse the full version history, compare any two versions side-by-side, and restore any past version as the active ("current") result — all while keeping the existing `document.analysis` accessor working so no other part of the app breaks.

---

## Glossary

- **Document**: An existing Django model representing an uploaded research paper or URL-scraped article owned by a user.
- **AnalysisResult**: The existing Django model that stores the AI-generated analysis fields for a Document (summary, keywords, methodology, etc.).
- **AnalysisVersion**: A new model that stores a snapshot of one analysis run for a Document, identified by a sequential version number.
- **Current Version**: The AnalysisVersion designated as the active result for a Document. The existing `document.analysis` accessor must always reflect this version's data.
- **Version History**: The ordered list of all AnalysisVersions for a Document, from v1 (oldest) to the latest.
- **Version Comparison**: A side-by-side diff view of two AnalysisVersions for the same Document.
- **Re-analysis**: The act of running the AI analysis pipeline on a Document that already has at least one AnalysisVersion.
- **Restore**: Promoting a non-current AnalysisVersion to become the Current Version.
- **Version_Manager**: The system component responsible for creating, retrieving, comparing, and restoring AnalysisVersions.
- **History_View**: The UI page that lists all AnalysisVersions for a Document.
- **Comparison_View**: The UI page that renders a side-by-side diff of two AnalysisVersions.
- **User**: An authenticated Django user who owns one or more Documents.

---

## Requirements

### Requirement 1: Version Creation on Re-analysis

**User Story:** As a researcher, I want each new analysis run to be saved as a new version, so that I never lose a previous result when I re-analyze a paper.

#### Acceptance Criteria

1. WHEN a Document is analyzed for the first time, THE Version_Manager SHALL create an AnalysisVersion with version_number = 1 and mark it as the Current Version.
2. WHEN a Document that already has at least one AnalysisVersion is re-analyzed, THE Version_Manager SHALL create a new AnalysisVersion with version_number equal to the previous highest version_number plus 1.
3. WHEN a new AnalysisVersion is created by re-analysis, THE Version_Manager SHALL automatically mark it as the Current Version and unmark the previously current version.
4. THE Version_Manager SHALL store the timestamp of creation for every AnalysisVersion.
5. THE Version_Manager SHALL store the version_number, all analysis fields (summary, abstract, keywords, methodology, technologies, goal, impact, publication_year, authors, word_count, unique_words, character_count, extracted_links, references, extras), and the model_used identifier in every AnalysisVersion.
6. IF the analysis pipeline fails after a Document already has existing versions, THEN THE Version_Manager SHALL leave all existing AnalysisVersions and the Current Version designation unchanged.

---

### Requirement 2: Backward Compatibility with Existing AnalysisResult

**User Story:** As a developer, I want the existing `document.analysis` accessor to keep working without changes, so that no existing views, exports, or API calls break.

#### Acceptance Criteria

1. THE Version_Manager SHALL keep the existing `AnalysisResult` record for a Document synchronized with the data of the Current Version at all times.
2. WHEN the Current Version changes (via re-analysis or restore), THE Version_Manager SHALL update the existing `AnalysisResult` record to match the new Current Version's data within the same database transaction.
3. THE System SHALL preserve the `document.analysis` one-to-one relationship so that all existing code accessing `document.analysis` continues to return the Current Version's data without modification.
4. IF no AnalysisVersion exists for a Document, THEN THE System SHALL return `None` for `document.analysis`, preserving existing null-handling behavior.

---

### Requirement 3: Version History Listing

**User Story:** As a researcher, I want to see a list of all analysis versions for a paper, so that I can understand how the analysis has evolved over time.

#### Acceptance Criteria

1. WHEN a User navigates to the history page for a Document they own, THE History_View SHALL display all AnalysisVersions for that Document ordered by version_number descending (newest first).
2. THE History_View SHALL display the version_number, creation timestamp, model_used, and Current Version indicator for each AnalysisVersion in the list.
3. THE History_View SHALL provide a link to view the full detail of each individual AnalysisVersion.
4. THE History_View SHALL provide a link to restore each non-current AnalysisVersion as the Current Version.
5. THE History_View SHALL provide a link to initiate a comparison between any two AnalysisVersions.
6. IF a Document has only one AnalysisVersion, THEN THE History_View SHALL display that version without restore or comparison controls.
7. WHEN a User requests the history page for a Document they do not own, THE History_View SHALL return an HTTP 403 response.

---

### Requirement 4: Individual Version Detail View

**User Story:** As a researcher, I want to view the full analysis output of any past version, so that I can review what the AI produced at that point in time.

#### Acceptance Criteria

1. WHEN a User navigates to the detail page for a specific AnalysisVersion of a Document they own, THE System SHALL render all stored analysis fields for that version.
2. THE System SHALL display the version_number, creation timestamp, model_used, and whether the version is the Current Version on the detail page.
3. THE System SHALL provide a navigation link back to the Version History page for the same Document.
4. THE System SHALL provide a restore action on the detail page for any non-current AnalysisVersion.
5. WHEN a User requests the detail page for an AnalysisVersion belonging to a Document they do not own, THE System SHALL return an HTTP 403 response.

---

### Requirement 5: Version Comparison (Diff View)

**User Story:** As a researcher, I want to compare two versions of an analysis side-by-side, so that I can see exactly what changed between runs.

#### Acceptance Criteria

1. WHEN a User requests a comparison between two AnalysisVersions of the same Document they own, THE Comparison_View SHALL render both versions side-by-side.
2. THE Comparison_View SHALL highlight fields that differ between the two selected versions.
3. THE Comparison_View SHALL display the version_number and creation timestamp for each version in the comparison header.
4. THE Comparison_View SHALL compare the following fields: summary, abstract, goal, impact, keywords, methodology, technologies, authors, publication_year, and model_used.
5. IF the two selected version numbers are identical, THEN THE Comparison_View SHALL return an HTTP 400 response with a descriptive error message.
6. WHEN a User requests a comparison for AnalysisVersions belonging to a Document they do not own, THE Comparison_View SHALL return an HTTP 403 response.
7. IF either requested version_number does not exist for the given Document, THEN THE Comparison_View SHALL return an HTTP 404 response.

---

### Requirement 6: Restore a Previous Version

**User Story:** As a researcher, I want to restore a previous version as the current result, so that I can revert to a better analysis if a newer run produced worse output.

#### Acceptance Criteria

1. WHEN a User submits a restore request for a non-current AnalysisVersion of a Document they own, THE Version_Manager SHALL mark that AnalysisVersion as the Current Version.
2. WHEN a restore is performed, THE Version_Manager SHALL unmark the previously current AnalysisVersion.
3. WHEN a restore is performed, THE Version_Manager SHALL update the existing `AnalysisResult` record to match the restored version's data within the same database transaction as steps 1 and 2.
4. WHEN a restore completes successfully, THE System SHALL redirect the User to the result detail page for the Document, which now reflects the restored version.
5. IF a User submits a restore request for the version that is already the Current Version, THEN THE System SHALL return an HTTP 400 response with a descriptive error message.
6. WHEN a User submits a restore request for an AnalysisVersion belonging to a Document they do not own, THE System SHALL return an HTTP 403 response.
7. THE Version_Manager SHALL perform the Current Version update and AnalysisResult synchronization atomically so that a partial failure leaves the database in a consistent state.

---

### Requirement 7: Current Version Indicator

**User Story:** As a researcher, I want to clearly see which version is currently active, so that I always know what result is being shown in the main result view.

#### Acceptance Criteria

1. THE System SHALL store a boolean `is_current` flag on each AnalysisVersion.
2. THE System SHALL enforce that exactly one AnalysisVersion per Document has `is_current = True` at any time when at least one version exists.
3. THE History_View SHALL visually distinguish the Current Version from all other versions in the list (e.g., a "Current" badge).
4. THE Version detail page SHALL display a clear "Current Version" indicator when the viewed version is the Current Version.
5. IF a Document has no AnalysisVersions, THEN THE System SHALL not enforce the single-current constraint.

---

### Requirement 8: Access Control

**User Story:** As a user, I want my analysis history to be private, so that other users cannot view or modify my paper versions.

#### Acceptance Criteria

1. THE System SHALL require authentication for all analysis history, version detail, comparison, and restore endpoints.
2. WHEN an unauthenticated User accesses any history or versioning endpoint, THE System SHALL redirect the User to the login page.
3. THE System SHALL verify that the Document referenced in any versioning request belongs to the requesting User before performing any read or write operation.
4. IF the Document does not belong to the requesting User, THEN THE System SHALL return an HTTP 403 response without revealing whether the Document exists.

---

### Requirement 9: Version Count and Storage Limits

**User Story:** As a system operator, I want to cap the number of versions stored per document, so that storage does not grow unboundedly.

#### Acceptance Criteria

1. THE Version_Manager SHALL enforce a configurable maximum number of AnalysisVersions per Document, defaulting to 20.
2. WHEN creating a new AnalysisVersion would exceed the maximum, THE Version_Manager SHALL delete the oldest non-current AnalysisVersion before saving the new one.
3. WHERE the maximum version limit is configured to 0 or a negative value, THE Version_Manager SHALL treat the limit as unlimited and retain all versions.
4. THE Version_Manager SHALL never delete the Current Version during automatic pruning.

---

### Requirement 10: Data Integrity and Round-Trip Consistency

**User Story:** As a developer, I want the version data to be consistent and recoverable, so that restoring a version always produces the same result as the original analysis.

#### Acceptance Criteria

1. THE Version_Manager SHALL store all analysis fields in the AnalysisVersion record as a complete snapshot, independent of any other version.
2. FOR ALL AnalysisVersions, promoting a version to Current and then reading `document.analysis` SHALL return data equal to the snapshot stored in that AnalysisVersion (round-trip property).
3. THE Version_Manager SHALL store JSON fields (keywords, methodology, technologies, authors, extracted_links, references, extras) as structured JSON, not as serialized strings.
4. IF a Document is deleted, THEN THE System SHALL cascade-delete all associated AnalysisVersions.
