import os
import re
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ==================================
# CONFIG
# ==================================

MODEL_FACT = "llama3.1:8b"
MODEL_FLOW = "qwen2.5:14b"

OLLAMA_API = "http://localhost:11434/api/generate"

DOCS_DIR = r"xx"
REPO_DIR = r"C:\xx\xx\xx\GIT\xx\XX"

OUTPUT_DOC = "MXX_system_raw.md"
PARTIAL_DOC = "partial_XX_output.md"
LOG_FILE = "process.log"

CHUNK_SIZE = 3500
MAX_CHUNKS = 75
MAX_WORKERS = 2
MAX_FILE_SIZE = 2_000_000

TIMEOUT = 900
RETRIES = 3

SESSION = requests.Session()

_log_lock = Lock()
_write_lock = Lock()

_whitespace_re = re.compile(r"\s+")

# ==================================
# LOGGING
# ==================================

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)

    with _log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

# ==================================
# OLLAMA
# ==================================

def call_ollama(prompt, model):

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    headers = {
        "Content-Type": "application/json"
    }

    for attempt in range(RETRIES):
        try:
            r = SESSION.post(
                OLLAMA_API,
                headers=headers,
                data=json.dumps(payload),
                timeout=TIMEOUT
            )

            r.raise_for_status()

            text = r.text.strip().split("\n")[-1]
            data = json.loads(text)

            return data.get("response", "")

        except Exception as e:
            log(f"Ollama error {attempt+1}: {e}")
            time.sleep(3 * (attempt + 1))

    return ""

# ==================================
# FILE READ
# ==================================

def safe_read(path):
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return None
        return path.read_text(errors="ignore")
    except Exception as e:
        log(f"Read failed {path}: {e}")
        return None

# ==================================
# EXTRACT FILES
# ==================================

def extract_all():
    text = []
    file_count = 0

    for root, _, files in os.walk(REPO_DIR):
        for f in sorted(files):
            path = Path(root) / f

            content = safe_read(path)
            if not content:
                continue

            file_count += 1

            text.append(f"\n### FILE: {path}\n")
            text.append(content[:3000])

    log(f"Files processed: {file_count}")
    return "\n".join(text)

# ==================================
# CHUNKING
# ==================================

def chunk_text(text):

    parts = text.split("### FILE:")

    chunks = []
    current = ""

    for part in parts:
        if len(current) + len(part) < CHUNK_SIZE:
            current += "\n" + part
        else:
            chunks.append(current.strip())
            current = part

    if current:
        chunks.append(current.strip())

    log(f"Chunks: {len(chunks)}")
    return chunks[:MAX_CHUNKS]

# ==================================
# PROMPTS
# ==================================

def build_fact_prompt(chunk):
    return f"""
Extract concrete system actors and interactions.

Return structured bullet points:

ENTITY:
TYPE (script/table/api/job/workflow/jar/xsl/xsd/file/view/procedure/config/sql_operation/unknown):
READS:
WRITES:
CALLS:
CALLED_BY:
TRIGGERED_BY:

Do not ignore entities without flow.

Rules:
- capture everything visible
- no guessing
- no explanations
- do not skip anything
- detect workflows (wf, workflow, scheduler jobs, pipelines) as TYPE: workflow
- treat .jar as executable component, but prioritize its role (called by workflow/script) over standalone description
- detect .xsl files as TYPE: xsl (data transformation component)
- detect .xsd files as TYPE: xsd (data transformation component)
- treat XML files as TYPE: config if they define workflows, jobs, or system configuration
- do not treat XML data messages as separate entities

Also detect data structures:

- database tables (CREATE TABLE)
- views
- procedures
- configuration files


INPUT:
{chunk}
"""


def build_flow_prompt(facts):
    return f"""
Build detailed system flows.

Use ONLY given facts.

For each flow, explicitly describe:

- TRIGGER (what starts it)
- COMPONENT (script, ETL, API, job, procedure)
- SOURCE (tables, files, APIs)
- TARGET (tables, files, systems)
- ACTION (what happens: load, transform, call, wait)

Rules:
- use real names exactly as given
- do not generalize
- do not invent anything
- include all technical details if present
- if something is missing, say it is not visible

If no flow is visible:
- describe only what the component is
- do not explain absence of flow
- do not use phrases like "standalone", "no interaction", "no actions"

Output:
One flow per paragraph, 3–5 sentences

Focus on:
- data movement
- dependencies
- execution order

INPUT:
{facts}
"""

# ==================================
# DEDUP
# ==================================

def deduplicate_text(text):
    seen = set()
    out = []

    for l in text.splitlines():
        k = _whitespace_re.sub(" ", l.strip().lower())
        if len(k) < 5:
            continue
        if k not in seen:
            seen.add(k)
            out.append(l)

    return "\n".join(out)

# ==================================
# PROCESS CHUNK
# ==================================

def process_chunk(i, chunk, total):

    log(f"[{i+1}/{total}] START")

    # STEP 1 — FACT (llama)
    facts = call_ollama(build_fact_prompt(chunk), MODEL_FACT)

    if not facts.strip():
        log(f"[{i+1}] EMPTY FACT")
        return ""

    # STEP 2 — FLOW (qwen)
    flows = call_ollama(build_flow_prompt(facts), MODEL_FLOW)

    if not flows.strip():
        log(f"[{i+1}] NO FLOWS")
        return ""

    log(f"[{i+1}] flows={len(flows)}")
    log(f"[{i+1}/{total}] DONE")

    with _write_lock:
        with open(PARTIAL_DOC, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Chunk {i+1}\n{flows}")

    return flows

# ==================================
# MAIN
# ==================================

def main():

    log("START")

    data = extract_all()
    log(f"Input size: {len(data)}")

    chunks = chunk_text(data)
    total = len(chunks)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_chunk, i, c, total)
            for i, c in enumerate(chunks)
        ]

        for _ in as_completed(futures):
            pass

    log("Merging output")

    text = Path(PARTIAL_DOC).read_text(encoding="utf-8")

    log("Deduplicating")

    text = deduplicate_text(text)

    Path(OUTPUT_DOC).write_text(text, encoding="utf-8")

    log("DONE")

# ==================================

if __name__ == "__main__":
    main()