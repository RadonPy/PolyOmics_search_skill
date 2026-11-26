# Release checklist

- [ ] Run the offline suite and validate standalone, portable, and workspace profile contents.
- [ ] Rebuild the tracked ZIPs twice and compare their hashes. Run the English text and link check on source and package content.
- [ ] Run strict checks against all eight public MCP tools and compare the five MD input schemas with the baseline.
- [ ] Open the feature PR and check its remote commit and CI status.
- [ ] Register or verify the intended cloud app and run the full [Web checks](web-compatibility.md#web-acceptance) with an eligible user.
- [ ] Run a representative portable workflow on a compatible desktop host.

Public directory submission is a separate approval path. Verify the published listing before reporting directory availability. [Public review checklist](public-submission.md)
