# Spill Ledger

Search the federal ship-source pollution compensation report by vessel, harbour, date, province or file status, then follow the financial steps for one incident.

[Open Spill Ledger](https://coolcode.ca/spillledger/)

## Try it

<!-- coolcode:guide -->
The June 2015 Farley Mowat incident in Shelburne has separate claims by the town and the Canadian Coast Guard. Select the incident to compare the amounts submitted and offered, alongside the shared recovery entry.
<!-- /coolcode:guide -->

## Sources and interpretation

The 2023–24 Ship-source Oil Pollution Fund annual report’s general-process table includes 81 incidents in British Columbia and Nova Scotia in this edition. The incident dates can predate the fiscal year by many years. Status, offers and recovery are as recorded in this edition of the report. The selection excludes the separate streamlined-claims table. It covers the fund’s cases, including preventive responses, so its counts cannot measure all spills in a harbour.

The importer reads the table geometry on PDF pages 63–76. It preserves multi-claim incidents, the claimant, decision and recovery text, and the original PDF page. A dash means that the publisher left that stage without an entry. For the February 2015 Cormorant incident in Bridgewater, the report lists $549,581.18 claimed, $515,267.25 offered and $375,000 recovered. Each belongs to a different financial stage.

[Fund’s 2023–24 annual report, claims appendix](https://ship-rail.gc.ca/sites/default/files/2025-09/ship_fund_-_2023-2024_annual_report.pdf#page=63)

## Refresh and verification

Monthly. Install the pinned PDF-table reader with `python3 -m pip install -r scripts/requirements.txt` for extraction. The retrieval date records the last successful source check in UTC. The coverage on the homepage and in the tool describes the underlying records. A changed archive requiring review or a failed download leaves the previous edition available. The scheduled workflow validates the data, runs the tests and publishes the resulting snapshot. For a manual refresh, run `python3 scripts/refresh.py`.

The interface, selections and CSV exports run locally in the browser. Visiting a source or map link opens the publisher’s site. The offline build uses the checked-in edition. To build and preview it, run the following commands.

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

The Pages workflow also exercises the tool in Chromium at its project subpath and checks the mobile layout. Update the source sentence in `tool.json` and the marked guide above when changing coverage or interpretation.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
