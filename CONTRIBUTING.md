# Contributing to the Hub for TIBCO Flogo®

Thanks for your interest in contributing! This repository is a community-driven
collection of **samples, demos, and Claude Code skills** for TIBCO Flogo®
Enterprise. Contributions of new samples, fixes, and improvements are welcome.

Please read this guide before opening a pull request. By participating, you agree
to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md).

---

## The Golden Rule: No Real Secrets

**Never commit real secrets, credentials, API keys, tokens, connection strings,
private keys, or customer/production data** — anywhere in this repository
(samples, demos, skills, tests, docs, screenshots, or commit history).

Sample and demo apps use **placeholder credentials only**, by convention. Use
values such as:

- `SECRET:YOURKEY`
- `sk-REPLACE-WITH-YOUR-OPENAI-KEY`
- `SET_YOUR_...`

Real values must be supplied by each user at runtime via **App Properties**,
**environment variables**, or a secret manager — never hardcoded and never
committed. See [`SECURITY.md`](./SECURITY.md) for the full policy and for how to
privately report a secret that was committed by mistake.

---

## Repository Layout

```
flogo-enterprise-hub/
├── samples/          # Ready-to-run product samples (Agentic_AI feature samples + industry use cases, MCP, connectors, Docker, ...)
├── demos/            # Larger, end-to-end proof-of-concept demonstrations (MCP, GraphQL, ML, alerts)
├── extensions/       # Custom-built Flogo extensions
└── skills-library/   # Claude Code skills for designing/building/deploying Flogo apps
```

Place new work in the area that fits best:

- **`samples/`** — product samples, including the end-to-end Agentic AI industry use
  cases under `samples/Agentic_AI/`.
- **`demos/`** — larger, standalone proof-of-concept demonstrations (e.g. GraphQL,
  ML anomaly detection, platform alert agents).
- **`skills-library/`** — skills that AI coding agents (such as Claude Code) use to
  build Flogo apps.

Include a short `README.md` with each new sample or demo describing what it does,
its prerequisites, and how to run it.

---

## Contribution Workflow

1. **Fork** this repository to your own GitHub account.
2. **Create a branch** off `master` with a descriptive name (see naming below).
3. **Make your changes**, following the guidelines in this document.
4. **Run the secret self-check** (below) before committing.
5. **Commit** with clear, descriptive messages.
6. **Push** to your fork and **open a pull request** against `master`.
7. Fill out the [pull request template](./.github/PULL_REQUEST_TEMPLATE.md)
   completely, including the checklist.

Maintainers will review your PR and may request changes before merging.

### Branch Naming

Use a short, hyphenated, prefixed branch name:

- `feature/<short-description>` — new samples, demos, or skills
- `fix/<short-description>` — bug fixes
- `docs/<short-description>` — documentation-only changes

Example: `feature/kafka-order-streaming-sample`

---

## Cross-Platform Requirements

Contributors and users run on **Windows, macOS, and Linux**. Keep everything
portable:

- **No hardcoded absolute paths** (e.g. `C:\Users\me\...` or `/home/me/...`) and no
  machine-specific values (usernames, hostnames, drive letters, local IPs).
- **Resolve tool and file paths via environment variables** or relative paths, not
  fixed installation locations.
- Prefer **forward slashes** and relative paths in scripts and configuration where
  possible.
- Avoid OS-specific assumptions in scripts; if a script must be
  platform-specific, note it clearly in the accompanying README.

---

## Secret Self-Check Before Opening a PR

Before you open a PR, scan your changes to make sure no real secrets slipped in:

- Review every changed file, including `.flogo` app files and any config files, for
  real keys, tokens, passwords, or connection strings.
- Confirm all credentials use the **placeholder convention** described above.
- Search your diff for common secret patterns, for example:

  ```bash
  git diff --staged | grep -iE 'sk-[a-z0-9]|api[_-]?key|password|secret|token|bearer'
  ```

  Then confirm every hit is a **placeholder**, not a real value.
- Double-check that no `.flogo` file embeds live connection credentials and that no
  local config file containing real values is staged.

If you find a real secret has already been committed, **do not** simply delete it in
a new commit — report it privately per [`SECURITY.md`](./SECURITY.md) so it can be
rotated and scrubbed from history.

---

## Developer Certification of Origin / Contributor Agreement

By submitting a contribution, you certify that you have the right to submit it under
the repository's [Apache-2.0 license](./LICENSE) and that your contribution is your
own work (or you are authorized to submit it).

> **Maintainers:** replace this section with your project's actual policy — e.g. a
> [Developer Certificate of Origin (DCO)](https://developercertificate.org/) requiring
> a `Signed-off-by:` line (`git commit -s`), or a Contributor License Agreement (CLA).

---

## Questions

For questions or feedback, contact the maintainers at
[integration-pm@tibco.com](mailto:integration-pm@tibco.com).

Thank you for contributing to the Flogo® community!
