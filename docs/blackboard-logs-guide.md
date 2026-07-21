# Blackboard Logs: Practitioner Guide

**Script version covered:** `convertlogs.py` v1.3.0

---

## Overview

Blackboard generates application logs on a rolling hourly basis and stores them in the Content Collection. The logs are compressed and require conversion before they are human-readable. This guide covers the full workflow: locating logs, downloading them, converting them, and understanding what each log file contains. For the official platform documentation, see [Logs — Blackboard Administrator Help](https://help.anthology.com/blackboard/administrator/en/system-management/logs.html).

Once converted, the log files are in standard formats that most commercial and open-source log analysis tools can ingest with minimal manipulation. Administrators are encouraged to explore cost-effective log analysis solutions to help better manage and monitor their Blackboard environment. The [Blackboard Community](https://community.anthology.com) is an excellent resource for finding out what tools and approaches other administrators are using.

---

## 1. Finding Logs

There are two ways to reach the log folders:

**Via the System Logs page (recommended for targeted access):**  
Administrator Panel → Tools and Utilities → Logs → System Logs

This page provides a date picker that generates a direct link into the Content Collection at the correct date folder, saving you from manually navigating the folder tree.

**Via the Content Collection directly (for broader browsing):**  
Administrator Panel → Content Management → Manage Content → `internal` → `logs`

The folder hierarchy is organized by year, month, day, and hour:

```
/internal/logs/
  └── YYYY/
        └── MM/
              └── DD/
                    └── HH/
                          └── <filename>.log.gz
```

---

## 2. Understanding Timestamps and the Four-Hour Delay

Two timestamp behaviors trip up most administrators.

**The filename hour is always UTC.** The hour in the filename (`2026.6.23.13...`) is UTC — it marks the *start* of the one-hour collection window. The Content Collection UI shows the file's "Edited" time in local server time. On a US-East server running EDT (UTC-4), a file named `2026.6.23.13...` will show an edited time of approximately 1:29 PM EDT. These are two different clocks on the same file.

To find logs for a specific incident, convert your local time to UTC first. On a UTC-4 server: an incident at 9:00 AM EDT → look for the `13` hour folder (9 + 4 = 13). The file contains data from 13:00–13:59 UTC, which is 9:00–9:59 AM local time.

**Logs arrive on a four-hour delay.** That same file covering 9–10 AM EDT won't appear in the Content Collection until roughly 2:00 PM EDT. In general: add your UTC offset plus four hours to the incident time to estimate when logs will be available. Don't expect to use these logs for real-time monitoring.

---

## 3. Downloading Logs

The simplest way to download logs is directly from the Content Collection UI. Navigate to the date/hour folder, select the files you want, and use the **Download Package** option to receive a zip. Avoid this for large date ranges or high-traffic multi-node deployments — the zip generation can time out or produce an incomplete archive when the volume of files is large.

For bulk or automated retrieval, the Content Collection also exposes logs via WebDAV at `https://<your-institution-domain>/bbcswebdav/internal/logs/`. You can mount this as a network drive (macOS Finder → Connect to Server, Windows → Map Network Drive) for browsing and selective download, or use `wget` or `curl` for scripted pulls. See Appendix A for command-line examples.

Stage all downloaded files into a local folder before running the converter.

---

## 4. Converting Logs

Logs are stored in a compressed format and must be converted to be readable. Blackboard provides `convertlogs.py` for this purpose, available from the System Logs page (Administrator Panel → Tools and Utilities → Logs → System Logs → Download Convert Logs script).

### Prerequisites

- Python 3 must be installed. Download from [python.org](https://www.python.org) if needed.
- Create an empty output folder before running. The script will not run if the output folder doesn't exist or already contains files. Note: the System Logs page states the script will create the output folder automatically — this is not accurate in v1.3.0.

### Running the Script

Open a terminal and run:

```bash
python3 convertlogs.py -f ~/Downloads/Logs -o ~/LearnLogs
```

- `-f` is the folder containing your downloaded log files
- `-o` is the empty folder where converted logs will be written

The script decompresses the `.gz` files, sorts them by date, and writes the output organized by server node. **Note:** the original `.gz` files are deleted during this process. Work on a copy of your downloads if you need to preserve them.

For incidents spanning multiple hours, download all relevant hour folders into the same input directory — the script sorts and processes them chronologically.

**JSON output mode** (for technical users who need full metadata):

```bash
python3 convertlogs.py -f ~/Downloads/Logs -o ~/LearnLogs -t json
```

If you want to browse this JSON output in a GUI tree viewer rather than `jq`/`grep`, see **[docs/viewing-raw-json.md](./viewing-raw-json.md)** — it covers the viewer options and the one format gotcha (newline-delimited JSON vs. a single JSON document) that trips people up.

---

## 5. Reading the Output

After conversion, the output folder is organized by server node IP address, then by the original log file path on the Blackboard server — mirroring how logs appear on the server itself.

```
LearnLogs/
  └── 10.0.1.5/
        └── usr/local/blackboard/logs/
              └── bb-services/
                    └── bb-services-log.txt
```

Standard text search tools work well for finding specific events:

```bash
# Search for a specific username
grep -r "jdoe" ~/LearnLogs/

# Find ERROR-level entries across all logs
grep -r "ERROR" ~/LearnLogs/

# Search within a specific log file type
grep -r "NullPointerException" ~/LearnLogs/ --include="bb-services-log.txt"
```

On Windows, use Notepad++, VS Code, or any text editor that supports folder-wide search.

---

## 6. Log File Overview

The converted output contains logs covering a range of system activity. Full descriptions of each log file are in **Appendix B**.

For most activity forensics investigations — tracing what a specific user did, confirming whether a request reached the server, or identifying the source of an authentication failure — the two most useful logs are:

- **`bb-authentication-log.txt`** — every authentication event: user, outcome, auth provider used, and source IP. Also the durable record for authentication history beyond the ~10-day retention window of the admin UI.
- **`tomcat/bb-access-log.txt`** — every HTTP request made to the server: who, when, what URI, response code, and how long it took.

**Important:** The Authentication Logs and SIS Integration Log interfaces in the admin UI are sourced from the database and have a short retention window — approximately 10 days for authentication events. The log files available via the Content Collection download are retained indefinitely under your institution's own retention policy and are the only durable record for historical investigations.

### Using Logs for User Activity Forensics

When investigating what a specific user did — or whether they were responsible for a particular action — `bb-authentication-log.txt` and `tomcat/bb-access-log.txt` are used together. The authentication log tells you when someone logged in and from where; the access log tells you what they did during that session.

#### bb-authentication-log.txt

Each line is a pipe-delimited authentication event. The fields most useful for investigation are `timestamp`, `evt_name`, `outcome`, `duser` (username), `src_ip`, and `authnmethod`.

A typical entry looks like:

```
timestamp=Sep 04 2025 12:07:01.137 EDT|...|evt_name=session expired|outcome=success|src_ip=|duid=_6_1|duser=jkelley|authnmethod=login page|...
```

Common event names you will encounter: `login`, `logout`, and `session expired` (a normal timeout — not an error). Failed access attempts appear as `unauthorized access` in `bb-security-log.txt` rather than this file.

When investigating a specific user, search for their username in the `duser` field. You can narrow results to a specific date by filtering on the timestamp. To understand whether a user was active on a given day, look for `login` and `session expired` events. To investigate logins from unexpected locations, review the `src_ip` field across their entries — multiple logins from very different IP addresses or geographic locations may warrant further investigation.

#### tomcat/bb-access-log.txt

Each line is a single HTTP request. A typical entry looks like:

```
136.226.107.95 127.0.0.1 connector-46 - [04/Sep/2025:14:23:11 -0400] "GET /webapps/blackboard/execute/announcement?method=search HTTP/1.1" 200 4821 "Mozilla/5.0 ..." "-" 142 4821
```

The access log does not contain usernames — it records IP addresses. To trace a specific user's activity, first identify their source IP from the authentication log, then look for that IP in the access log during the relevant time window.

Key things to focus on when reviewing access log entries:

- **The URI** — identifies what page, course, or API endpoint was accessed
- **The status code** — 200 is success; 403 is access denied; 404 is not found; 500 is a server error
- **The response time** (second-to-last field, in milliseconds) — useful for identifying slow requests during a performance investigation

Note that AWS load balancer health checks to `/webapps/portal/healthCheck` generate a high volume of entries and can be visually noisy when reviewing the log manually. Any log analysis tool should be configured to exclude these when focusing on user activity.


---


## 7. Quick Reference

| Task | How |
|---|---|
| Find logs (targeted) | Admin Panel → Tools and Utilities → Logs → System Logs (use date picker) |
| Find logs (browse) | Admin Panel → Content Management → Manage Content → internal → logs |
| Log availability delay | ~4 hours after the hour closes |
| Filename hour | Always UTC — convert local time: local hour + UTC offset = filename hour |
| UI "Edited" timestamp | Local server time — different clock from the filename |
| Download (one-off) | Content Collection → select files → Download Package |
| Download (bulk) | WebDAV at `/bbcswebdav/internal/logs/` via `wget` or `curl` |
| Convert logs | `python3 convertlogs.py -f <input_folder> -o <empty_output_folder>` |
| Preserve source files | Copy downloads before running — originals are deleted during conversion |
| Search converted output | `grep -r "search term" <output_folder>` |
| Auth log retention (UI) | ~10 days (database-backed) |
| Auth log retention (files) | Indefinite (institution-controlled) |

---



## Appendix A: Technical Reference for Developers

### Log File Format (Raw)

After decompression, each file is a newline-delimited sequence of JSON objects. Each object may span multiple lines and terminates with `}\n`. Standard fields:

| Field | Description |
|---|---|
| `path` | Path on the Blackboard server where the event originated |
| `@timestamp` | ISO 8601 timestamp of the event (UTC) |
| `clientId` | Client/tenant identifier |
| `log` | Log tag/category |
| `host` | IP address of the Blackboard node that generated the event |
| `message` | The actual log content |

Multi-line messages (stack traces are common) are concatenated by the converter before JSON parsing. The script accumulates lines until it sees one ending in `}\n`, then attempts `json.loads()`.

### convertlogs.py Internals

The script processes logs in four steps:

1. **`to_list()`** — Walks the input path and collects all file paths.
2. **`decompress_logs()`** — Gunzips any `.gz` files in-place, then deletes the originals.
3. **`convert()`** — Filters to files with parseable dates, sorts chronologically, converts in order.
4. **`convert_file()`** — Reads the decompressed file, assembles multi-line JSON objects, writes to output.

**Output modes:**

Flat file (default) recreates the Blackboard server directory structure under the output directory, organized by host IP. Only the `message` field is written.

```
output/
  └── 10.0.1.5/
        └── usr/local/blackboard/logs/bb-services/
                  └── bb-services-cached.log
```

JSON mode (`-t json`) writes the full JSON object to a single `logs.json` per host — useful when `@timestamp`, `host`, or other metadata is needed alongside the message.

```
output/
  └── 10.0.1.5/
        └── logs.json
```

**Searching JSON output with jq:**

```bash
# Filter by message content
cat output/10.0.1.5/logs.json | jq 'select(.message | contains("ERROR"))'

# Filter by time range
cat output/10.0.1.5/logs.json | jq 'select(.["@timestamp"] >= "2024-03-15T14:00:00")'
```

### Known Behaviors and Edge Cases

**`.gz` originals are deleted.** `decompress_logs()` removes the source `.gz` after decompression. Always work on a copy of your downloads.

**Silent skip on non-matching filenames.** Any file that doesn't start with `YYYY.MM.DD.HH.` is silently excluded. If a log you expect isn't appearing in output, verify the filename matches the expected pattern.

**`rstrip('.gz')` edge case.** The decompression code uses `compressed.rstrip('.gz')` to produce the decompressed filename. Python's `rstrip()` strips characters, not a suffix — it would also strip trailing `g` and `z` characters from the base name. In practice Blackboard log filenames always end in `.log.gz` so this produces `.log` correctly, but non-standard filenames could be affected.

**Silent JSON parse failures.** The converter catches all exceptions silently when JSON parsing fails. Malformed or corrupted entries are skipped without any error output. If output seems sparse, check whether the source file is intact.

**Output directory must exist and be empty.** The `check_preconditions()` check requires the directory to exist and be empty. The System Logs UI page states the script creates the folder automatically — this is inaccurate in v1.3.0.

**File handles stay open until completion.** `FileWriter` keeps all output files open for the duration of the run. For very large log sets with many unique paths, this could approach OS file descriptor limits. Process one day's logs at a time if this occurs.


---


## Appendix B: Log File Descriptions

### Core Application Logs

**`bb-services-log.txt`**  
The primary application log. The most common entries are routine autoscaling metrics — these `[WARNING]` lines are expected background noise, not actual warnings. Genuine application errors, integration failures, and stack traces appear here as well. This is the first log to check for general application errors and usually the first one Blackboard Support will ask for.

**`bb-authentication-log.txt`**  
Authentication events. Records login attempts, session expirations, auth provider used, outcome (success/failure), source IP, and username. First place to look for login issues, lockouts, or IdP problems. Also the durable record for authentication history beyond the ~10-day UI retention window.

**`bb-security-log.txt`**  
Security events. Covers unauthorized access attempts, input validation failures, and other security-layer events. Useful for identifying scanning or probing activity and distinguishing automated attacks from legitimate usage errors. Entries include the offending request details and full stack traces.

**`bb-schema-log.txt`**  
Database schema operations. Records DDL executed against the database during application startup and patch application. Primarily relevant when investigating upgrade failures or startup errors. Small and largely static under normal operation.

**`bbcms_log.txt`**  
Content Management System (Xythos) events. Covers Content Collection file system operations. Stack traces here are often benign transaction boundary warnings rather than true errors. Relevant when investigating Content Collection access issues or file operation failures.

### Tomcat Logs

**`tomcat/bb-access-log.txt`**  
HTTP access log. One line per request: client IP, timestamp, HTTP method, URI, response code, and response time. The most useful log for performance investigation and activity forensics — identify slow endpoints, confirm whether requests reached the server, and spot 4xx/5xx spikes. AWS ELB health checks generate significant volume and can be filtered out when searching for user traffic.

**`tomcat/bb-remote-admin-access-log.txt`**  
Access log for the Xythos Content Collection administration interface. Traffic here is internal infrastructure. Useful for confirming that the CMS subsystem is communicating normally.

**`tomcat/catalina-log.txt`**  
Tomcat container log. Covers JVM-level events and the Blackboard notifications service WebSocket connection lifecycle. Periodic disconnect/reconnect cycles for the notifications service are normal. Relevant for diagnosing Tomcat startup failures or notification service connectivity issues.

**`tomcat/stdout-stderr-YYYYMMDD.log`**  
JVM output. In normal operation dominated by ELB health check responses. Errors that bypass the application logging framework appear here — useful as a catch-all when errors aren't appearing in the application logs.

**`tomcat/gc.log`**  
JVM garbage collection log. Not useful for most troubleshooting, but relevant when diagnosing memory pressure or performance degradation correlated with heap exhaustion.

### Infrastructure Logs

**`activemq-broker/activemq-broker-log.txt`**  
ActiveMQ message broker events. Records node discovery and cluster membership changes. Relevant when investigating issues with background job processing or notifications that depend on the message broker.

### Integration Logs

**`data-integration/<integration-name>/data-integration.txt`**  
SIS integration run log for LIS/IMS integrations. Contains per-record processing results: field validation warnings, username mapping resolution, and success/failure status for each record processed. Includes the full XML payload for each person or membership record, making it verbose but comprehensive. The folder path reflects the integration name configured in the SIS Framework. First place to look when investigating why specific users or enrollments are not being created or updated correctly.

**`plugins/bbgs-SISFrameworkController.log`**  
SIS Framework Controller log. Records job queue polling and execution status. Under normal idle conditions the dominant entry is `no job pending execution` on a 15-second interval. Useful for confirming whether SIS jobs are being queued and picked up.

### Plugin / Extension Logs

**`plugins/bb-telemetry/application.log`**  
Blackboard internal telemetry pipeline. Records the scheduled data export tasks that feed the Illuminate CDM. If a client is seeing stale CDM data, this log will show whether exports are running and completing successfully.

**`plugins/mdb-sa/safeassign-log.txt`**  
SafeAssign plugin log. Records token requests for SafeAssign service authentication. Minimal under normal operation. Errors here indicate connectivity or authentication problems with the SafeAssign service.

**`x-bbgs-partner-cloud.log`**  
Partner Cloud (Building Blocks marketplace) main log. Records REST API calls made on behalf of the Partner Cloud service.

**`x-bbgs-partner-cloud.tasks.log`**  
Partner Cloud scheduled task log. Records periodic maintenance tasks such as partner icon updates. Normal operation produces routine housekeeping entries on an hourly schedule.

### Deployment-Specific Logs

**`custom/x-bbgs-consulting-central.log`** and **`custom/x-bbgs-consulting-central-grade-export.log`**  
Logs for Blackboard Professional Services extensions (Consulting Central / Grade Journey). Present only on deployments where these extensions are installed. Not standard system logs.
