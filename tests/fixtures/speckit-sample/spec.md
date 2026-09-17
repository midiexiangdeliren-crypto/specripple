# Feature: User Authentication

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Email login (Priority: P1)

A registered user logs in with email and password.

**Why this priority**: core value proposition of the product.

#### Acceptance Scenarios

| Given | When | Then |
| --- | --- | --- |
| Registered user | Valid credentials submitted | Session issued |
| Registered user | Wrong password | Login fails with clear error |

### User Story 2 - Session persistence (Priority: P2)

A logged-in session survives an application restart.

#### Acceptance Scenarios

| Given | When | Then |
| --- | --- | --- |
| Active session | App restarts | User stays logged in |

### Edge Cases

- Expired session token redirects to login.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-1**: Login accepts email and password.
- **FR-2**: Sessions persist across restarts.

## Success Criteria

### Measurable Outcomes

- Login success rate above 99%.
