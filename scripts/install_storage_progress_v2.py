from pathlib import Path
import textwrap

path = Path('.github/workflows/ikiraplus-storage.yml')
s = path.read_text(encoding='utf-8')
original = s


def one(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)


# Worker callbacks + source size hint from DL Server.
one(
    '      CALLBACK_FAIL_URL: ${{ github.event.client_payload.callbackFailUrl }}\n',
    '      CALLBACK_FAIL_URL: ${{ github.event.client_payload.callbackFailUrl }}\n'
    '      CALLBACK_PROGRESS_URL: ${{ github.event.client_payload.callbackProgressUrl }}\n'
    '      CALLBACK_TOKEN: ${{ github.event.client_payload.callbackToken }}\n'
    '      EXPECTED_SIZE: ${{ github.event.client_payload.expectedSize }}\n',
    'job progress env',
)

one(
    '          import urllib.request\n          import time\n',
    '          import urllib.request\n          import time\n          import json\n',
    'python json import',
)

helper_body = r'''CALLBACK_PROGRESS_URL = os.environ.get("CALLBACK_PROGRESS_URL", "").strip()
CALLBACK_TOKEN = os.environ.get("CALLBACK_TOKEN", "").strip()
try:
    EXPECTED_SIZE = max(0, int(float(os.environ.get("EXPECTED_SIZE", "0") or 0)))
except Exception:
    EXPECTED_SIZE = 0
_progress_last_sent = {}


def report_progress(stage, transferred=0, total=0, speed=0, force=False, message=None, attempt=None):
    """Send live transfer progress to DL Server without ever failing the storage job."""
    if not CALLBACK_PROGRESS_URL or not CALLBACK_TOKEN:
        return
    try:
        transferred = max(0, int(transferred or 0))
        total = max(0, int(total or 0)) or EXPECTED_SIZE
        speed = max(0, int(speed or 0))
        percent = None
        if total > 0:
            percent = max(0.0, min(100.0, transferred * 100.0 / total))

        now = time.time()
        prev = _progress_last_sent.get(stage, {"time": 0.0, "percent": -999.0, "bytes": -1})
        pct_delta = 999.0 if percent is None else abs(percent - float(prev.get("percent", -999.0)))
        byte_delta = max(0, transferred - int(prev.get("bytes", -1)))
        if not force and now - float(prev.get("time", 0.0)) < 5.0 and pct_delta < 1.0 and byte_delta < 8 * 1024 * 1024:
            return

        payload = {
            "id": os.environ.get("SHORT_ID", ""),
            "token": CALLBACK_TOKEN,
            "runId": int(os.environ.get("GITHUB_RUN_ID", "0") or 0),
            "stage": stage,
            "transferredBytes": transferred,
            "totalBytes": total or None,
            "speedBps": speed,
            "percent": round(percent, 1) if percent is not None else None,
            "attempt": attempt,
            "message": message,
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(
            CALLBACK_PROGRESS_URL,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "ikiraplus-progress/2.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            resp.read(256)
        _progress_last_sent[stage] = {
            "time": now,
            "percent": percent if percent is not None else -999.0,
            "bytes": transferred,
        }
    except Exception as exc:
        print("Progress callback warning:", str(exc)[:180])


def probe_remote_size(url):
    """Best-effort total-size probe when DL Server could not determine it."""
    if EXPECTED_SIZE > 0:
        return EXPECTED_SIZE
    headers = {
        "User-Agent": UA,
        "Accept": "application/octet-stream,*/*;q=0.8",
        "Accept-Encoding": "identity",
        "Range": "bytes=0-0",
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            cr = resp.headers.get("Content-Range", "")
            m = re.search(r"/(\d+)\s*$", cr)
            if m and int(m.group(1)) > 0:
                return int(m.group(1))
            if getattr(resp, "status", resp.getcode()) != 206:
                cl = resp.headers.get("Content-Length", "")
                if str(cl).isdigit() and int(cl) > 4096:
                    return int(cl)
    except Exception as exc:
        headers_obj = getattr(exc, "headers", None)
        if headers_obj is not None:
            cr = headers_obj.get("Content-Range", "")
            m = re.search(r"/(\d+)\s*$", cr)
            if m and int(m.group(1)) > 0:
                return int(m.group(1))
    return 0


def run_with_file_progress(cmd, output, total_hint=0, label="تنزيل الملف"):
    """Run a downloader while sampling the growing output file every two seconds."""
    initial_size = output.stat().st_size if output.exists() else 0
    report_progress("download", initial_size, total_hint, 0, force=True, message=f"بدأ {label}")
    proc = subprocess.Popen(cmd)
    last_bytes = initial_size
    last_time = time.monotonic()
    last_speed = 0
    while proc.poll() is None:
        time.sleep(2)
        current = output.stat().st_size if output.exists() else 0
        now_mono = time.monotonic()
        elapsed = max(0.001, now_mono - last_time)
        if current >= last_bytes:
            last_speed = int((current - last_bytes) / elapsed)
        last_bytes = current
        last_time = now_mono
        report_progress("download", current, total_hint, last_speed)

    rc = proc.wait()
    current = output.stat().st_size if output.exists() else 0
    if rc != 0:
        report_progress("download", current, total_hint, 0, force=True, message=f"توقفت محاولة التنزيل برمز {rc}")
        raise subprocess.CalledProcessError(rc, cmd)
    report_progress("download", current, total_hint or current, 0, force=True, message="اكتمل تنزيل الملف")

'''
helper = textwrap.indent(helper_body, '          ')
anchor = '          def host_of(url):\n              return (urllib.parse.urlparse(url).hostname or "").lower()\n'
if s.count(anchor) != 1:
    raise SystemExit(f'helper anchor: expected 1, found {s.count(anchor)}')
s = s.replace(anchor, helper + anchor, 1)

# Main curl path: measure actual bytes written to candidate/output.
one(
'''              cmd.append(url)\n              print("Downloading from:", host_of(url) or url)\n              subprocess.run(cmd, check=True)\n''',
'''              cmd.append(url)\n              print("Downloading from:", host_of(url) or url)\n              total_hint = probe_remote_size(url)\n              run_with_file_progress(cmd, output, total_hint)\n''',
'run_curl live progress',
)

# IPAOMTK direct-file path has its own curl invocation; monitor it too.
one(
'''              print("IPAOMTK file download:", host_of(file_url), "referer:", page_url)\n              try:\n                  subprocess.run(cmd, check=True)\n              except subprocess.CalledProcessError as exc:\n                  print("IPAOMTK file request failed:", exc)\n                  return False\n''',
'''              print("IPAOMTK file download:", host_of(file_url), "referer:", page_url)\n              try:\n                  run_with_file_progress(cmd, candidate, probe_remote_size(file_url), "تنزيل IPAOMTK")\n              except subprocess.CalledProcessError as exc:\n                  print("IPAOMTK file request failed:", exc)\n                  return False\n''',
'IPAOMTK direct progress',
)

# Chrome fallback: it already samples partial file size; publish those bytes.
one(
'''                          if now - last_report >= 10:\n                              print(\n                                  "IPAOMTK Chrome waiting:",\n                                  "started=", download_started,\n                                  "partials=", len(partials),\n                                  "downloaded_bytes=", total_bytes,\n                              )\n                              last_report = now\n''',
'''                          if now - last_report >= 10:\n                              report_progress("download", total_bytes, EXPECTED_SIZE, 0, message="IPAOMTK Chrome download")\n                              print(\n                                  "IPAOMTK Chrome waiting:",\n                                  "started=", download_started,\n                                  "partials=", len(partials),\n                                  "downloaded_bytes=", total_bytes,\n                              )\n                              last_report = now\n''',
'Chrome progress',
)

# StreamVault dylib knows exact total.
one(
'''                      out.write(got)\n                      out.flush()\n                      print(f"Downloaded dylib chunk {part_no}: {start}-{end}")\n                      start = end + 1\n''',
'''                      out.write(got)\n                      out.flush()\n                      print(f"Downloaded dylib chunk {part_no}: {start}-{end}")\n                      start = end + 1\n                      report_progress("download", start, total, 0, message="StreamVault chunked download")\n''',
'chunked progress',
)

# Explicit validation stage between download and upload.
one(
'''          size = final_file.stat().st_size\n          print("Validated real file:", final_file)\n          print("Validation:", reason)\n          print(f"Final size: {size} bytes ({size / 1024 / 1024:.2f} MiB)")\n          PY\n''',
'''          size = final_file.stat().st_size\n          report_progress("validate", size, size, 0, force=True, message="تم تنزيل الملف وفحصه بنجاح")\n          print("Validated real file:", final_file)\n          print("Validation:", reason)\n          print(f"Final size: {size} bytes ({size / 1024 / 1024:.2f} MiB)")\n          PY\n''',
'validate stage',
)

# Build one reusable uploader script at the top of the release-upload step.
uploader_body = r'''import os
import json
import time
import http.client
import urllib.parse
import urllib.request

file_path = os.environ["UPLOAD_FILE"]
release_id = os.environ["RELEASE_ID"]
repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GH_TOKEN"]
asset_name = os.environ["ASSET_NAME"]
short_id = os.environ.get("SHORT_ID", "")
callback_url = os.environ.get("CALLBACK_PROGRESS_URL", "").strip()
callback_token = os.environ.get("CALLBACK_TOKEN", "").strip()
run_id = int(os.environ.get("GITHUB_RUN_ID", "0") or 0)
attempt = int(os.environ.get("UPLOAD_ATTEMPT", "1") or 1)
total = os.path.getsize(file_path)
last_callback = 0.0
last_bytes = 0
last_time = time.monotonic()
speed = 0


def progress(sent, force=False, message=None):
    global last_callback, last_bytes, last_time, speed
    if not callback_url or not callback_token:
        return
    now_mono = time.monotonic()
    elapsed = max(0.001, now_mono - last_time)
    if sent >= last_bytes:
        speed = int((sent - last_bytes) / elapsed)
    last_bytes = sent
    last_time = now_mono
    if not force and now_mono - last_callback < 5:
        return
    payload = {
        "id": short_id,
        "token": callback_token,
        "runId": run_id,
        "stage": "upload",
        "transferredBytes": sent,
        "totalBytes": total,
        "speedBps": max(0, speed),
        "percent": round(sent * 100.0 / total, 1) if total else None,
        "attempt": attempt,
        "message": message,
    }
    try:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(
            callback_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "ikiraplus-upload-progress/2.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            resp.read(256)
    except Exception as exc:
        print("Upload progress callback warning:", str(exc)[:180])
    last_callback = now_mono


encoded_name = urllib.parse.quote(asset_name, safe="")
api_path = f"/repos/{repo}/releases/{release_id}/assets?name={encoded_name}"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ikiraplus-storage-uploader/2.0",
    "Content-Type": "application/octet-stream",
    "Content-Length": str(total),
}

progress(0, force=True, message=f"بدأ رفع المحاولة {attempt}/2")
conn = http.client.HTTPSConnection("uploads.github.com", timeout=120)
try:
    conn.putrequest("POST", api_path)
    for name, value in headers.items():
        conn.putheader(name, value)
    conn.endheaders()

    sent = 0
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(4 * 1024 * 1024)
            if not chunk:
                break
            conn.send(chunk)
            sent += len(chunk)
            progress(sent)

    response = conn.getresponse()
    body = response.read()
    if response.status not in (200, 201):
        text = body.decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"GitHub upload HTTP {response.status}: {text}")
    progress(total, force=True, message="اكتمل إرسال البايتات إلى GitHub")
    print(f"Uploaded {total} bytes to GitHub release asset: {asset_name}")
finally:
    conn.close()
'''

# YAML strips ten leading spaces from run-block content, so the heredoc delimiter must use exactly ten here.
uploader_script = (
    '          UPLOADER="$RUNNER_TEMP/ikiraplus-storage/upload-release.py"\n'
    '          cat > "$UPLOADER" <<\'PY_UPLOAD\'\n'
    + textwrap.indent(uploader_body, '          ')
    + '          PY_UPLOAD\n\n'
)
anchor_upload = '          LOCAL_SIZE="$(stat -c%s "$FILE")"\n\n'
if s.count(anchor_upload) != 1:
    raise SystemExit(f'uploader script anchor: expected 1, found {s.count(anchor_upload)}')
s = s.replace(anchor_upload, anchor_upload + uploader_script, 1)

one(
'''              set +e\n              timeout --foreground 7200s gh release upload "$tag" "$FILE" --repo "$GITHUB_REPOSITORY"\n              rc=$?\n              set -e\n''',
'''              set +e\n              UPLOAD_FILE="$FILE" RELEASE_ID="$release_id" UPLOAD_ATTEMPT="$attempt" \\
                timeout --foreground 7200s python3 "$UPLOADER"\n              rc=$?\n              set -e\n''',
'GitHub streaming uploader',
)

if s == original:
    raise SystemExit('No workflow changes were made')
path.write_text(s, encoding='utf-8')
print('Patched', path, 'bytes', len(original), '->', len(s))
