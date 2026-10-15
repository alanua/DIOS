# Full-surface CAD provider capability registry — source-only prototype

**Status: not a native CAD plug-in, not approved for installation.** Canonical requirement: every publicly documented operation exposed by an installed CAD application's native APIs should be independently discoverable and callable within an operator-approved CAD workspace, subject to version, module, licensing, and security boundaries.

The contract deliberately **does not hardcode six generic CAD actions**. At host boot, a trusted provider plug-in (once implemented and enrolled) must register an extensible catalog of named operations, argument schemas, version/module requirements, effects and trusted native handler implementations. The source-only registry validates catalog structure but cannot authenticate native provider provenance itself. The assistant discovers *availability* before planning multi-step CAD work. No request can register a native handler, select arbitrary Python methods/COM classes, execute OS commands or request arbitrary file paths.

Provider examples: SOLIDWORKS COM/.NET add-in for parts, sketches, features, assemblies, drawings, BOM, material/configuration/equation/simulation interfaces where installed; AutoCAD managed .NET/ObjectARX, ActiveX/COM and documented AutoLISP for document/database, drafting, layers, annotation, 3D geometry and discipline add-ins. "Everything" is limited by the actual vendor API, installed modules, license and validated support; unsupported or GUI-only controls must be reported as such, not claimed.

A `FULL_CAD_WORKSPACE` lease is *session scoped*; it avoids repeated consent prompts for every ordinary CAD operation inside the authorized workspace. **Without a registered `trusted_admission` callback, all handler execution is denied**, even with a full-workspace lease. A real callback must be backed by the canonical signed Skeleton Gate and verify exact request, node/application/workspace/lease binding, policy and command journal. A lambda returning True is used only by synthetic tests; it provides NO real protection and must never be used on a workstation. This library cannot issue or verify a real operator-issued proof by itself. Operations that affect systems outside the workspace (secrets, arbitrary shell/network, licensing, security, deployment, client data export) remain forbidden without separate explicit authorization.

The callable handlers in this prototype are only **synthetic** Python functions. They have no native application integration. The coverage report distinguishes `registered_handlers` (including synthetic callbacks) from `native_bound` and `provider_verified` (both **zero** until separately proven by native integration). There is no installer, local background service, credentials, or vendor SDK code here. Actual automatic workflows require registered provider handlers, typed results, transaction-aware retry, validated crash recovery and cancellation.

To test in DIOS checkout with its existing `src/dios` module layout:

```
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Privacy: include only redacted aggregate capability counts in GitHub; CAD files, filenames, property values, device identity, licensing and customer information stay in private local workstation scope. This proposal must pass separate architecture review against PR #34/#35/#50 and Skeleton #4785/#4786 before any merge or deployment.

## Source-only manifest ingestion

`CapabilityRouter.from_manifest(...)` validates exact manifest fields, typed arguments,
version boundaries, installed-module declarations and a bounded operation count.
The schema resides in `schemas/cad_provider_capabilities.schema.json`
(Draft 2020-12). **Neither a manifest nor a handler mapping may come directly
from untrusted CAD documents, user chat messages or plugin search results.**
The control plane must independently verify installed provider identity, native
module/license state and signed manifest provenance before binding a handler.
No arbitrary import, method reflection or code execution is performed by the
registry.

Operation IDs follow `provider-family.module.action` (for example,
`solidworks.parts.feature_extrude`); the separately attested provider instance
(for example `solidworks.desktop`) must belong to that family. The catalog
reports version/module availability, but *available* is not *natively verified*.

Validation on the Python 3.11-compatible standard-library test runner:

```
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/dios/provider_capabilities.py tests/test_provider_capabilities.py
```

Security and release boundary: this change includes no real SOLIDWORKS COM/.NET
or AutoCAD .NET/ObjectARX adapter, no server-side signing, no outbound device
transport, no ACL installer, no third-party CAD dependencies, and no live CAD
operations. Real providers require separate private conformance tests with
disposable drawings. `DO_NOT_DEPLOY` until then.
