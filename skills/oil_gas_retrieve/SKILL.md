---
name: oil_gas_retrieve
description: Retrieve OPEC/EIA/CBR Report chunks (Chroma + OpenRouter Nemotron embeddings) for oil-and-gas answers.
version: 0.1.0
type: extension
runtime: python3
entry: plugin.py
permissions: [tool]
when_to_use: >
  The user asks an in-Competence oil or gas question that Reports may answer
  (demand, supply, OPEC/EIA/CBR outlooks, crude prices in published editions).
timeout_sec: 120
---

# Report retrieve

Call this tool when the question is inside Competence and a Report may hold the figure.
Use the returned `citation` strings verbatim as `[Отчёт …]` tags. Sample chunks say excerpt.
Do not invent volumes. English chunks are valid for a Russian question.
Do not cite a Report unless this tool ran **this turn**.
