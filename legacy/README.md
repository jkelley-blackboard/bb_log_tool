# Legacy: convertlogs.py

`convertlogs.py` is Blackboard's officially supported command-line script for decompressing and converting downloaded Blackboard log packages into readable text. It's vendored here (and also embedded in `streamlit_app/modules/`) for use without the Streamlit app — e.g. on a machine where you'd rather not install Streamlit, or to script the conversion step directly.

For the full walkthrough — finding logs in the Content Collection, UTC/timestamp gotchas, downloading, what each log file means — see **[docs/blackboard-logs-guide.md](../docs/blackboard-logs-guide.md)**. This README only covers running the script itself.

## Usage

1. Create an empty output folder. The script refuses to run if it doesn't exist or already has files in it.
2. Run:

   ```bash
   python convertlogs.py -f <input_folder> -o <empty_output_folder>
   ```

   - `-f` — folder containing your downloaded `.gz`/`.txt` log files
   - `-o` — empty folder to write converted logs into
   - `-t json` — optional, writes full JSON objects (with `@timestamp`, `host`, etc.) instead of flat text

`run_me.bat` is a convenience wrapper around the same command, assuming `log_packages_IN` and `text_logs_OUT` sibling folders:

```bat
python convertlogs.py -f log_packages_IN -o text_logs_OUT
```

> **The original `.gz` files are deleted during conversion.** Work on a copy of your downloads if you need to preserve the originals.

## convertlogs_patched.py

`convertlogs.py` above is left untouched as the unmodified copy Blackboard distributes. `convertlogs_patched.py` is a fork of it with these fixes and additions:

- `decompress_logs()` used `path.rstrip('.gz')` to drop the `.gz` suffix, which strips trailing `g`/`z`/`.` characters rather than the suffix itself — harmless for normal Blackboard filenames, but silently truncates anything else ending in those characters. Fixed to slice off the literal suffix.
- `convert_file()` caught all exceptions around JSON parsing, which meant a parsed entry missing an expected field (`host`, `path`, `message`) would be silently dropped instead of surfacing as an error. Narrowed to only swallow `json.JSONDecodeError` (expected when a log entry spans multiple lines).
- `-t`/`--output_type` now validates against `flat`/`json` (`choices=`) instead of silently treating any unrecognized value as flat output.
- The script now exits with status `1` when precondition checks fail (e.g. output folder not empty), instead of printing an error but exiting `0`. Lets calling scripts/scheduled tasks detect failure.
- Added `-k`/`--keep-originals` to skip deleting source `.gz` files after decompression — use this if you'd rather not work on a throwaway copy of your downloads.

Use `convertlogs_patched.py` in place of `convertlogs.py` with the same `-f`/`-o`/`-t` arguments if you want these fixes. `runme_patched.bat` is the equivalent of `run_me.bat` for the patched script:

```bat
python convertlogs_patched.py -f log_packages_IN -o text_logs_OUT
```

> Edit `runme_patched.bat` to add `-k` if you want it to keep source `.gz` files by default.
