# Adding a cluster provider

The shortest successful path is a small declarative provider profile. Provider
packages belong in the [plugin repository](https://github.com/mskomek/hpc-client-gui-plugins),
not in application source code.

1. Copy the repository's minimal provider template.
2. Set the provider ID, profile ID, display name, supported scheduler, and
   minimum app version required by the template format.
3. Add only verified paths, Slurm defaults, and public help links.
4. Leave quota and other unavailable fields blank or disabled.
5. Validate and package the complete profile, README, and manifest.
6. Open a registry pull request with the generated package and validation results.

## Optional quota

Quota is not required for a usable provider. A missing, null, empty, or
whitespace-only quota command means no quota request, probe, timer, retry, or
fallback filesystem scan. Known paths and help text remain available.

Only a reviewed backend with a safe command contract can provide live quota
data. Do not copy a command from another cluster, add credentials, run shell
hooks, parse login banners, or use `df`, `du`, `find`, or an invented fallback.

## What belongs in a public profile

- provider and profile identity;
- scheduler command templates and non-secret defaults;
- known home, scratch, project, or custom paths;
- queue/account guidance and software notes;
- public documentation and support links;
- optional storage policy notes, clearly marked when unknown.

Keep usernames, account grants, passwords, private endpoints, VPN settings,
measured usage, and live account observations in local settings or private
documentation. A provider package describes site defaults; it does not create
directories or promise institutional endorsement.

## Validation checklist

- Validate the minimal example with no quota fields.
- Validate the full example with optional sections blank or disabled.
- Check placeholder syntax and public URLs.
- Confirm every manifest file has the computed size and SHA-256 hash.
- Confirm the package does not alter an existing published version directory.
- Test loading the provider without a cluster connection; validation must not
  contact a remote host.

For application failures, use the [application issue chooser](https://github.com/mskomek/hpc-client-gui/issues/new/choose).
For provider content or registry requests, use the [plugin repository](https://github.com/mskomek/hpc-client-gui-plugins/issues/new/choose).
