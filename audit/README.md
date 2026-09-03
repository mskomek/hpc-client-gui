# GUI audit evidence

This directory contains reproducible validation notes for the Qt reference
screens and the current wx migration screens. The screenshots use disposable
mock data; they are not packaged or real-cluster evidence.

- English guide: [`docs/wiki/GUI-Feature-Guide.md`](../docs/wiki/GUI-Feature-Guide.md)
- Turkish guide: [`docs/wiki/GUI-Feature-Guide-TR.md`](../docs/wiki/GUI-Feature-Guide-TR.md)
- Qt screenshots: [`screenshots/qt/`](screenshots/qt/)
- wx screenshots: [`screenshots/wx/`](screenshots/wx/)
- Test record: [`test-results.md`](test-results.md)

The mock cluster tests use loopback-only, disposable SSH/SFTP/Slurm data. No
credentials, real cluster, or `.tmp/` content is used.
