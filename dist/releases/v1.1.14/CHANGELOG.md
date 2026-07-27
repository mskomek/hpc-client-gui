## v1.1.14
- Transfers: when uploading or downloading a selected folder into an existing
  folder of the same name, merge the folders and ask only about conflicting
  nested files; preserve the complete subfolder hierarchy in both directions.
- Transfers: an overwrite now deletes each conflicting target immediately
  before its own upload or download, rather than deleting all conflicts first.
- Local files: fixed a Delete-key crash caused by debug telemetry converting a
  Qt keyboard-modifier flag incorrectly.

