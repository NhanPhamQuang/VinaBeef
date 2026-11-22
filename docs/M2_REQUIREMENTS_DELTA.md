# M1 → M2 Requirements and Architecture Delta

## Source and classification

- **M1 baseline:** the team's October 2026 final architecture report and the ID-aligned UC-01..UC-28 workbook supplied earlier.
- **M2 assignment-confirmed issue 1:** farm sites frequently lose network connectivity while gate readers process cattle movement transactions.
- **M2 assignment-confirmed issue 2:** barn supervisors need mobile-app-assisted on-site vaccination and health data entry with an RFID reader.
- **M2 delivery tasks:** module view, component-and-connector view, allocation view, SOLID explanation and reflection, and implementation of **at least one** main module.

## Updated use cases

- **UC-07** now has a conditional, offline-first farm gateway intake flow. Local acknowledgment means only "durably queued at the farm", not "central movement accepted".
- **UC-08 / UC-09 / UC-10 / UC-13 / UC-27** must account for delayed/duplicate observations and reconciliation; a central dashboard might lag a disconnected site.
- **UC-14 / UC-15 / UC-16** support on-site mobile entry; the backend remains the authoritative health record store.
- **UC-29 (M2 derived)** Identify animal by scanned RFID EPC in a mobile workflow. Physical RFID scanning uses a keyboard-wedge device or a typed EPC in this demo, not a real vendor SDK.
- **UC-30 (M2 derived)** Persist and synchronize deferred RFID events between the local SQLite gateway and central platform.
- **UC-31 (proposed)** Review and resolve failed synchronization: queue inspection exists; a comprehensive operator resolution workflow remains unimplemented.

## Traceability additions

- **FR-21 (derived from M2 issue):** support farm-side RFID event acceptance through WAN interruptions and deferred delivery to the central system of record.
- **FR-22 (assignment-confirmed capability):** support on-site vaccination and health data entry using a mobile application and RFID reader.
- **NFR-P01:** maximum 2 s response per eligible RFID read under the *defined* peak experiment; gateway local acknowledgment and central processing acknowledgment must be reported separately.
- **NFR-R01:** no loss of successfully acknowledged records during defined normal operation. Events never received by the reader or gateway are not covered by this software-only demonstration.
- **NFR-S01:** RBAC and comprehensive audit. This demo includes an operation audit ledger but some security scenarios still require stronger verification.

## Open decisions (never silently upgraded to confirmed requirements)

- Actual RFID reader protocol, event identifiers, directional detection, clock sync and read multiplicity.
- Farm policy for missing-animal return sessions/windows; the demo uses a configurable **example** grace period.
- Offline duration, disk capacity, local store protection, clock skew and expected replay throughput.
- Physical RFID reader integration, offline animal lookup requirements and approval workflow for clinical records.
- National Disease Control API endpoint, security protocol, payload schema, frequencies and redaction/retention rules.
- Current local-only deployment: central FastAPI and SQLite gateway run as separate Python processes using one `.venv`; a real farm gateway would run at the physical site.

See `use_case_coverage.csv` for current implementation evidence and limitations. The M1 spreadsheet is provided unchanged as a baseline.
