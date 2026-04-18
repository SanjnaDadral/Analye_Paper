# Requirements Document

## Introduction

The Library Search feature adds full-text search and filtering capabilities to the research paper analyzer's library page at `/library/`. Currently the library displays all of a user's `Document` records in a flat, unfiltered list. This feature introduces a prominent search bar, multi-field text matching across `Document` and `AnalysisResult` fields, result highlighting, filter controls (date range, methodology, technology, keyword), and sort controls (relevance, date, title). Search is implemented using Django ORM `Q` objects with `icontains` lookups — no external search engine is required.

---

## Glossary

- **Document**: The existing `analyzer.Document` model representing a single analyzed research paper owned by a user. Fields relevant to search: `title`, `content`, `created_at`.
- **AnalysisResult**: The existing `analyzer.AnalysisResult` model with a one-to-one relation to `Document`. Fields relevant to search: `summary`, `abstract`, `keywords` (JSONField list), `methodology` (JSONField list), `technologies` (JSONField list), `authors` (JSONField list).
- **Search_Engine**: The Django view-layer subsystem responsible for accepting a query, building `Q` objects, executing the ORM query, and returning ranked results.
- **Library_View**: The Django view that renders the `/library/` page.
- **Search_Query**: A non-empty string submitted by the user via the search bar.
- **Filter_Set**: The optional combination of date range, methodology type, technology, and keyword filters applied alongside a Search_Query or independently.
- **Relevance_Score**: A numeric value computed per result indicating how many searchable fields contain the Search_Query term, used for relevance-based sorting.
- **Highlight**: An HTML `<mark>` tag wrapping the matched substring within a displayed text snippet to visually indicate where the Search_Query appears.
- **Snippet**: A short excerpt (up to 200 characters) extracted from a searchable text field, centered around the first match of the Search_Query.

---

## Requirements

### Requirement 1: Search Bar Placement and Submission

**User Story:** As a researcher, I want a prominent search bar on the library page, so that I can immediately start searching without navigating away.

#### Acceptance Criteria

1. THE Library_View SHALL render a search input element at the top of the document list on the `/library/` page, visible without scrolling on standard desktop viewports (≥ 1024 px wide).
2. WHEN an authenticated user submits the search form with a non-empty query string, THE Library_View SHALL reload the page with the query reflected in the URL as a `q` GET parameter and display matching results.
3. WHEN an authenticated user submits the search form with an empty or whitespace-only query string, THE Library_View SHALL display the full unfiltered document list and SHALL NOT execute a search query against the database.
4. WHEN an authenticated user clears the search input and resubmits, THE Library_View SHALL return to displaying the full unfiltered document list.
5. THE Library_View SHALL preserve the current search query value inside the search input element when the page is rendered with an active `q` parameter, so that the user can see and edit their previous query.

---

### Requirement 2: Full-Text Search Across Multiple Fields

**User Story:** As a researcher, I want to search across all analysis fields of my papers, so that I can find documents regardless of which field contains the relevant term.

#### Acceptance Criteria

1. WHEN a Search_Query is submitted, THE Search_Engine SHALL search across the following fields: `Document.title`, `AnalysisResult.summary`, `AnalysisResult.abstract`, `AnalysisResult.keywords`, `AnalysisResult.methodology`, `AnalysisResult.technologies`, `AnalysisResult.authors`.
2. THE Search_Engine SHALL perform all text comparisons case-insensitively.
3. THE Search_Engine SHALL match documents where the Search_Query appears as a substring of any searchable field (partial match).
4. THE Search_Engine SHALL return only Documents owned by the authenticated user making the request.
5. WHEN a Document has no associated `AnalysisResult`, THE Search_Engine SHALL still include that Document in results if `Document.title` matches the Search_Query.
6. THE Search_Engine SHALL construct the search using Django ORM `Q` objects combined with the `|` operator so that a single database query is issued per search request.
7. WHEN the Search_Query contains multiple whitespace-separated words, THE Search_Engine SHALL return Documents that match ANY of the individual words across any searchable field (OR semantics).

---

### Requirement 3: Search Result Display

**User Story:** As a researcher, I want to see which part of a paper matched my search, so that I can quickly assess relevance without opening each document.

#### Acceptance Criteria

1. WHEN search results are returned, THE Library_View SHALL display each matching Document with its title, upload date, and at least one Snippet showing where the Search_Query matched.
2. THE Library_View SHALL wrap each occurrence of the Search_Query within a Snippet in a `<mark>` HTML element to produce a Highlight.
3. THE Library_View SHALL display a Snippet of up to 200 characters extracted from the first matching field, centered around the first occurrence of the Search_Query in that field.
4. THE Library_View SHALL display the total count of matching documents above the result list (e.g., "5 results for 'neural network'").
5. WHEN no documents match the Search_Query and active Filter_Set, THE Library_View SHALL display an empty-state message that includes the submitted query string and suggests the user try different terms.
6. THE Library_View SHALL indicate on each result card which fields matched (e.g., "Matched in: summary, keywords") using the field names from the Glossary.

---

### Requirement 4: Filter by Date Range

**User Story:** As a researcher, I want to filter results by upload date range, so that I can narrow down papers from a specific time period.

#### Acceptance Criteria

1. THE Library_View SHALL provide a date range filter with a "From" date input and a "To" date input.
2. WHEN an authenticated user submits a "From" date, THE Search_Engine SHALL exclude Documents with `created_at` earlier than the start of that date (00:00:00 UTC).
3. WHEN an authenticated user submits a "To" date, THE Search_Engine SHALL exclude Documents with `created_at` later than the end of that date (23:59:59 UTC).
4. WHEN both "From" and "To" dates are provided and the "From" date is later than the "To" date, THE Library_View SHALL display a validation error message and SHALL NOT execute the filtered query.
5. WHEN only one of "From" or "To" is provided, THE Search_Engine SHALL apply only the supplied bound and treat the other as unbounded.
6. THE Library_View SHALL preserve the submitted date range values in the filter inputs when the page is re-rendered with active date filters.

---

### Requirement 5: Filter by Methodology Type

**User Story:** As a researcher, I want to filter papers by methodology, so that I can find papers that use a specific research approach.

#### Acceptance Criteria

1. THE Library_View SHALL provide a methodology filter input that accepts a free-text string.
2. WHEN an authenticated user submits a methodology filter value, THE Search_Engine SHALL return only Documents whose associated `AnalysisResult.methodology` list contains at least one entry that matches the filter value as a case-insensitive substring.
3. WHEN the methodology filter is combined with a Search_Query, THE Search_Engine SHALL return only Documents that satisfy both conditions simultaneously (AND semantics between filters and search query).
4. THE Library_View SHALL preserve the submitted methodology filter value in the filter input when the page is re-rendered with an active methodology filter.

---

### Requirement 6: Filter by Technology

**User Story:** As a researcher, I want to filter papers by technology, so that I can find papers that use a specific tool or framework.

#### Acceptance Criteria

1. THE Library_View SHALL provide a technology filter input that accepts a free-text string.
2. WHEN an authenticated user submits a technology filter value, THE Search_Engine SHALL return only Documents whose associated `AnalysisResult.technologies` list contains at least one entry that matches the filter value as a case-insensitive substring.
3. WHEN the technology filter is combined with a Search_Query or other active filters, THE Search_Engine SHALL apply all active conditions simultaneously (AND semantics).
4. THE Library_View SHALL preserve the submitted technology filter value in the filter input when the page is re-rendered with an active technology filter.

---

### Requirement 7: Filter by Keyword

**User Story:** As a researcher, I want to filter papers by keyword, so that I can find papers tagged with a specific topic.

#### Acceptance Criteria

1. THE Library_View SHALL provide a keyword filter input that accepts a free-text string.
2. WHEN an authenticated user submits a keyword filter value, THE Search_Engine SHALL return only Documents whose associated `AnalysisResult.keywords` list contains at least one entry that matches the filter value as a case-insensitive substring.
3. WHEN the keyword filter is combined with a Search_Query or other active filters, THE Search_Engine SHALL apply all active conditions simultaneously (AND semantics).
4. THE Library_View SHALL preserve the submitted keyword filter value in the filter input when the page is re-rendered with an active keyword filter.

---

### Requirement 8: Sort Results

**User Story:** As a researcher, I want to sort search results by relevance, date, or title, so that I can find the most useful papers quickly.

#### Acceptance Criteria

1. THE Library_View SHALL provide a sort control with three options: "Relevance", "Date (Newest First)", and "Title (A–Z)".
2. WHEN the sort order is set to "Relevance" and a Search_Query is active, THE Search_Engine SHALL order results by Relevance_Score descending, with ties broken by `Document.created_at` descending.
3. WHEN the sort order is set to "Date (Newest First)", THE Search_Engine SHALL order results by `Document.created_at` descending regardless of Relevance_Score.
4. WHEN the sort order is set to "Title (A–Z)", THE Search_Engine SHALL order results by `Document.title` ascending, case-insensitively.
5. WHEN no Search_Query is active and the sort order is "Relevance", THE Search_Engine SHALL fall back to ordering by `Document.created_at` descending.
6. THE Library_View SHALL default to "Relevance" sort when a Search_Query is present and to "Date (Newest First)" when no Search_Query is present.
7. THE Library_View SHALL preserve the selected sort option in the sort control when the page is re-rendered.

---

### Requirement 9: Relevance Scoring

**User Story:** As a researcher, I want the most relevant results to appear first, so that I don't have to scan through unrelated papers.

#### Acceptance Criteria

1. THE Search_Engine SHALL compute a Relevance_Score for each result as the count of distinct searchable fields in which the Search_Query appears.
2. THE Search_Engine SHALL assign a higher Relevance_Score to a Document when the Search_Query appears in `Document.title` than when it appears only in body fields (`summary`, `abstract`, `keywords`, `methodology`, `technologies`, `authors`).
3. THE Search_Engine SHALL implement Relevance_Score computation using Django ORM annotation (e.g., `annotate` with `Case`/`When` expressions) so that scoring is performed in the database query rather than in Python application code.

---

### Requirement 10: URL State Preservation

**User Story:** As a researcher, I want to be able to share or bookmark a search URL, so that I can return to the same filtered view later.

#### Acceptance Criteria

1. THE Library_View SHALL encode the active Search_Query as the `q` GET parameter in the page URL.
2. THE Library_View SHALL encode the active "From" date filter as the `date_from` GET parameter in the page URL.
3. THE Library_View SHALL encode the active "To" date filter as the `date_to` GET parameter in the page URL.
4. THE Library_View SHALL encode the active methodology filter as the `methodology` GET parameter in the page URL.
5. THE Library_View SHALL encode the active technology filter as the `technology` GET parameter in the page URL.
6. THE Library_View SHALL encode the active keyword filter as the `keyword` GET parameter in the page URL.
7. THE Library_View SHALL encode the active sort selection as the `sort` GET parameter in the page URL.
8. WHEN an authenticated user loads the `/library/` page with any combination of the above GET parameters, THE Library_View SHALL restore all filter and sort controls to the values specified in those parameters and display the corresponding results.

---

### Requirement 11: Performance

**User Story:** As a researcher, I want search results to load quickly, so that I can iterate through queries without frustrating delays.

#### Acceptance Criteria

1. WHEN a Search_Query is submitted against a library of up to 500 Documents, THE Search_Engine SHALL return results within 2 seconds under normal server load.
2. THE Search_Engine SHALL use `select_related('analysis')` when querying Documents to avoid N+1 queries when accessing `AnalysisResult` fields.
3. THE Search_Engine SHALL issue no more than 3 database queries per search request (one for the document count, one for the paginated result set, and one for any aggregation needed for filter dropdowns).

---

### Requirement 12: Access Control

**User Story:** As a researcher, I want my search results to be scoped to my own library, so that I cannot see other users' documents.

#### Acceptance Criteria

1. THE Search_Engine SHALL filter all queries by `Document.user = request.user` before applying any search or filter conditions.
2. WHEN an unauthenticated user accesses the `/library/` page, THE Library_View SHALL redirect the user to the login page.
3. WHEN an authenticated user submits a Search_Query, THE Search_Engine SHALL never return Documents owned by a different user, regardless of query content.

---

### Requirement 13: Pagination of Search Results

**User Story:** As a researcher, I want search results to be paginated, so that the page remains usable when many documents match.

#### Acceptance Criteria

1. THE Library_View SHALL paginate search results to a maximum of 20 Documents per page.
2. THE Library_View SHALL display pagination controls (previous page, next page, page numbers) when the total result count exceeds 20.
3. WHEN an authenticated user navigates to a subsequent page of results, THE Library_View SHALL preserve all active search query, filter, and sort parameters in the pagination links.
4. WHEN an authenticated user requests a page number beyond the last available page, THE Library_View SHALL redirect to the last available page and display its results.
