# LLM-Assisted Enterprise Audit Pipeline

A Python-based automation pipeline for analyzing undocumented enterprise systems using local LLMs.

The project processes unstructured technical documentation and source code repositories, extracts system entities and relationships, reconstructs technical flows, and enriches the output with business-oriented explanations.

The pipeline was designed to support audit, system analysis, dependency reconstruction, and documentation validation in complex legacy enterprise environments.

---

# Problem Statement

Large enterprise systems often contain:

* undocumented dependencies
* inconsistent documentation
* fragmented technical knowledge
* legacy workflows spread across multiple repositories and file formats

Manual analysis of these systems is time-consuming and difficult to scale.

This project explores how local LLMs can assist with:

* technical entity extraction
* dependency reconstruction
* workflow interpretation
* documentation enrichment
* audit-oriented analysis

while still maintaining deterministic processing and validation layers.

---

# Pipeline Architecture

The solution is divided into multiple processing stages.

## Stage 1 — Technical Extraction

The pipeline processes repositories and technical documents and extracts:

* workflows
* scripts
* database objects
* APIs
* configuration files
* data transformations
* inter-system relationships

Key features:

* recursive repository parsing
* chunk-based processing
* multi-model orchestration
* parallel execution
* structured extraction prompts
* flow reconstruction

Models used:

* `llama3.1:8b`
* `qwen2.5:14b`

---

## Stage 2 — Cleaning & Validation

LLM outputs are post-processed to reduce noise and improve consistency.

Implemented safeguards include:

* hallucination filtering
* duplicate removal
* formatting cleanup
* deterministic output normalization

The project intentionally treats LLM output as probabilistic and applies additional validation layers before generating final outputs.

---

## Stage 3 — Business Enrichment Overlay

The cleaned technical output is enriched with business-oriented explanations while preserving the original technical structure.

Key design goals:

* preserve technical accuracy
* avoid destructive summarization
* maintain original formatting and hierarchy
* add contextual explanations without modifying technical facts

Model used:

* `mixtral:8x7b`

---

# Technologies

* Python
* Ollama
* Local LLMs
* ThreadPoolExecutor
* Regex
* Markdown processing

---

# Key Engineering Challenges

The project focuses heavily on practical limitations of real-world LLM workflows, including:

* inconsistent outputs
* hallucinated relationships
* duplicate generation
* context-size limitations
* chunk continuity
* deterministic post-processing
* balancing technical and business-level outputs

---

# Design Philosophy

The project intentionally avoids treating LLMs as autonomous decision-makers.

Instead, LLMs are used as assisted processing components within a controlled pipeline architecture.

Core principles:

* preserve original technical meaning
* avoid uncontrolled summarization
* prefer deterministic cleanup over blind generation
* separate extraction, validation, and interpretation stages

---

# Example Use Cases

* enterprise system audits
* undocumented system analysis
* dependency mapping
* technical documentation reconstruction
* workflow analysis
* legacy system exploration

---

# Repository Structure

```text
.
├── stage1_extraction.py
├── stage2_cleaning.py
├── stage3_business_overlay.py
├── output/
├── logs/
└── README.md
```

---

# Disclaimer

This repository contains a simplified and anonymized version of the original project.

No proprietary data, internal documentation, or enterprise-specific logic is included.

---

# Author

Personal automation and systems analysis project focused on enterprise environments, infrastructure-oriented thinking, and practical LLM-assisted workflows.
