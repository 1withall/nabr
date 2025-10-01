# Project Overview

Nābr is a community-focused platform designed to connect verified volunteers with local individuals or groups in need. The MVP encompasses:

- **User Verification:** Implement multi-layer verification processes.
- **Volunteer Request Management:** Facilitate request creation, matching, and assignment.
- **Event-Linked Reviews:** Allow participants to submit reviews post-assistance.
- **Temporal Workflow Integration:** Orchestrate all backend processes using Temporal Workflows and Activities.

---

## Development Environment

- **Package Management:** Utilize the `uv` package management system **exclusively**.
- **Execution:** Run Python code using `uv run` from the project root.
- **Environment Setup:** Create and manage project and virtual environments programmatically via `uv init` and `uv add/remove`.
- **Temporal Integration:** Develop using the `temporalio/temporal:1.4.1` Docker image, incorporating built-in CLI, UI, Server, and SQLite DB (bind-mounted to container) for local development.
- Maintain a robust, comprehensive `changelog` according to modern best practices where every action taken within the repo is clearly documented apart from source/version control features. This `changelog` should only ever be appended-to (never edited).

---

## Coding Guidelines

- **Scope Adherence:** Focus solely on MVP features; avoid introducing additional functionalities.
- **Modular Design:** Structure code to facilitate future expansion without refactoring core components.
- **Temporal Workflows:** Ensure all processes that *can* be *are* implemented as Temporal Workflows and Activities, with comprehensive error handling and observability with persistent, immutable logging.
- **UI Copy:** Maintain neutral, concise, and user-focused language in all user interface elements.

---

## Security and Privacy

- **Data Handling:** Implement comprehensive and robust security features: encryption, secure storage, and access controls for all personal information, utilizing current best practices for maximum security, enterprise-level systems such as medical/financial/government institutions.
- **Immutability:** Ensure that event logs, reviews, and verification data are immutable and auditable.
- **Privacy:** Expose only necessary participant information, safeguarding personal privacy.

---

## Testing and Validation

- **Reliability:** Verify that workflows execute reliably and produce auditable logs.
- **MVP Functionality:** Ensure all core features are fully functional, processing at least 100 simulated volunteer requests.
- **Cross-Platform Compatibility:** Test code across web, iOS, and Android platforms to ensure consistent behavior.

---

## Output Expectations

- **Code Quality:** Produce fully functional Python modules with maximum, advanced Temporal integration.
- **Documentation:** Provide clear, concise, and neutral inline documentation.
- **Logging:** Implement immutable, auditable, and observable logging for all workflows.
- **Modularity:** Ensure code is modular, supporting future feature expansion.
- **Setup Instructions:** Include automated setup instructions using `uv`.

---

## Copilot Interaction Guidelines

- **Task Clarity:** Provide clear, well-scoped tasks with specific acceptance criteria.
- **Context Provision:** Open relevant files and provide specific repositories, files, and symbols as context.
- **Prompt Refinement:** Rephrase prompts as needed to obtain desired responses.
- **Feedback Utilization:** Use feedback mechanisms to improve future suggestions.

---

This document serves as the primary guide for GitHub Copilot in assisting with the Nābr MVP development. Adherence to these instructions will ensure consistency, quality, and alignment with project objectives.

