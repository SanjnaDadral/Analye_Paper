# Requirements Document

## Introduction

The Citation Generation feature enables users of the Django research paper analyzer to automatically generate properly formatted citations for any analyzed paper. Since the app already extracts metadata (title, authors, publication year, abstract, etc.) into `AnalysisResult`, citations can be derived without re-processing. Users can generate citations in APA, MLA, and Chicago formats directly from the result/detail page, copy them to the clipboard, and optionally export them.

## Glossary

- **Citation_Generator**: The backend component responsible for formatting citation strings from extracted metadata.
- **Citation_Format**: One of the supported citation styles: APA, MLA, or Chicago.
- **AnalysisResult**: The Django model storing extracted metadata for an analyzed document (authors, title, publication year, abstract, etc.).
- **Document**: The Django model representing an uploaded PDF or URL submitted by a user.
- **Result_Page**: The detail view rendered at `/result/<document_id>/` showing analysis output for a single document.
- **Clipboard**: The operating system clipboard used to store text for pasting.
- **Citation_Export**: A downloadable file containing one or more formatted citations.
- **Metadata**: The structured data extracted from a paper: title, authors, publication year, URL/DOI, and source type.

---

## Requirements

### Requirement 1: Generate Citations from Extracted Metadata

**User Story:** As a researcher, I want citations to be automatically generated from the already-extracted paper metadata, so that I do not have to manually format references.

#### Acceptance Criteria

1. WHEN a user views the Result_Page for a document that has an associated AnalysisResult, THE Citation_Generator SHALL produce a formatted citation string for each supported Citation_Format (APA, MLA, Chicago).
2. WHEN the AnalysisResult contains an empty authors list, THE Citation_Generator SHALL substitute "Unknown Author" in the citation string.
3. WHEN the AnalysisResult contains an empty publication_year field, THE Citation_Generator SHALL substitute "n.d." (no date) in the citation string.
4. WHEN the AnalysisResult contains an empty title (via the associated Document), THE Citation_Generator SHALL substitute "Untitled" in the citation string.
5. THE Citation_Generator SHALL generate all three Citation_Format variants from a single AnalysisResult without requiring additional user input or re-analysis.

---

### Requirement 2: APA Citation Format

**User Story:** As a researcher, I want APA-formatted citations, so that I can use them in academic papers that require APA style.

#### Acceptance Criteria

1. WHEN generating an APA citation, THE Citation_Generator SHALL format the citation as: `LastName, F. M., & LastName, F. M. (Year). Title of paper. *Source*. URL`
2. WHEN an AnalysisResult has multiple authors, THE Citation_Generator SHALL list all authors in "LastName, Initials" format separated by ", & " for the final author.
3. WHEN an AnalysisResult has a single author, THE Citation_Generator SHALL omit the ampersand separator.
4. WHEN the Document input_type is "url", THE Citation_Generator SHALL append the source URL to the APA citation.
5. WHEN the Document input_type is "pdf", THE Citation_Generator SHALL omit the URL from the APA citation.

---

### Requirement 3: MLA Citation Format

**User Story:** As a researcher, I want MLA-formatted citations, so that I can use them in humanities papers that require MLA style.

#### Acceptance Criteria

1. WHEN generating an MLA citation, THE Citation_Generator SHALL format the citation as: `LastName, FirstName, and FirstName LastName. "Title of Paper." *Source*, Year.`
2. WHEN an AnalysisResult has more than two authors, THE Citation_Generator SHALL list the first author followed by "et al." in the MLA citation.
3. WHEN an AnalysisResult has exactly two authors, THE Citation_Generator SHALL list both authors joined by "and".
4. WHEN the Document input_type is "url", THE Citation_Generator SHALL append the URL and access date to the MLA citation.

---

### Requirement 4: Chicago Citation Format

**User Story:** As a researcher, I want Chicago-formatted citations, so that I can use them in history or social science papers that require Chicago style.

#### Acceptance Criteria

1. WHEN generating a Chicago citation, THE Citation_Generator SHALL format the citation as: `LastName, FirstName. "Title of Paper." *Source* (Year). URL`
2. WHEN an AnalysisResult has multiple authors, THE Citation_Generator SHALL list all authors in "FirstName LastName" format separated by commas, with the first author in "LastName, FirstName" format.
3. WHEN the Document input_type is "url", THE Citation_Generator SHALL append the URL to the Chicago citation.

---

### Requirement 5: Display Citations on the Result Page

**User Story:** As a researcher, I want to see all citation formats displayed on the result page, so that I can quickly pick the one I need.

#### Acceptance Criteria

1. WHEN a user loads the Result_Page for a document with an AnalysisResult, THE Result_Page SHALL display a citations section containing all three Citation_Format variants.
2. THE Result_Page SHALL render each citation in a visually distinct, read-only text area or code block labeled with its Citation_Format name.
3. WHEN a document has no associated AnalysisResult, THE Result_Page SHALL hide the citations section entirely.
4. THE Result_Page SHALL display the citations section without requiring a page reload or additional user action.

---

### Requirement 6: Copy Citation to Clipboard

**User Story:** As a researcher, I want to copy a citation to my clipboard with one click, so that I can paste it directly into my document.

#### Acceptance Criteria

1. WHEN a user clicks the copy button adjacent to a citation, THE Result_Page SHALL copy the full citation text to the Clipboard.
2. WHEN the copy operation succeeds, THE Result_Page SHALL display a visual confirmation (e.g., button text changes to "Copied!") for at least 2 seconds.
3. IF the browser Clipboard API is unavailable, THEN THE Result_Page SHALL display an error message instructing the user to copy the text manually.
4. THE Result_Page SHALL provide a separate copy button for each Citation_Format variant.

---

### Requirement 7: Export Citations

**User Story:** As a researcher, I want to export citations as a downloadable file, so that I can save them for later use or share them.

#### Acceptance Criteria

1. WHEN a user requests a citation export for a document, THE Citation_Generator SHALL return a plain-text (.txt) file containing all three Citation_Format variants.
2. WHEN generating the export file, THE Citation_Generator SHALL label each citation with its Citation_Format name as a section header.
3. THE Citation_Generator SHALL make the export available via a dedicated URL endpoint at `/citation/<document_id>/export/`.
4. WHEN the requested document does not belong to the authenticated user, THE Citation_Generator SHALL return an HTTP 403 response.
5. WHEN the requested document has no associated AnalysisResult, THE Citation_Generator SHALL return an HTTP 404 response.

---

### Requirement 8: Citation Generation API Endpoint

**User Story:** As a developer, I want a JSON API endpoint for citation generation, so that the frontend can fetch citations dynamically without a full page reload.

#### Acceptance Criteria

1. WHEN a GET request is made to `/citation/<document_id>/`, THE Citation_Generator SHALL return a JSON response containing all three Citation_Format variants keyed by format name.
2. WHEN the requesting user is not authenticated, THE Citation_Generator SHALL return an HTTP 401 response.
3. WHEN the requested document does not belong to the authenticated user, THE Citation_Generator SHALL return an HTTP 403 response.
4. WHEN the requested document has no associated AnalysisResult, THE Citation_Generator SHALL return an HTTP 404 response with a descriptive error message.
5. THE Citation_Generator SHALL respond to valid requests within 500ms, as citation generation is a pure in-memory formatting operation.

---

### Requirement 9: Author Name Parsing

**User Story:** As a researcher, I want author names to be correctly parsed and formatted per citation style, so that citations are accurate and style-compliant.

#### Acceptance Criteria

1. WHEN an author name in AnalysisResult contains both a first and last name separated by a space, THE Citation_Generator SHALL correctly split and reformat the name per the target Citation_Format.
2. WHEN an author name contains only a single token (no space), THE Citation_Generator SHALL treat the entire token as the last name.
3. THE Citation_Generator SHALL handle author names with middle names or initials by using only the first and last name tokens for citation formatting.
4. FOR ALL valid author name strings, parsing then formatting then re-parsing SHALL produce an equivalent structured representation (round-trip property).
