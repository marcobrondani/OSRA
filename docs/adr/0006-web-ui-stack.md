# ADR-0006: Server-rendered web UI, no build step, no external assets

**Status:** Accepted · September 2026
**Context:** The web UI is in v1 and is the main surface for organisations that cannot use an agent. It must work offline and in air-gapped environments, load no external resources, be keyboard accessible, and be maintainable by one person who is not a front-end specialist.

## Decision

Serve HTML rendered by the same Python process, over loopback, with a small amount of hand-written JavaScript for form behaviour. No front-end framework, no bundler, no build step, and every asset shipped inside the package.

## Why

- "No external fonts, scripts or styles" (TR-51) rules out most framework defaults anyway.
- A build step is another toolchain to maintain, and another way for a release to differ from a checkout.
- Server rendering keeps all rules in the engine, so the UI cannot drift into a second implementation (TR-20).
- Accessibility is easier to get right with plain HTML forms than with custom components.

## Alternatives

- **A single-page application with a bundled framework.** Better interactivity. Rejected: a build step, a much larger dependency set, and a strong pull towards duplicating validation in the client.
- **A desktop application.** Better distribution for non-technical users. Rejected: platform packaging work far beyond one maintainer.
- **No UI, terminal only.** Rejected by the product decision to include the UI in v1.

## Consequences

- Interaction is page-based; long register editing needs careful form design rather than rich client state.
- Progressive enhancement is the rule: every action must work without JavaScript. This has a real cost in the scoring screens, where anchors, the effect of a weight change and validation feedback are easier with client-side behaviour; those screens may need more page transitions than a single-page application would.
- The UI ships as part of the same package and version as the engine.
