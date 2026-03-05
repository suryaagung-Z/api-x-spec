<!--
Sync Impact Report
- Version change: N/A → 1.0.0
- Modified principles: (initial ratification of all principles)
- Added sections: Core Principles; Technology & Architecture Constraints;
	Development Workflow & Quality Gates; Governance
- Removed sections: none
- Templates:
	- ✅ .specify/templates/plan-template.md – Constitution Check gates updated
		for Python stack, clean architecture, and testing.
	- ✅ .specify/templates/spec-template.md – Already aligned; no changes
		required.
	- ✅ .specify/templates/tasks-template.md – Testing language aligned with
		test-first, non-optional tests.
- Follow-up TODOs: none.
-->

# API-X Spec Constitution

## Core Principles

### I. Python API Stack (Non-Negotiable)

- Backend services MUST be implemented in Python (default: 3.11+), unless a
	different language is explicitly justified in the feature plan.
- HTTP APIs for new backend features MUST use a mainstream, well-supported
	framework (default recommendation: FastAPI). Alternative frameworks MUST be
	justified in the plan.
- Third-party libraries MUST be popular, actively maintained, and
	well-documented. Niche or unmaintained libraries MAY be used only with clear
	risk acknowledgment and fallback strategy in the plan.

### II. Clean Architecture Boundaries

- Business rules and domain models MUST be framework-agnostic plain Python
	code.
- The architecture MUST separate at least these concerns:
	- API layer (e.g., FastAPI routers/controllers)
	- Application/services/use-case layer
	- Domain layer (entities, value objects, domain logic)
	- Infrastructure/adapters (ORMs, HTTP clients, messaging, persistence)
- Dependencies MUST point inward: outer layers may depend on inner layers, but
	domain code MUST NOT depend on frameworks or infrastructure details.
- Each feature MUST document where its composition root lives (e.g., API
	startup module or dependency-injection container) and how dependencies are
	wired.

### III. Test-First & Fast Feedback (Non-Negotiable)

- Every user story that introduces or changes behavior MUST have automated
	tests before it is considered done.
- Unit tests MUST exist for core domain and application logic. HTTP APIs and
	integrations SHOULD have contract and/or integration tests where they are
	part of the story value.
- Tests SHOULD be written before or alongside implementation and MUST fail at
	least once before being made to pass (red-green-refactor spirit).
- The default testing stack for Python APIs is `pytest` with tests organized
	under `tests/unit`, `tests/integration`, and `tests/contract` as appropriate.
	Deviations MUST be justified in the plan.

### IV. Specification-Driven APIs & Contracts

- Every feature MUST start from a written specification under `specs/` using
	the project spec template.
- Behavior, inputs, outputs, and error envelopes for APIs MUST be derived from
	and traceable back to the feature spec.
- Where HTTP/JSON contracts are exposed, they SHOULD be capturable as
	OpenAPI/JSON Schema or equivalent artifacts during planning or contracts
	phases.
- Changes to external contracts (request/response schemas, status codes,
	error formats) MUST be documented in the spec and validated by tests.

### V. Simplicity, Observability, and Versioning Discipline

- The simplest architecture that satisfies the spec MUST be preferred. New
	services, projects, or abstraction layers MUST be justified and, when
	necessary, captured in the complexity tracking section of the plan.
- Logging and error reporting MUST be sufficient to debug issues in
	production-like environments without relying on ad-hoc print debugging.
- Public APIs and libraries MUST follow semantic versioning for breaking
	changes. Breaking changes to existing behavior MUST be explicitly called out
	in specs and plans, with migration guidance where applicable.

## Technology & Architecture Constraints

- **Language**: Python is the primary implementation language for backend
	APIs. Default runtime target is Python 3.11+; other versions MUST be
	explicitly stated in the plan.
- **Frameworks**: New HTTP APIs SHOULD default to FastAPI. Other frameworks
	(Flask, Django REST Framework, etc.) MAY be used when justified by
	requirements (ecosystem fit, existing codebase) and called out in the plan.
- **Project structure** (default for new Python API features):

	```text
	src/
	├── api/          # routers/controllers
	├── application/  # use cases, services
	├── domain/       # entities, value objects, domain logic
	└── infrastructure/ # DB, messaging, external integrations

	tests/
	├── unit/
	├── integration/
	└── contract/
	```

- **Type safety & quality**:
	- Public modules and functions MUST use type hints.
	- Code MUST be formatted with an auto-formatter (e.g., black) and checked by
		a linter (e.g., ruff/flake8). The chosen tools MUST be documented in the
		plan or project README.
- **Configuration**: Runtime configuration (secrets, connection strings,
	environment-specific values) MUST come from environment variables or a
	configuration system that can be safely managed per environment. Hard-coded
	secrets are forbidden.
- **Dependencies**: Dependencies MUST be pinned or constrained via a standard
	mechanism (e.g., `requirements.txt`, `pyproject.toml`) and reviewed in
	code review.

## Development Workflow & Quality Gates

- Each feature follows the Speckit flow: spec → clarify (as needed) → plan →
	research/data-model/contracts → tasks → implementation.
- The "Constitution Check" section in the implementation plan is a mandatory
	gate: features MUST not proceed to implementation if they violate core
	principles without explicit, documented justification.
- A feature is considered ready for merge only when:
	- The spec is up to date with the implemented behavior.
	- The plan documents architecture, dependencies, and any deviations from
		default stack or structure.
	- Tasks cover implementation and testing work and are traceable to user
		stories.
	- Automated tests exist and are passing for all impacted behavior.
- Code review MUST include a check against this constitution. Reviewers are
	responsible for blocking changes that introduce unjustified complexity,
	violate clean architecture boundaries, or ship untested behavior.

## Governance

- This constitution supersedes ad-hoc conventions when there is a conflict.
- Amendments to the constitution MUST be proposed via pull request that:
	- Updates `.specify/memory/constitution.md` including the Sync Impact Report
		comment.
	- Bumps the **Version** field according to semantic versioning:
		- MAJOR: Backward-incompatible governance or principle changes.
		- MINOR: New principles or sections, or materially expanded guidance.
		- PATCH: Clarifications, wording fixes, and non-semantic refinements.
	- Updates affected templates (plan, spec, tasks, commands, prompts) so they
		remain aligned with the constitution.
- Ratification and amendments MUST be reviewed and approved by the designated
	technical owner(s) of this repository (or their delegate) before merge.
- Compliance expectations:
	- Feature plans MUST explicitly call out any intentional deviations from the
		constitution and document rationale and mitigations.
	- Periodic reviews MAY be run to ensure live code and specs still reflect
		these principles; identified gaps SHOULD result in follow-up tasks.

**Version**: 1.0.0 | **Ratified**: 2026-03-05 | **Last Amended**: 2026-03-05

