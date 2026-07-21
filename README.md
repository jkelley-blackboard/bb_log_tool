# Blackboard Log Tool (bb_log_tool)

Tools and guidance for downloading, converting, and analyzing Blackboard session/application logs.

## Repository Layout

```
streamlit_app/   Streamlit app for downloading, converting, and analyzing logs.
                 See streamlit_app/README.md for setup, usage, and troubleshooting.

legacy/          Blackboard's officially supported convertlogs.py CLI script, for
                 converting logs without the Streamlit app. See legacy/README.md.

docs/            Practitioner guide to Blackboard logs: where they live, timestamp/UTC
                 gotchas, and what each log file means. See docs/blackboard-logs-guide.md.
                 docs/viewing-raw-json.md is a companion guide covering how to view
                 convertlogs.py's JSON-mode output in a JSON tree viewer.
```
