# Requirements Document

## Introduction

The Paper Collections feature allows authenticated users of the research paper analyzer to organize their Document library into named collections (folders). Currently the library at `/library/` displays all documents in a flat list. This feature introduces a `Collection` model that groups documents, enabling users to create, rename, delete, and filter by collections. A document may belong to multiple collections simultaneously. Collections support an optional description, color, and icon to aid visual organization.

---

## Glossary

- **Collection**: A named, user-owned grouping of zero or more Documents. Equivalent to a folder or tag.
- **Document**: An existing model (`analyzer.Document`) representing a single analyzed research paper belonging to a user.
- **Collection_Manager**: The subsystem (views + model layer) responsible for creating, updating, deleting, and querying Collections and their memberships.
- **Library_View**: The Django view that renders the `/library/` page showing a user's Documents.
- **Membership**: The many-to-many relationship record linking a Document to a Collection.
- **Slug**: A URL-safe, human-readable identifier derived from the collection name, unique per user.
- **Color**: A hex color string (e.g., `#3B82F6`) used to visually distinguish a collection.
- **Icon**: A short string identifier referencing a supported icon (e.g., a Font Awesome class name such as `fa-folder`).

---

## Requirements

### Requirement 1: Create a Collection

**User Story:** As a researcher, I want to create a named collection, so that I can group related papers together under a meaningful label.

#### Acceptance Criteria

1. WHEN an authenticated user submits a valid collection name, THE Collection_Manager SHALL create a new Collection record owned by that user with the provided name.
2. WHEN a collection is created, THE Collection_Manager SHALL set the collection's `created_at` timestamp to the current server time.
3. WHEN an authenticated user submits a collection name that is an empty string or contains only whitespace, THE Collection_Manager SHALL return a validation error and SHALL NOT create a Collection record.
4. WHEN an authenticated user submits a collection name longer than 100 characters, THE Collection_Manager SHALL return a validation error and SHALL NOT create a Collection record.
5. WHEN an authenticated user submits a collection name that duplicates an existing collection name owned by the same user (case-insensitive), THE Collection_Manager SHALL return a validation error and SHALL NOT create a duplicate Collection record.
6. WHERE a description is provided, THE Collection_Manager SHALL store the description text (up to 500 characters) on the Collection record.
7. WHERE a color hex value is provided, THE Collection_Manager SHALL validate that the value matches the pattern `#[0-9A-Fa-f]{6}` and store it; IF the color value does not match that pattern, THEN THE Collection_Manager SHALL return a validation error.
8. WHERE an icon identifier is provided, THE Collection_Manager SHALL validate that the identifier is present in the supported icon list and store it; IF the identifier is not in the supported list, THEN THE Collection_Manager SHALL return a validation error.
9. WHEN a collection is created without a color, THE Collection_Manager SHALL assign a default color of `#6B7280`.
10. WHEN a collection is created without an icon, THE Collection_Manager SHALL assign a default icon of `fa-folder`.

---

### Requirement 2: List Collections

**User Story:** As a researcher, I want to see all my collections in the library sidebar or as tabs, so that I can quickly navigate to a specific group of papers.

#### Acceptance Criteria

1. WHEN an authenticated user loads the Library_View, THE Library_View SHALL retrieve all Collections owned by that user ordered by name ascending.
2. THE Library_View SHALL display each collection's name, color, icon, and document count.
3. THE Library_View SHALL display a document count equal to the number of Documents that are members of that collection and are owned by the requesting user.
4. WHEN a user has zero collections, THE Library_View SHALL display an empty-state prompt inviting the user to create their first collection.
5. THE Library_View SHALL display an "All Papers" entry that, when selected, shows all documents regardless of collection membership.

---

### Requirement 3: Filter Library by Collection

**User Story:** As a researcher, I want to filter my library by a specific collection, so that I can focus on a subset of papers relevant to a task.

#### Acceptance Criteria

1. WHEN an authenticated user selects a collection in the Library_View, THE Library_View SHALL display only the Documents that are members of that collection and are owned by that user.
2. WHEN an authenticated user selects "All Papers", THE Library_View SHALL display all Documents owned by that user regardless of collection membership.
3. WHEN an authenticated user selects a collection that contains zero documents, THE Library_View SHALL display an empty-state message indicating the collection is empty.
4. WHILE a collection filter is active, THE Library_View SHALL visually indicate which collection is currently selected.
5. WHEN an authenticated user applies a text search query while a collection filter is active, THE Library_View SHALL return only Documents that match both the search query and the active collection filter.

---

### Requirement 4: Add Documents to a Collection

**User Story:** As a researcher, I want to add one or more papers to a collection, so that I can organize my library without re-uploading documents.

#### Acceptance Criteria

1. WHEN an authenticated user requests to add a Document to a Collection, and both the Document and Collection are owned by that user, THE Collection_Manager SHALL create a Membership record linking the Document to the Collection.
2. WHEN an authenticated user requests to add a Document to a Collection where a Membership record already exists, THE Collection_Manager SHALL return a success response and SHALL NOT create a duplicate Membership record.
3. WHEN an authenticated user requests to add a Document to a Collection that is not owned by that user, THE Collection_Manager SHALL return a 403 Forbidden response and SHALL NOT create a Membership record.
4. WHEN an authenticated user requests to add a Document that is not owned by that user to any Collection, THE Collection_Manager SHALL return a 403 Forbidden response and SHALL NOT create a Membership record.
5. THE Collection_Manager SHALL support adding multiple Documents to a Collection in a single request by accepting a list of Document identifiers.
6. WHEN a batch add request contains one or more invalid Document identifiers, THE Collection_Manager SHALL add all valid Documents and SHALL return a response listing the identifiers that were not found or not authorized.

---

### Requirement 5: Remove Documents from a Collection

**User Story:** As a researcher, I want to remove a paper from a collection, so that I can keep my collections accurate without deleting the paper from my library.

#### Acceptance Criteria

1. WHEN an authenticated user requests to remove a Document from a Collection, and both are owned by that user, THE Collection_Manager SHALL delete the Membership record linking that Document to that Collection.
2. WHEN an authenticated user requests to remove a Document from a Collection where no Membership record exists, THE Collection_Manager SHALL return a success response and SHALL NOT raise an error.
3. WHEN an authenticated user requests to remove a Document from a Collection not owned by that user, THE Collection_Manager SHALL return a 403 Forbidden response and SHALL NOT modify any Membership record.
4. WHEN a Document is removed from a Collection, THE Collection_Manager SHALL NOT delete the Document from the user's library.

---

### Requirement 6: Rename a Collection

**User Story:** As a researcher, I want to rename a collection, so that I can keep my organizational structure up to date as my research evolves.

#### Acceptance Criteria

1. WHEN an authenticated user submits a new name for a Collection owned by that user, THE Collection_Manager SHALL update the Collection's name to the new value.
2. WHEN an authenticated user submits a new name that is an empty string or contains only whitespace, THE Collection_Manager SHALL return a validation error and SHALL NOT update the Collection record.
3. WHEN an authenticated user submits a new name longer than 100 characters, THE Collection_Manager SHALL return a validation error and SHALL NOT update the Collection record.
4. WHEN an authenticated user submits a new name that duplicates another existing collection name owned by the same user (case-insensitive), THE Collection_Manager SHALL return a validation error and SHALL NOT update the Collection record.
5. WHEN an authenticated user renames a Collection, THE Collection_Manager SHALL preserve all existing Membership records for that Collection.
6. WHEN an authenticated user attempts to rename a Collection not owned by that user, THE Collection_Manager SHALL return a 403 Forbidden response and SHALL NOT modify the Collection record.

---

### Requirement 7: Delete a Collection

**User Story:** As a researcher, I want to delete a collection, so that I can remove organizational groupings I no longer need without losing the underlying papers.

#### Acceptance Criteria

1. WHEN an authenticated user requests to delete a Collection owned by that user, THE Collection_Manager SHALL delete the Collection record and all associated Membership records.
2. WHEN a Collection is deleted, THE Collection_Manager SHALL NOT delete any Document records that were members of that Collection.
3. WHEN an authenticated user attempts to delete a Collection not owned by that user, THE Collection_Manager SHALL return a 403 Forbidden response and SHALL NOT delete the Collection record.
4. WHEN an authenticated user requests to delete a Collection that does not exist, THE Collection_Manager SHALL return a 404 Not Found response.

---

### Requirement 8: Update Collection Metadata

**User Story:** As a researcher, I want to update a collection's description, color, and icon, so that I can visually distinguish and annotate my collections.

#### Acceptance Criteria

1. WHEN an authenticated user submits an updated description for a Collection owned by that user, THE Collection_Manager SHALL update the description field; WHERE the description exceeds 500 characters, THE Collection_Manager SHALL return a validation error and SHALL NOT update the record.
2. WHEN an authenticated user submits an updated color for a Collection owned by that user, THE Collection_Manager SHALL validate the hex pattern `#[0-9A-Fa-f]{6}` and update the color field; IF the value does not match, THEN THE Collection_Manager SHALL return a validation error.
3. WHEN an authenticated user submits an updated icon for a Collection owned by that user, THE Collection_Manager SHALL validate the identifier against the supported icon list and update the icon field; IF the identifier is not supported, THEN THE Collection_Manager SHALL return a validation error.
4. WHEN an authenticated user attempts to update a Collection not owned by that user, THE Collection_Manager SHALL return a 403 Forbidden response and SHALL NOT modify the Collection record.

---

### Requirement 9: Document Count Accuracy

**User Story:** As a researcher, I want to see an accurate document count on each collection, so that I can quickly gauge the size of each group.

#### Acceptance Criteria

1. THE Collection_Manager SHALL compute the document count for a Collection as the number of distinct Documents linked via Membership records to that Collection.
2. WHEN a Document is added to a Collection, THE Collection_Manager SHALL reflect the updated count the next time the collection list is retrieved.
3. WHEN a Document is removed from a Collection, THE Collection_Manager SHALL reflect the updated count the next time the collection list is retrieved.
4. WHEN a Document owned by a user is deleted from the library, THE Collection_Manager SHALL remove all Membership records for that Document so that collection counts remain accurate.

---

### Requirement 10: Access Control

**User Story:** As a researcher, I want my collections to be private to my account, so that other users cannot view or modify my organizational structure.

#### Acceptance Criteria

1. THE Collection_Manager SHALL associate every Collection with exactly one User via a foreign key.
2. WHEN an unauthenticated request is made to any Collection endpoint, THE Collection_Manager SHALL return a 401 Unauthorized response.
3. WHEN an authenticated user requests a list of collections, THE Collection_Manager SHALL return only Collections owned by that user.
4. WHEN an authenticated user requests details of a specific Collection not owned by that user, THE Collection_Manager SHALL return a 404 Not Found response.

---

### Requirement 11: API Endpoints

**User Story:** As a developer integrating the front-end, I want well-defined HTTP endpoints for collection operations, so that the UI can interact with collections without full page reloads.

#### Acceptance Criteria

1. THE Collection_Manager SHALL expose a `POST /collections/` endpoint that creates a new collection and returns the created collection's data as JSON.
2. THE Collection_Manager SHALL expose a `GET /collections/` endpoint that returns a JSON list of all collections owned by the authenticated user, each including `id`, `name`, `description`, `color`, `icon`, and `document_count`.
3. THE Collection_Manager SHALL expose a `PATCH /collections/<id>/` endpoint that updates the name, description, color, or icon of a collection and returns the updated collection data as JSON.
4. THE Collection_Manager SHALL expose a `DELETE /collections/<id>/` endpoint that deletes a collection and returns a 204 No Content response on success.
5. THE Collection_Manager SHALL expose a `POST /collections/<id>/add-documents/` endpoint that accepts a list of document IDs and adds them to the collection, returning a JSON summary of added and skipped IDs.
6. THE Collection_Manager SHALL expose a `POST /collections/<id>/remove-documents/` endpoint that accepts a list of document IDs and removes them from the collection, returning a 200 OK response.
7. WHEN any Collection endpoint receives a request with a malformed JSON body, THE Collection_Manager SHALL return a 400 Bad Request response with a descriptive error message.
