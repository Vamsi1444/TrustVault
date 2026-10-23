# TrustVault — Threat Model

## 1. Project Overview

TrustVault is a secure document-sharing application that allows authenticated users to upload, manage, search, download, and share documents with other users.

The application supports:

* Document owners.
* Viewers with read permissions.
* Users with edit permissions.
* Administrators who can inspect activity logs.

The backend uses Flask, SQLAlchemy, JWT authentication, and PostgreSQL in production. The frontend uses React.

## 2. Assets to Protect

| Asset               | Security Importance                           |
| ------------------- | --------------------------------------------- |
| User credentials    | Prevent account compromise                    |
| JWT access tokens   | Prevent unauthorized API access               |
| Uploaded documents  | Protect document confidentiality              |
| Document metadata   | Prevent unauthorized information disclosure   |
| Permission records  | Prevent unauthorized access escalation        |
| Audit logs          | Preserve accountability and traceability      |
| Database records    | Protect integrity and availability            |
| Application secrets | Prevent authentication and signing compromise |

## 3. Threat Actors

1. Unauthenticated attackers attempting to access protected endpoints.
2. Authenticated users attempting to access documents belonging to other users.
3. Malicious viewers attempting to download or modify documents without permission.
4. Users attempting to grant themselves additional permissions.
5. Attackers attempting to manipulate or delete audit records.
6. Compromised accounts attempting to misuse legitimate permissions.

## 4. Threat Analysis and Mitigations

### T1 — Unauthorized Document Access

**Threat:** A user changes a document ID in an API request to access another user's document.

**Impact:** Confidential documents could be disclosed.

**Mitigation:**

* Authenticate protected endpoints using JWT.
* Check document ownership or explicit read permission on the server.
* Enforce authorization independently of frontend visibility.
* Check permissions before returning document metadata or file contents.

### T2 — Unauthorized Document Download

**Threat:** An authenticated user directly calls the download endpoint without having permission.

**Impact:** Private documents could be downloaded.

**Mitigation:**

* Perform server-side authorization before accessing the stored file.
* Permit downloads only for owners and users with valid read/edit permissions.
* Record successful and denied download attempts.
* Do not expose public or long-lived document URLs.

### T3 — Privilege Escalation

**Threat:** A viewer attempts to grant permissions, revoke permissions, or change another user's access.

**Impact:** Unauthorized users could gain control over private documents.

**Mitigation:**

* Restrict permission management to active document owners.
* Validate target users and permission types.
* Support only defined permission levels: `read` and `edit`.
* Recheck authorization on every permission-management request.

### T4 — Permission Revocation Bypass

**Threat:** A user continues accessing a document after their permission has been revoked.

**Impact:** Formerly authorized users could retain access.

**Mitigation:**

* Check current database permissions for each protected request.
* Avoid relying on cached authorization decisions.
* Avoid public or long-lived signed download URLs.
* Verify access again after revocation.

### T5 — Unauthorized Document Deletion

**Threat:** A user attempts to delete a document they do not own.

**Impact:** Data loss or disruption.

**Mitigation:**

* Restrict deletion to document owners.
* Enforce the check on the backend.
* Record denied deletion attempts.

### T6 — Malicious File Upload

**Threat:** An attacker uploads an unsupported or disguised file.

**Impact:** Malicious content, storage abuse, or unsafe file handling.

**Mitigation:**

* Restrict allowed extensions to PDF, PNG, JPG, JPEG, and TXT.
* Validate basic file signatures.
* Apply a 10 MB maximum upload size.
* Generate random storage identifiers.
* Keep uploaded documents in private server-side storage.

### T7 — Audit Log Tampering

**Threat:** An attacker attempts to modify or delete audit records.

**Impact:** Security investigations and accountability could be compromised.

**Mitigation:**

* Generate SHA-256 hashes for audit entries.
* Link each entry to the previous entry's hash.
* Verify the audit chain.
* Use SQLite triggers in the test environment to prevent ordinary UPDATE and DELETE operations against audit records.
* Restrict audit activity viewing to administrators.

**Limitation:** Hash chaining and SQLite triggers provide tamper detection and protection against ordinary application-level modifications. They do not provide absolute immutability against a privileged database administrator who can rewrite the database or bypass triggers.

### T8 — Unauthorized Audit Log Access

**Threat:** A normal viewer attempts to inspect administrative activity records.

**Impact:** Exposure of sensitive operational information.

**Mitigation:**

* Require authentication.
* Verify that the requesting account has the administrator role.
* Return HTTP 403 for unauthorized users.

### T9 — Authentication Attacks

**Threat:** Attackers attempt account compromise through weak passwords or unauthorized API requests.

**Impact:** Unauthorized account access.

**Mitigation:**

* Hash passwords using bcrypt.
* Require passwords of at least 12 characters during registration.
* Use JWT authentication for protected routes.
* Keep access tokens short-lived.
* Store signing secrets in deployment environment variables.

### T10 — Database and Storage Exposure

**Threat:** Attackers attempt to access database credentials or private uploaded files.

**Impact:** Exposure or loss of application data.

**Mitigation:**

* Keep secrets outside source control.
* Use environment variables for production configuration.
* Exclude local databases, private uploads, and environment files from Git.
* Validate storage paths before file operations.
* Use private server-side storage.

## 5. Security Testing Strategy

The automated test suite checks:

* Unauthenticated document access.
* Unauthorized metadata access.
* Unauthorized downloads.
* Unauthorized deletion.
* Unauthorized permission grants and revocations.
* Permission revocation enforcement.
* Document ownership isolation.
* Shared document access.
* Invalid permission values.
* Audit-chain integrity.
* Audit-chain tampering detection.
* Administrator-only activity access.

The reported test result during development was **24 passing tests**.

Security tests should be rerun after changes to authentication, permissions, document routes, or audit functionality.

## 6. Residual Risks and Limitations

1. The current audit hash chain is tamper-evident, not absolutely immutable against privileged database access.
2. Audit logging and business operations are not guaranteed to be one atomic transaction in the current implementation.
3. Concurrent audit writes may require additional synchronization to prevent chain inconsistencies.
4. Render's free filesystem is ephemeral. Uploaded files may disappear after service restarts or redeployments.
5. Production storage durability requires persistent storage or an external object-storage solution.
6. Rate limiting and advanced brute-force protection require additional implementation and verification.
7. Production deployment secrets must be rotated if exposed and kept private.

## 7. Security Priorities

The most important security requirement is that authorization must be enforced on the backend for every protected document operation.

Hiding a button in React is not authorization.

Even if a user manually constructs an HTTP request, changes a document ID, or calls an endpoint directly, the backend must independently verify their identity and permissions.

**TrustVault follows a deny-by-default approach: access is granted only when the authenticated user has the required ownership or permission.**

