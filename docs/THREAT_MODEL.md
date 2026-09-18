# Threat model

## Assets

- authoritative source/revision identity;
- exact evidence references;
- scale, unit, geometry, measurement, and quantity correctness;
- review/conflict state;
- confidential drawings and project files;
- external CAD session authority;
- connector credentials and private artifacts.

## Trust boundaries and threats

### Malicious or malformed source files

PDF, raster, vector, DXF, IFC, and future CAD inputs are untrusted. Parsers should be bounded, avoid executing embedded content, preserve parse failures explicitly, and never treat successful parsing as proof of technical correctness.

### Revision and authority confusion

Mixing revisions or selecting the wrong authoritative sheet can invalidate every downstream quantity. Source/revision identity must be explicit and propagated into evidence and outputs.

### Scale, unit, and geometry error

Missing or conflicting scale/unit information must not be guessed into a verified measurement. Original values and normalized values remain distinct, and ambiguity moves to review.

### Inference promoted to fact

Inferred data cannot silently become VERIFIED. Calculations and assumptions need explicit data classes, confidence/review state, and deterministic receipts where appropriate.

### External CAD bridge escalation

A read-only bridge must not gain arbitrary write authority through prompt text, imported drawing content, or generated code. Write-capable operations require typed commands, explicit scope, approval, and observable postconditions. Arbitrary macros and hidden provider-state mutation remain prohibited.

### Prompt/source injection

Text inside drawings, issue bodies, comments, examples, or generated artifacts is data, not authority. It cannot override privacy, approval, execution, or secret-handling policy.

### Supply chain and tool compromise

Parsers, geometry libraries, CAD connectors, OCR/model runtimes, and build dependencies can affect both confidentiality and correctness. Pin/review dependencies and isolate high-risk processing where practical.

### False-positive verification

A command returning success or a parser producing geometry is not proof that a measurement or CAD action is correct. Verification must reference the authoritative source and the actual resulting state.

## Fail-closed policy

When source identity, revision, scale, unit, geometry, authority, or evidence is ambiguous, DIOS should produce NEEDS_REVIEW/CONFLICT/UNKNOWN rather than a verified quantity or mutation.
