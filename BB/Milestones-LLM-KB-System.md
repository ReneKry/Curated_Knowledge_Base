# Milestones-Dokument – LLM Knowledge Base System (MCP + FastAPI)

**Ableitung aus PRD v1.0 vom 2026-04-06**  
**Zielbild:** Skalierbares, auditierbares, deterministisches LLM-Knowledge-Base-System auf Markdown-Basis mit Delta-Sync, GC-Workflow, MCP-Server und FastAPI.

---

## 1) Leitplanken und Architekturprinzipien

### 1.1 Produktleitlinien
- **Markdown-first:** Markdown bleibt die Wahrheitsschicht; Index ist Navigations- und Konsistenzschicht.
- **Determinismus vor Heuristik:** Gleiches Input-Set ergibt gleiche Dateireihenfolge und gleiche Antwortbasis.
- **Auditability by Design:** Jeder Sync-Lauf und jeder GC-Fall ist protokolliert und nachvollziehbar.
- **KISS, DRY, YAGNI:**
  - KISS: wenige klar getrennte Komponenten,
  - DRY: gemeinsame Service-Schicht für MCP und FastAPI,
  - YAGNI: Neo4j erst bei nachgewiesenem Bedarf.

### 1.2 Zielarchitektur (v1)
1. **Content Layer:** Dateisystem/Git für `LLM_KB/`.
2. **Index Layer:** SQLite mit minimalem, erweiterbarem Schema.
3. **Bridge Layer:** `sync_kb.py` für Delta-Sync + Orphan-Cleanup.
4. **Governance Layer:** `gc_rules.py` + GC-Report Writer.
5. **Interface Layer A:** FastAPI (HTTP Contract, Observability, Integrationsfähigkeit).
6. **Interface Layer B:** MCP Server (LLM-Tooling, standardisierter Tool-Zugriff).

### 1.3 Skalierbarkeitsstrategie
- **Vertikale Skalierung v1:** SQLite-WAL, saubere Indizes, inkrementelle Verarbeitung.
- **Horizontale Entkopplung:** stateless API/MCP-Worker, gemeinsamer Storage/DB.
- **Asynchronität für schwere Läufe:** Sync/GC als Jobs, Query-Pfad strikt low-latency.
- **Backpressure & Limits:** harte `max_files`/`max_chars`-Grenzen, Rate Limits, Timeouts.

---

## 2) Milestone-Plan (M0–M8)

## M0 – Foundation & Repo-Baseline

### Ziel
Ein reproduzierbares Fundament schaffen, damit alle Folgephasen konsistent und messbar umgesetzt werden.

### Scope
- Projektstruktur für `reader/`, `sync/`, `gc/`, `api/`, `mcp/`, `db/`, `tests/`, `benchmarks/`.
- Konfigurationsmodell (z. B. Umgebungsvariablen + zentrale Config-Datei).
- Logging-, Error- und Exit-Code-Konventionen.

### Deliverables
- Verzeichnisstruktur + technische README.
- Entscheidungsvorlage für Runtime/Dependency-Management.

### Analyse
Ohne frühe Konventionen entsteht technische Drift zwischen CLI, API und MCP. M0 reduziert Integrationskosten in späteren Phasen signifikant.

### Exit-Kriterien
- Team kann lokal in <15 Minuten starten.
- Einheitliches Logging in mindestens 3 Kernkomponenten aktiv.

---

## M1 – Deterministischer Reader (FR-1 Kern)

### Ziel
`llm_kb_reader` als stabile Kernfunktion für priorisierte Volltext-Kontextgewinnung implementieren.

### Scope
- Manifest-first (`system/manifest.md` zuerst).
- Hierarchische Suche: `system > entities > topics > notes > outputs > sources`.
- Volltext-Rückgabe relevanter Markdown-Dateien.
- Limits: `--max-files`, `--max-chars`.

### Deliverables
- `query_kb_fast.sh` v2 oder Python-Reader CLI.
- Determinismus-Tests (identische Reihenfolge bei identischem Input).

### Analyse
Der Reader ist das produktive Herzstück. Determinismus ermöglicht reproduzierbare LLM-Antworten, Debugging und Audit-Trails.

### Risiken
- Zu große Dateien gefährden Latenz.
- Uneinheitliche Dateinamen/Ordnerstruktur erzeugen unerwartete Reihenfolgen.

### Gegenmaßnahmen
- Early Cut-Off mit globalem Zeichenlimit.
- Feste Sortierregeln (Pfad + Name) zusätzlich zur Ebenenpriorität.

### Exit-Kriterien
- FR-1 vollständig erfüllt.
- Query-Latenz auf Testdatenbasis < 1s bei 500 Dateien.

---

## M2 – SQLite-Schema + Sync-State (FR-3 Basis)

### Ziel
Auditable Indexbasis mit minimalem, aber ausreichendem Schema bereitstellen.

### Scope
- Tabellen gemäß PRD: `files`, `entities`, `claims`, `relations`, `sync_state`.
- Primär-/Fremdschlüssel, notwendige Indizes, Constraints.
- Laufprotokollierung pro Sync-Run.

### Deliverables
- `schema.sql`.
- Migrationsmechanismus (Versionierung des Schemas).

### Analyse
SQLite-first minimiert Betriebsaufwand und erlaubt trotzdem robuste lokale und serverseitige Deployments. Saubere Indizes sind entscheidend für <5s bei 5.000 Dateien.

### Exit-Kriterien
- Schema-Migration ohne Datenverlust zwischen zwei Versionen getestet.
- `sync_state` enthält mindestens Startzeit, Endzeit, Change-/Delete-Zähler.

---

## M3 – Delta-Sync + Orphan-Cleanup (FR-2)

### Ziel
Inkrementeller Sync statt Full-Reindex, inklusive sauberer Behandlung gelöschter Quellen.

### Scope
- MD5-Berechnung pro `.md`.
- Vergleich gegen `files.content_hash`.
- Nur geänderte/neue Dateien extrahieren.
- Orphan-Detection und Cleanup bei gelöschten Dateien.

### Deliverables
- `sync_kb.py`.
- Testfälle für create/update/delete-Szenarien.

### Analyse
Delta-Sync reduziert Laufzeit und Compute-Kosten drastisch. Orphan-Cleanup verhindert schleichende Inkonsistenzen (Sync Drift).

### Risiken
- Hash-Kollision (theoretisch).
- Race Conditions bei parallelen Sync-Läufen.

### Gegenmaßnahmen
- Optionale zusätzliche Größen-/Zeitstempelprüfung.
- Globales Sync-Lock und idempotente Runs.

### Exit-Kriterien
- FR-2 vollständig erfüllt.
- Kein Re-Extract bei unveränderten Dateien.

---

## M4 – Garbage Collection Workflow (FR-4 & FR-5)

### Ziel
Redundanz und Konflikte transparent markieren statt stillschweigend zu entfernen.

### Scope
- Regeln für `redundant` und `conflict`.
- Priorisierung nach Kanonregel: `system > entities > topics > notes > outputs > sources > raw`.
- Report-Writer für `BB/KB-Garbage-Collection-Report.md`.
- Optionales Flag `needs_review`.

### Deliverables
- `gc_rules.py`.
- Initiale Report-Struktur + Eintragsformat.

### Analyse
GC ist Governance, nicht nur Datenhygiene. Dokumentierte Konflikte erhalten Wissenshistorie und reduzieren Fehlentscheidungen durch stilles Löschen.

### Exit-Kriterien
- Jeder GC-Fall enthält: voller Pfad, Typ, Begründung, kanonische Referenz, Zeitstempel.
- FR-4 und FR-5 in v1-Scope umgesetzt.

---

## M5 – FastAPI Service Layer

### Ziel
HTTP-fähige, integrierbare Schnittstelle auf Basis derselben Kernlogik wie CLI/Reader schaffen.

### Scope
- Endpunkte: `/health`, `/query`, `/sync/run`, `/sync/runs/{run_id}`, `/gc/evaluate`, `/gc/report`.
- Pydantic-Modelle für Input/Output.
- Gemeinsame Service-Schicht für Reader/Sync/GC (DRY).

### Deliverables
- `api/main.py` + Router/Service-Module.
- OpenAPI-Spezifikation.

### Analyse
FastAPI ermöglicht standardisierte Integration in interne Systeme (UIs, Scheduler, Bots). Durch gemeinsame Service-Schicht sinkt Wartungsaufwand.

### Skalierung
- Mehrere API-Instanzen hinter Load Balancer.
- Sync/GC asynchron via Job-Queue.
- Query-Timeouts und Rate-Limits für Stabilität.

### Exit-Kriterien
- Alle Kernendpunkte funktionsfähig und getestet.
- 95%-Perzentil Query-Latenz < 2s bei 1.500 Dateien (Staging).

---

## M6 – MCP Server Integration

### Ziel
LLM-native Tooling bereitstellen, damit Agenten deterministisch und auditierbar auf die KB zugreifen.

### Scope
- MCP Tools: `kb.query`, `kb.sync`, `kb.gc_report`, `kb.file_get`.
- Tool-Verträge inklusive Fehlercodes und Grenzwerten.
- Optional: MCP auf dieselbe interne Service-Schicht wie FastAPI aufsetzen.

### Deliverables
- `mcp/server.py`.
- Tool-Contract-Dokumentation inkl. Beispiele.

### Analyse
MCP reduziert Integrationsaufwand mit LLM-Clients und erzwingt klare Funktionsgrenzen (statt freier Dateisystemzugriffe).

### Exit-Kriterien
- MCP-Tools in End-to-End-Tests aus Agentensicht erfolgreich.
- Identische Query via MCP und FastAPI liefert identische Dateireihenfolge.

---

## M7 – Performance, Skalierung & Zuverlässigkeit

### Ziel
Nicht-funktionale Ziele verifizieren und Engpässe eliminieren.

### Scope
- Benchmarking bei 500 / 1.500 / 5.000 Dateien.
- Lasttests für parallele Query-Aufrufe.
- Full-Hash-Audit-Job (wöchentlich) gegen Sync Drift.

### Deliverables
- Benchmark-Report mit KPIs.
- Tuning-Maßnahmenliste (Indices, IO, Caching).

### Analyse
Skalierbarkeit entsteht nicht nur durch Technologie, sondern durch Messbarkeit. M7 entscheidet evidenzbasiert über Neo4j-Bedarf.

### Exit-Kriterien
- <5s Query bei 5.000 Dateien (PRD-Ziel).
- Indexgröße <2x Rohtextgröße ohne Embeddings.

---

## M8 – Abnahme, Betriebsmodell & Rollout

### Ziel
Produktionsreife inkl. Governance, Betriebshandbuch und klarer Rollout-Routine.

### Scope
- Abnahme gegen FR- und KPI-Kriterien.
- Incident-Runbook (Sync-Fehler, DB-Lock, GC-Fehlmarkierung).
- Rollout-Plan (Canary/Staged Rollout, Backout-Strategie).

### Deliverables
- Abnahmeprotokoll.
- Operations Guide + SLO/SLA-Definition.

### Exit-Kriterien
- Alle Akzeptanzkriterien erfüllt oder mit Abweichungsbegründung dokumentiert.
- Betriebsübergabe formal abgeschlossen.

---

## 3) Cross-Milestone Deliverables (durchgängig)

- **Testpyramide:** Unit (Parser/Regeln), Integration (DB + Sync), E2E (Reader/API/MCP).
- **Observability:** strukturierte Logs, Metriken (Latenz, Fehlerrate, Sync-Dauer), Tracing optional.
- **Security-Basics:** Input-Validierung, Pfadnormalisierung, sichere Dateizugriffe.
- **Dokumentation:** Architekturentscheidungen (ADR), API-Contracts, GC-Governance.

---

## 4) KPI-Framework und Messmethodik

### Primäre KPIs
1. **Relevanzpräzision:** >90% relevante Kontextdateien.
2. **Latenz:** <5s bei 5.000 Dateien.
3. **GC-Qualität:** 100% dokumentierte Konflikt-/Redundanzfälle.
4. **Stabilität:** reproduzierbare Dateireihenfolge bei identischer Query.

### Sekundäre KPIs
- Sync-Dauer pro geändertem File.
- Anteil inkrementeller vs. vollständiger Extraktionen.
- Anzahl `needs_review` pro Woche.
- DB-Wachstum pro 1.000 neue Markdown-Dateien.

### Messdesign
- Feste Benchmark-Korpora (Small/Medium/Large).
- Wiederholte Runs (mind. n=20) für Median/95p.
- Getrennte Messung für Cold- und Warm-Cache.

---

## 5) Risikoanalyse mit Triggern

| Risiko | Trigger | Frühindikator | Maßnahme |
|---|---|---|---|
| Sync Drift | Inkrementeller Lauf übersieht Dateiänderung | Unterschied zwischen FS-Hash-Audit und DB-Status | Wöchentlicher Full-Hash-Audit, Alarmierung |
| Query-Überlauf | Sehr große/zu viele Trefferdateien | Hoher Anteil abgeschnittener Antworten | Ebenenlimits + globales Zeichenbudget |
| GC-Fehlklassifikation | Ambigue Aussagen in Quellen | Steigende `needs_review`-Quote | Reviewer-Workflow + Regelverfeinerung |
| SQLite-Lock-Contention | Viele parallele Schreiboperationen | Zeitouts/Lock-Fehler im Sync | Serialisierte Writes, Queue, WAL-Tuning |
| Overengineering | Frühe Neo4j-Einführung ohne Nachweis | Höhere Komplexität ohne KPI-Gewinn | Stage-Gate: Neo4j nur bei messbarem Bottleneck |

---

## 6) Stage-Gates (Go/No-Go)

- **Gate A (nach M3):** Reader + Delta-Sync stabil? Wenn nein: keine API/MCP-Exponierung.
- **Gate B (nach M5/M6):** API/MCP liefern identische Ergebnisse? Wenn nein: Contract-Harmonisierung vor M7.
- **Gate C (nach M7):** KPI-Ziele erreicht? Wenn nein: gezieltes Tuning vor Rollout.
- **Gate D (M8):** Abnahme vollständig? Wenn nein: kein Production-Go-Live.

---

## 7) Team- und Betriebsmodell (Rollen)

- **KB Curator:** pflegt Markdown-Quellen und Kanon-Entscheidungen.
- **Platform Engineer:** verantwortet Sync, DB, Deployment, Observability.
- **API/MCP Engineer:** betreut Schnittstellen, Contracts und Integrationen.
- **Reviewer (GC):** prüft Konflikt-/Redundanzfälle mit `needs_review`.
- **Product Owner:** priorisiert Milestones, akzeptiert Deliverables.

---

## 8) Vorschlag für Zeitplanung (indikativ)

- M0: 0,5 Woche
- M1: 1 Woche
- M2: 0,5–1 Woche
- M3: 1 Woche
- M4: 1 Woche
- M5: 1 Woche
- M6: 0,5–1 Woche
- M7: 1 Woche
- M8: 0,5 Woche

**Gesamt:** ca. 7–8 Wochen bis produktionsnahe Erstversion (teamabhängig).

---

## 9) Definition of Done (gesamt)

Das System gilt als umgesetzt, wenn:
1. FR-1 bis FR-5 erfüllt und getestet sind,
2. FastAPI- und MCP-Schnittstellen produktiv nutzbar sind,
3. KPI-Ziele erreicht oder mit nachvollziehbarer Abweichung dokumentiert sind,
4. GC-Report alle Fälle strukturiert, nachvollziehbar und revisionssicher dokumentiert,
5. Betriebs- und Rollout-Dokumentation vollständig vorliegt.

