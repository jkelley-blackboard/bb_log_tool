# Blackboard Log Tool (bb_log_tool)

Tools and guidance for downloading, converting, and analyzing Blackboard session/application logs.

> **Unsupported.** Everything in this repository is provided as-is, without warranty or support of any kind, and is superseded by official Blackboard/Anthology product documentation and your institution's support agreements. See [LICENSE](LICENSE).

## Repository Layout

- **[streamlit_app/](streamlit_app/)** — Streamlit app for downloading, converting, and analyzing logs. See [streamlit_app/README.md](streamlit_app/README.md) for setup, usage, and troubleshooting.
- **[legacy/](legacy/)** — Blackboard's officially supported `convertlogs.py` CLI script, for converting logs without the Streamlit app. See [legacy/README.md](legacy/README.md).
- **[docs/](docs/)** — Practitioner guide to Blackboard logs: where they live, timestamp/UTC gotchas, and what each log file means. See [docs/blackboard-logs-guide.md](docs/blackboard-logs-guide.md), plus a companion guide on viewing JSON-mode output at [docs/viewing-raw-json.md](docs/viewing-raw-json.md).
