# Viewing Converted JSON Log Output

This page is a companion to the main [Blackboard logs guide](./blackboard-logs-guide.md). It covers how to get from a downloaded `.log.gz` package to something browsable in a plain JSON viewer — including the one format gotcha that trips people up.

## The format, in short

Downloaded logs from the Content Collection arrive as `.log.gz` files, organized by year/month/day/hour. They are **not** already JSON-viewer-ready — two things have to happen first:

1. **Decompress.** `convertlogs.py` does this automatically as part of conversion (and deletes the original `.gz` files when it does — see the gotcha below).
2. **Convert to a single JSON document per host.** Run the script in JSON mode:
   ```bash
   python3 convertlogs.py -f ~/Downloads/Logs -o ~/LearnLogs -t json
   ```
   This produces one `logs.json` per server node (e.g. `LearnLogs/10.0.1.5/logs.json`), containing the full event objects (`@timestamp`, `host`, `message`, etc.), not just plain text lines.

**This `logs.json` output is what a JSON viewer actually wants.** The raw decompressed `.log` file underneath is *newline-delimited JSON* — many separate JSON objects one after another, some spanning multiple lines — not a single JSON document with one root. Tree-view viewers like Dadroit and Janice expect one root object or array, so pointing them at a raw decompressed `.log` file directly (skipping the `-t json` conversion step) will often fail to parse or show only the first record.

## Recommended tools

**[Dadroit JSON Viewer](https://dadroit.com/)** — start here.
Free desktop app (Windows/Mac/Linux). Open the `logs.json` file, get a collapsible tree view, and use the built-in search to find keys or values (e.g. a username in `message`, or a specific `@timestamp` range). No install issues, no command line, no SQL. The easiest option for a non-technical admin to use unsupervised.

**[Janice](https://github.com/ErikKalkoken/janice)** — no-install backup.
Free, open-source, ships as a single executable — no installer, just download and run. Same tree-view browsing model as Dadroit, with search across keys/values (including wildcards). Good option if Dadroit can't be installed on a locked-down machine.

**[Pandia](https://www.pandia.app/large-json-viewer)** — for unusually large files.
Free, native, offline viewer built to open very large JSON (hundreds of MB to multi-GB) without freezing. Only needed if a `logs.json` file comes back much larger than a typical day's worth of logs for one node.

## Gotchas to watch for

**The original `.gz` files get deleted.** `convertlogs.py`'s decompression step removes the source `.gz` files once it's done with them — this is expected behavior, not a bug. Always run the script against a copy of your downloads if you want to keep the originals.

**Flat mode vs. JSON mode produce different output.** The default (flat file) mode writes only the `message` field as plain text, recreating the server's folder structure — good for `grep`/Notepad++ search, but not something a JSON viewer needs or benefits from. Only the `-t json` output (`logs.json`) is meant for a JSON viewer. If someone hands you flat-mode output and asks why it won't open in Dadroit, that's why — it's plain text by design, not JSON.

**Silent JSON parse failures during conversion.** The converter skips malformed or corrupted entries silently. If a `logs.json` file looks sparse compared to what you expected, it's worth checking whether the source `.log` file was intact before assuming the JSON viewer is at fault.
