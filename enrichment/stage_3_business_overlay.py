import json
import time
import logging
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# =========================
# CONFIG
# =========================

INPUT_DOC = "XX_clean.md"
OUTPUT_DOC = "XX_business.md"
PROGRESS_FILE = "progress1.json"

MODEL = "mixtral:8x7b"
OLLAMA_API = "http://localhost:11434/api/generate"

TIMEOUT = 900
RETRIES = 3

MAX_CHARS = 2200
MAX_WORKERS = 2   
CONTEXT_OVERLAP = 300

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# =========================
# LOCK
# =========================

progress_lock = Lock()

# =========================
# PROGRESS
# =========================

def load_progress(path):
    if path.exists():
        return json.loads(path.read_text())
    return {"done": []}

def save_progress(path, data):
    path.write_text(json.dumps(data))

# =========================
# CHUNKING
# =========================

def split_text_smart(text, max_chars=MAX_CHARS):
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for p in paragraphs:
        if len(p) > max_chars:
            for i in range(0, len(p), max_chars):
                chunks.append(p[i:i+max_chars])
            continue

        if len(current) + len(p) <= max_chars:
            current += p + "\n\n"
        else:
            if current:
                chunks.append(current)
            current = p + "\n\n"

    if current:
        chunks.append(current)

    return chunks

# =========================
# PROMPT (OVERLAY)
# =========================

def build_prompt(text):
    return f"""
You are a technical consultant explaining a system to a business audience.

TASK:
Keep the INPUT text intact and enrich it with business-level explanations.

HEADING RULE:
- You may add a short descriptive heading at the beginning of the section
- Only if a clear component, workflow, or system name is present in the INPUT
- The heading must reuse exact names from INPUT
- If no clear heading can be derived, do NOT add one

CRITICAL RULES:
- DO NOT remove or rewrite original technical content
- DO NOT shorten the text
- DO NOT simplify technical descriptions
- DO NOT change meaning

STRUCTURE RULES:
- Preserve ALL original structure exactly as it appears
- Preserve headings, bullet points, lists, and formatting
- DO NOT rename, merge, or split sections
- DO NOT convert structured data into paragraphs
- Do NOT always place explanations only at the end of the section

GENERAL RULE:
- Whatever structure exists in INPUT must remain unchanged
- The explanation must adapt to the structure, not the other way around

WHAT TO DO:
- Keep all original technical text
- Add explanations that clarify:
  - what is happening
  - where in the system it happens
  - why it matters
- Add brief but meaningful explanations (typically 2–4 sentences per section)
- Integrate explanations naturally with the existing structure


STYLE:
- Grounded in the actual technical content
- Explanations must reference concrete elements from INPUT
- Avoid generic or abstract statements

FORBIDDEN:
- Adding new structural elements, except for an optional heading as defined above
- Generalizing specific technical behavior
- Vague claims without reference to actual components
- Commenting on missing information or completeness of the input
- Evaluating the quality of the input

QUALITY CHECK:
- Each section must still describe the same system part as in INPUT
- Each explanation must be traceable to specific technical details

CONTEXT USAGE:
- Use CONTEXT only to maintain continuity
- Do NOT assume it fully describes the system
- Focus primarily on INPUT

If unsure, return INPUT unchanged.

OUTPUT:
Return enriched text with identical structure.

INPUT:
{text}
"""

# =========================
# OLLAMA CALL
# =========================

def call_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 1200,
            "temperature": 0.1
        }
    }

    for attempt in range(RETRIES):
        try:
            start = time.time()

            r = requests.post(
                OLLAMA_API,
                json=payload,
                timeout=TIMEOUT
            )

            r.raise_for_status()
            data = r.json()

            duration = time.time() - start
            logging.info(f"Ollama response in {duration:.2f}s")

            return data.get("response", "")

        except Exception as e:
            logging.error(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)

    return ""

# =========================
# PROCESSING
# =========================

def process_chunks(chunks, progress, progress_path, output_path):
    results = {}
    next_to_write = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        for i, chunk in enumerate(chunks):
            if i in progress["done"]:
                continue

            prev = chunks[i-1][-CONTEXT_OVERLAP:] if i > 0 else ""
            prompt = build_prompt(
            f"CONTEXT:\n{prev}\n\nINPUT:\n{chunk}"
            )

            futures[executor.submit(call_ollama, prompt)] = i

        for future in as_completed(futures):
            i = futures[future]

            try:
                result = future.result()

                if not result.strip():
                    result = chunks[i]

                results[i] = result

                with progress_lock:
                    progress["done"].append(i)
                    save_progress(progress_path, progress)

                logging.info(f"[DONE] Chunk {i+1}/{len(chunks)}")

                # ordered write
                while next_to_write in results:
                    with open(output_path, "a", encoding="utf-8") as f:
                        f.write(results[next_to_write].strip() + "\n\n")
                        f.flush()

                    logging.info(f"[WRITE] Chunk {next_to_write+1}")

                    del results[next_to_write]
                    next_to_write += 1

            except Exception as e:
                logging.error(f"Chunk {i} failed: {e}")

# =========================
# MAIN
# =========================

def main():
    logging.info("START")

    base_dir = Path(__file__).parent
    input_path = base_dir / INPUT_DOC
    output_path = base_dir / OUTPUT_DOC
    progress_path = base_dir / PROGRESS_FILE

    if not progress_path.exists() and output_path.exists():
        output_path.unlink()

    text = input_path.read_text(encoding="utf-8")
    chunks = split_text_smart(text)

    logging.info(f"Total chunks: {len(chunks)}")

    progress = load_progress(progress_path)

    process_chunks(
        chunks,
        progress,
        progress_path,
        output_path
    )

    logging.info("ALL DONE")

# =========================

if __name__ == "__main__":
    main()