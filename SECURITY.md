# Security Policy

Thank you for helping keep the **Hub for TIBCO Flogo®** and its community safe.

This repository contains **illustrative samples, demos, and Claude Code skills** for
TIBCO Flogo® Enterprise. The code here is provided **as-is**, for learning and
demonstration purposes. It is not a supported product, and the samples are not
intended to be deployed to production without review and hardening.

If you have purchased commercial support for TIBCO Flogo®, product security issues
in the shipping product should be raised through your TIBCO Support entitlement at
[https://support.tibco.com/](https://support.tibco.com/). This policy covers the
**contents of this repository** only.

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities **privately** using GitHub's built-in private reporting:

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability** (this opens a private GitHub Security Advisory).
3. Provide as much detail as you can:
   - A description of the issue and its potential impact.
   - The file(s), sample, demo, or skill affected.
   - Step-by-step instructions to reproduce.
   - Any suggested remediation, if you have one.

If you are unable to use GitHub's private advisory feature, you may contact the
maintainers directly at **<security-contact@example.com>**
*(maintainers: replace this placeholder with your monitored security contact address).*

We will acknowledge your report, keep you updated on our progress, and coordinate a
disclosure timeline with you. Please give us a reasonable amount of time to
investigate and remediate before any public disclosure.

---

## Credentials, Secrets, and Sample Data

All sample and demo applications in this repository ship with **placeholder
credentials only**. You will see values such as:

- `SECRET:YOURKEY`
- `sk-REPLACE-WITH-YOUR-OPENAI-KEY`
- `SET_YOUR_...`

These are **intentional placeholders**, not real secrets. To run any sample you
**must supply your own credentials** via **App Properties**, **environment
variables**, or your platform's secret-management mechanism.

**Never commit real secrets, credentials, API keys, tokens, connection strings,
or customer data to this repository** — in samples, demos, skills, tests, or
documentation.

If you discover a **real credential that appears to have been committed by
mistake**, please **report it privately** using the process above rather than
opening a public issue. The maintainers will treat it as a security incident,
remove it from the codebase, and arrange for the exposed credential to be
**rotated/revoked**.

---

## Supported Scope

- This repository is a collection of **illustrative samples and demos**, provided
  **as-is** with no warranty (see [`LICENSE`](./LICENSE), Apache-2.0).
- There is no formal "supported versions" matrix; fixes are applied to the current
  `master` branch.
- Security reports about the samples, demos, and skills in this repository are
  welcome and will be addressed on a best-effort basis.

Thank you for contributing to the security of the Flogo® community.
