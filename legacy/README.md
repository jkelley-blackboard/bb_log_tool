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
