# Security Policy

## Trust boundaries

Downloaded plugins are data, not code; executable legacy plugins are disabled.
Application-owned code builds allowlisted scheduler operations. Credentials are
redacted before logging or diagnostics export, and unknown/binary diagnostic
files are skipped. Third-party tools are opened through their official download
pages rather than automatically downloaded and executed. Automatic application
updates require Ed25519-signed metadata rooted in an embedded public key.

CI keeps `pip-audit` and runs a focused security regression group. Bandit was
evaluated for this wave but not added: broad subprocess warnings overlap the
intentional SSH and packaging process boundaries and would require noisy global
suppressions; targeted fail-closed tests cover the changed trust boundaries.

## Supported versions

Only the latest published release receives security fixes. Older releases should be upgraded before reporting a suspected issue.

## Confidential reporting

Please use GitHub's **Private Vulnerability Reporting** for this repository. Open the repository's Security tab and choose **Report a vulnerability**. Do not disclose an uncoordinated vulnerability in a public issue, discussion, pull request, or social post.

## What to include

- affected version and operating system
- a concise impact description
- safe reproduction steps using mock or disposable data
- relevant logs with credentials, tokens, hosts, and personal data removed
- a suggested mitigation, if known

Please do not attach secrets or real cluster credentials. We will acknowledge receipt through the private GitHub report and coordinate remediation there; no response-time, reward, or legal safe-harbor commitment is made by this policy.
