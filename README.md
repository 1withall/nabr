# README for GitHub Copilot

This README provides instructions for the AI co-developer to build the **minimum viable product (MVP)** of the Nābr app. The Nābr app is a community-focused platform that connects verified volunteers with local individuals or groups in need, coordinating assistance, feedback, and follow-up through a secure, transparent, and reliable system. Its primary aim is to strengthen community engagement, foster trust and accountability, and ensure that every interaction is efficient, private, and meaningful. The app also emphasizes fairness, equality, and autonomy, giving users confidence that their needs and contributions are respected and protected.

All backend and behind-the-scenes processes must be implemented using **Temporal workflows and activities**. Temporal integration is mandatory and must serve as the foundational “glue” of the system, ensuring that every process, to the extent possible, is orchestrated, observable, auditable, and immutably logged. This includes all user verification, volunteer matching, request handling, notifications, review submissions, data operations, and any internal system processes. Temporal is essential for reliability, transparency, and security, and it must not be treated as optional or secondary.

---

## MVP Scope

The MVP includes the following core features, with each process orchestrated through Temporal workflows and activities for maximum reliability and traceability:

1. **User Verification**

   - All participants (volunteers, requesters, businesses, organizations) must have verified identities. “Minimal verification” requires in-person confirmation by at least two trusted community members (notaries, community leaders, or other recognized figures).
   - Verification may also include secure digital credentials and/or personal references. Multiple verification methods provide layered, 100% verifiable identification that are difficult or impossible to spoof individually.
   - Minimal verification is required before accessing core features such as posting, requesting, reviewing, or interacting with others.
   - Verification processes must be implemented as Temporal workflows and activities to ensure immutability, reliability, and traceable logging.
   - Verification should prevent duplication, fraud, and unauthorized access wherever feasible.

2. **Volunteer Requests**

   - Users can create requests for assistance using structured forms to indicate their needs and preferences.
   - An advanced algorithm matches requestor needs and preferences with volunteer skills and availability. There is no searchable database of requests; all matching occurs exclusively through the Temporal-backed system to preserve dignity.
   - Request creation, assignment, acceptance, and completion processes are handled as Temporal Workflows/Activities for reliability, consistency, and traceable logging.
   - The system enforces fairness, preventing exploitation or misuse of volunteer assistance, and ensuring that all contributions are valued and recognized appropriately.

3. **Event-Linked Reviews**

   - Reviews are tied to completed, verified events and can only be submitted by event participants. The specific details of personal requests for help (exactly what assistance was provided) will be kept private to preserve participant dignity, but the names of the participants and the time and location of the assistance provided should be “public knowledge” to the extent that if a person or property are harmed, there can be accountability for the perpetrator(s).
   - Reviews are immutable, auditable, and managed via Temporal Workflows to maintain trust and transparency.
   - Safeguards prevent duplicate or fraudulent submissions.
   - Users can query review history, aggregate ratings, and event summaries without compromising personal privacy.
   - Reviews reinforce fairness, accountability, and the credibility of participants within the system.

---

## UI and Interaction Guidelines

- All interface elements must implement robust, comprehensive, and proactive accessibility features using modern best practices.
- Use clear, neutral, and concise language to guide users effectively without ideological or promotional framing.
- Emphasize clarity, direct usability, and intuitive navigation for all participants.
- Provide immediate, real-time feedback for actions such as creating requests, claiming tasks, or submitting reviews. All feedback mechanisms should be integrated through Temporal Workflows.
- Include intuitive navigation elements: home, create request, browse requests, profile/verification status, and notifications center.
- Support contextual, Workflow-managed notifications for all relevant updates.
- Maintain consistent design and functionality across platforms, prioritizing clarity and efficiency over aesthetic elements.

---

## Data Handling

- Personal information must be a foundational priority for security, employing comprehensive, state-of-the-art measures including encryption, secure storage, access controls, and best practices for privacy and information security.
- Event logs, requests, reviews, and other critical interactions must be immutable, auditable, and securely logged via Temporal Workflows/Activities, utilizing Temporal’s advanced error-handling, logging, and observability features robustly and comprehensively.
- Data architecture must support efficient querying of events, requests, reviews, and verification statuses while ensuring participant privacy and transparency.
- Aggregate Activity and summary data may be publicly viewable to support transparency, but no individual participant information should be exposed beyond what is necessary/logical.

---

## Technical Requirements

- Cross-platform support: web, iOS, Android.
- Modular, adaptable, and maintainable architecture that allows for expansion without disrupting existing functionality.
- Lightweight code structure with clear separation of concerns between modules.
- Scalable backend capable of supporting growth in users, requests, and events.
- All processes that can be *must* be executed through Temporal Workflows and Activities, ensuring reliability, traceability, observability, and immutable logging.
- Clear integration points for future extensions or module additions without impacting existing processes.
- Logical and orderly organization of directory structure according to best practices.
- Define release criteria for the MVP, covering functionality, usability, and reliability. These criteria will be used to assess readiness for deployment.
  ## Assumptions and Constraints

## Assumptions and Constraints

- **Temporal Dependency:** All backend processes rely on Temporal; any changes to Temporal or workflow architecture may affect implementation and stability.
- **Package Management:** The project assumes the `uv` package management system is used consistently; reliance on other package managers could introduce conflicts.
- **Immutable Logging:** All event logs, reviews, and verification data are assumed to be immutable; modifications to this requirement could impact transparency and trust.
- **User Verification:** Effective verification requires access to in-person trusted community members; limited availability could constrain MVP operations.
- **Algorithmic Matching:** The volunteer-request matching algorithm assumes accurate input data and sufficient volunteer pool; data inconsistencies or low participation could affect effectiveness.
- **Cross-Platform Operation:** The MVP assumes compatibility across web, iOS, and Android; platform-specific constraints could limit features or user experience.
- **Privacy and Security:** Strong encryption and access controls are assumed; any deviation could risk PII exposure or regulatory non-compliance.
- **Operational Environment:** Assumes sufficient server resources, network reliability, and access to \`Docker Compose\` for Temporal; resource constraints may affect deployment and testing (though the development environment will take place exclusively on the sole human developer's high-performance, top-tier, bleeding-edge "consumer-grade" PC).

## MVP SMART Goals

The MVP has the following SMART goals to guide development and measure success:

- **Specific:** Enable verified volunteers to assist local community members via secure request matching.
- **Measurable:** Successfully process at least 100 volunteer requests and track completion, satisfaction, and review accuracy.
- **Achievable:** Ensure all core features (verification, request creation, volunteer matching, reviews) function reliably using Temporal Workflows.
- **Relevant:** Strengthen community engagement and trust while maintaining security, privacy, and fairness.
- **Time-bound:** MVP should be fully functional and tested within 12 weeks from project start, with all Temporal workflows operational and logging verified.

---

## Copilot Instructions

- *All* package/project management ***needs*** to be accomplished with advanced, expert-level usage of the `uv` package management system (**not** `pip`), and *all* Python code is required to be executed with `uv run` from the project root. The virtual environment and `pyproject.toml` file for the project ***must*** be created/updated programmatically from the terminal using `uv init` and `uv add/remove/etc`. Use context7 as the source of truth for all packages/libraries/etc, *including* `uv`.
- Generate code and suggestions strictly for MVP features: verification, request creation and management, volunteer matching, and event-linked reviews.
- Keep UI copy functional, concise, neutral, and user-focused.
- Avoid introducing features, terminology, or functionality beyond the MVP scope.
- Structure components and modules for straightforward expansion once MVP is operational.
- Ensure that all logic, data operations, notifications, and workflows are fully managed through Temporal activities, maintaining consistent, traceable, reliable, and immutably logged execution throughout the system.
- Utilize the `temporalio/temporal:1.4.1` official Docker image (which includes the Temporal CLI, UI, Server, and a built-in SQLite DB (bind-mounted to a local data directory)) for development, with a clear strategy for migrating to cloud services when deployed.

