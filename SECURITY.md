# Security Policy

DIOS handles technical drawings, measurement evidence, derived quantities, revision identity, and future external CAD application bridges. Errors can affect confidential project data as well as technical decisions, so source integrity and controlled mutation are both security concerns.

## Reporting

Do not publish real customer drawings, project identifiers, credentials, private CAD files, private application sessions, proprietary project outputs, or a working exploit in a public issue. Prefer GitHub private vulnerability reporting when available; otherwise request a private contact channel through the maintainer profile.

## High-sensitivity areas

- confidential drawing/project-file disclosure;
- revision or source-authority confusion;
- incorrect scale, unit, geometry, or quantity interpretation;
- malicious PDFs, CAD files, embedded content, or parser inputs;
- dependency/parser/tool supply-chain compromise;
- uncontrolled CAD application mutation or macro execution;
- prompt/source injection from imported documents;
- secrets and connector credentials;
- false-positive verification of measurements or external application actions.

## Mutation boundary

Public DIOS code and CI do not authorize live CAD mutations. Application bridges should remain read-only first and expose typed, bounded operations only after explicit review. Original project files and private runtime sessions remain outside this repository.

## Evidence integrity

Measurements and quantities must preserve source references, revision identity, data class, verification status, assumptions/conflicts, and review state. Ambiguity must fail closed to review rather than be silently converted into verified data.
