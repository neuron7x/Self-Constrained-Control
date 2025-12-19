# Security Policy

This project is a simulation + orchestration scaffold.

## Reporting Security Issues

If you discover a security issue:
- Do **not** open a public issue with exploit details.
- Open a private report via repository security advisories (preferred), or contact the maintainer.

## Security Scope

- Supply chain (dependency pinning, integrity)
- Unsafe deserialization / state persistence
- Arbitrary code execution via configuration, scripts, or plugins

## GitHub Actions Security Controls

This repository implements the following security controls for CI/CD:

### Permissions (Principle of Least Privilege)

- **Default `GITHUB_TOKEN` permissions**: `contents: read` only
- **Job-level permissions**: Explicitly defined per workflow/job
- **No write access by default**: Write permissions granted only when required

### Supply Chain Security

- **SHA Pinning**: All GitHub Actions are pinned to full commit SHA
- **Dependency Review**: Automated scanning for vulnerable dependencies in PRs
- **Dependabot**: Automated security updates for dependencies
- **CodeQL Analysis**: Static security analysis for code vulnerabilities

### Secret Protection

- **Fork PR restrictions**: Workflows with secrets do not run on fork PRs
- **Environment protection**: Use GitHub Environments for production secrets
- **OIDC recommended**: Use OIDC tokens instead of long-lived credentials where possible
- **Secret masking**: Secrets are automatically masked in logs

### Required Status Checks

The following checks must pass before merging to `main`:

- `quality-gate` (CI workflow - lint, type check, tests)
- `dependency-review` (Dependency vulnerability scan)
- `codeql-analysis` (Security static analysis)

## Recommended Branch Protection Rules

Repository administrators should enable the following branch protection rules for `main`:

### Required Settings

- ✅ **Require a pull request before merging**
  - ✅ Require approvals (minimum 1)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from code owners

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - Status checks: `quality-gate`, `Dependency Review`, `Analyze (python)`

- ✅ **Require conversation resolution before merging**

- ✅ **Require signed commits** (if team has GPG keys configured)

- ✅ **Require linear history**

- ✅ **Do not allow bypassing the above settings**

### Recommended Settings

- ✅ **Restrict who can push to matching branches**
- ✅ **Block force pushes**
- ✅ **Require deployments to succeed** (if using environments)

## Self-Hosted Runner Security (If Applicable)

If using self-hosted runners:

- Runners must be isolated (ephemeral/containerized)
- Automatic updates enabled
- Network access restricted
- Only controlled runner labels allowed
- Untrusted workflows blocked

## Artifact and Log Security

- Minimal artifact retention (default: 30 days)
- No secrets in logs (use `add-mask` or environment secrets)
- Regular audit of workflow executions

## Security Scanning Schedule

| Scan Type | Frequency | Trigger |
|-----------|-----------|---------|
| CodeQL | Weekly + on PR | Push, PR, Schedule |
| Dependency Review | On PR | Pull Request |
| Dependabot Alerts | Continuous | Automatic |
| Secret Scanning | Continuous | Automatic (GitHub) |

## Compliance

This security configuration aims to comply with:
- GitHub Security Best Practices
- SLSA Level 2+ supply chain security
- OWASP CI/CD Security Guidelines
