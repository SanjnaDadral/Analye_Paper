# Requirements Document

## Introduction

The Similar Papers feature enables users to discover related research papers within their own library immediately after analyzing a new paper. After a paper is analyzed, the result page displays a "Similar Papers in Your Library" section showing the top 5 most similar papers ranked by a composite similarity score. Similarity is computed on-demand by combining keyword overlap, methodology overlap, technology overlap, and summary text similarity. Each result shows the similarity percentage, which specific fields matched, and a direct link to that paper's result page. Only papers belonging to the same user are compared, ensuring privacy and relevance.

## Glossary

- **Similarity_Engine**: The component responsible for computing composite similarity scores between two `AnalysisResult` records.
- **Composite_Score**: A weighted numerical score (0–100) combining keyword overlap, methodology overlap, technology overlap, and summary text similarity.
- **Keyword_Overlap**: The Jaccard similarity between the `keywords` lists of two `AnalysisResult` records, expressed as a percentage.
- **Methodology_Overlap**: The Jaccard similarity between the `methodology` lists of two `AnalysisResult` records, expressed as a percentage.
- **Technology_Overlap**: The Jaccard similarity between the `technologies` lists of two `AnalysisResult` records, expressed as a percentage.
- **Summary_Similarity**: The TF-IDF cosine similarity between the `summary` fields of two `AnalysisResult` records, expressed as a percentage.
- **Match_Breakdown**: A structured description of which fields contributed to the similarity score, including the specific shared terms for each field.
- **Target_Paper**: The paper whose result page is currently being viewed.
- **Candidate_Paper**: Any other paper in the same user's library that is compared against the Target_Paper.
- **Result_Page**: The Django view at `/result/<document_id>/` that displays the full analysis of a paper.
- **User_Library**: The set of all `Document` records owned by a given authenticated user.

---

## Requirements

### Requirement 1: Compute Composite Similarity Score

**User Story:** As a researcher, I want the system to compute a meaningful similarity score between papers, so that the most relevant papers are surfaced at the top.

#### Acceptance Criteria

1. WHEN the Similarity_Engine compares two papers, THE Similarity_Engine SHALL compute a Composite_Score as a weighted average of Keyword_Overlap (40%), Methodology_Overlap (25%), Technology_Overlap (20%), and Summary_Similarity (15%).
2. THE Similarity_Engine SHALL compute Keyword_Overlap as `|A ∩ B| / |A ∪ B| * 100` where A and B are the lowercased keyword lists of the two papers, returning 0 when both lists are empty.
3. THE Similarity_Engine SHALL compute Methodology_Overlap as `|A ∩ B| / |A ∪ B| * 100` where A and B are the lowercased methodology lists of the two papers, returning 0 when both lists are empty.
4. THE Similarity_Engine SHALL compute Technology_Overlap as `|A ∩ B| / |A ∪ B| * 100` where A and B are the lowercased technologies lists of the two papers, returning 0 when both lists are empty.
5. WHEN both papers have non-empty summary fields, THE Similarity_Engine SHALL compute Summary_Similarity using TF-IDF cosine similarity on the summary texts.
6. IF either paper has an empty summary field, THEN THE Similarity_Engine SHALL assign a Summary_Similarity of 0 for that pair.
7. THE Similarity_Engine SHALL return the Composite_Score rounded to one decimal place, capped at 100.0.

---

### Requirement 2: Retrieve Top Similar Papers

**User Story:** As a researcher, I want to see the top 5 most similar papers in my library, so that I can quickly navigate to related work without manually searching.

#### Acceptance Criteria

1. WHEN a user views the Result_Page for a Target_Paper, THE Similarity_Engine SHALL compare the Target_Paper against all Candidate_Papers in the User_Library that have an associated `AnalysisResult`.
2. THE Similarity_Engine SHALL exclude the Target_Paper itself from the list of Candidate_Papers.
3. THE Similarity_Engine SHALL return the top 5 Candidate_Papers ranked by Composite_Score in descending order.
4. IF the User_Library contains fewer than 5 Candidate_Papers with an `AnalysisResult`, THEN THE Similarity_Engine SHALL return all available Candidate_Papers ranked by Composite_Score.
5. IF the User_Library contains no Candidate_Papers with an `AnalysisResult`, THEN THE Similarity_Engine SHALL return an empty list.
6. THE Similarity_Engine SHALL only compare the Target_Paper against papers belonging to the same authenticated user, never against papers owned by other users.

---

### Requirement 3: Display Similar Papers Section on Result Page

**User Story:** As a researcher, I want to see a "Similar Papers in Your Library" section on the result page, so that I can discover related papers without leaving the page.

#### Acceptance Criteria

1. WHEN a user views the Result_Page and at least one similar paper exists, THE Result_Page SHALL display a "Similar Papers in Your Library" section containing up to 5 similar paper cards.
2. WHEN a user views the Result_Page and no similar papers exist, THE Result_Page SHALL display a message indicating that no similar papers were found in the library.
3. THE Result_Page SHALL display each similar paper card with: the paper title, the Composite_Score as a percentage (e.g., "73.5% similar"), and a Match_Breakdown.
4. THE Result_Page SHALL render each similar paper card with a clickable link to that paper's Result_Page at `/result/<document_id>/`.
5. THE Result_Page SHALL display the similar papers section below the main analysis content without requiring a page reload.

---

### Requirement 4: Display Match Breakdown

**User Story:** As a researcher, I want to see which fields matched between papers, so that I understand why two papers are considered similar.

#### Acceptance Criteria

1. WHEN a Candidate_Paper shares at least one keyword with the Target_Paper, THE Result_Page SHALL display the shared keywords under a "Shared keywords" label within the similar paper card.
2. WHEN a Candidate_Paper shares at least one methodology item with the Target_Paper, THE Result_Page SHALL display the shared methodology items under a "Shared methodology" label within the similar paper card.
3. WHEN a Candidate_Paper shares at least one technology with the Target_Paper, THE Result_Page SHALL display the shared technologies under a "Shared technologies" label within the similar paper card.
4. WHEN a Candidate_Paper has a Summary_Similarity greater than 0, THE Result_Page SHALL display the summary similarity percentage under a "Summary similarity" label within the similar paper card.
5. IF a Candidate_Paper shares no keywords, methodology, or technologies and has a Summary_Similarity of 0, THEN THE Result_Page SHALL display "No specific field matches found" within the similar paper card.

---

### Requirement 5: On-Demand Similarity Computation

**User Story:** As a system operator, I want similarity to be computed on-demand at page load, so that no pre-computation infrastructure is needed for small libraries.

#### Acceptance Criteria

1. WHEN the Result_Page is requested, THE Similarity_Engine SHALL compute all similarity scores synchronously within the same HTTP request-response cycle.
2. THE Similarity_Engine SHALL complete similarity computation for a User_Library of up to 100 papers within 3 seconds.
3. THE Similarity_Engine SHALL NOT persist computed similarity scores to the database.
4. THE Similarity_Engine SHALL NOT require any background task queue or scheduled job to function.

---

### Requirement 6: Access Control

**User Story:** As a user, I want my similar papers results to only include my own papers, so that my library remains private and results are relevant to me.

#### Acceptance Criteria

1. WHEN an authenticated user requests the Result_Page, THE Similarity_Engine SHALL only retrieve Candidate_Papers from the `Document` records where `user` matches the authenticated user.
2. IF an unauthenticated user attempts to access the Result_Page, THEN THE Result_Page SHALL redirect the user to the login page.
3. IF an authenticated user attempts to access the Result_Page for a document not owned by them, THEN THE Result_Page SHALL return a 404 response.

---

### Requirement 7: Graceful Handling of Incomplete Analysis Data

**User Story:** As a researcher, I want the similar papers feature to work even when some papers have incomplete analysis data, so that partial data does not break the feature.

#### Acceptance Criteria

1. IF a Candidate_Paper has an empty `keywords` list, THEN THE Similarity_Engine SHALL treat Keyword_Overlap as 0 for that pair without raising an error.
2. IF a Candidate_Paper has an empty `methodology` list, THEN THE Similarity_Engine SHALL treat Methodology_Overlap as 0 for that pair without raising an error.
3. IF a Candidate_Paper has an empty `technologies` list, THEN THE Similarity_Engine SHALL treat Technology_Overlap as 0 for that pair without raising an error.
4. IF a Candidate_Paper has an empty `summary` field, THEN THE Similarity_Engine SHALL treat Summary_Similarity as 0 for that pair without raising an error.
5. IF the Target_Paper has no associated `AnalysisResult`, THEN THE Result_Page SHALL display the similar papers section as empty with an appropriate message.
