# BB – Build Book

Dieses Verzeichnis enthält zentrale Planungs- und Governance-Dokumente für das LLM-Knowledge-Base-System.

## Inhalte
- `Milestones-LLM-KB-System.md`: Umsetzungs-Milestones mit Analysen, Risiken, KPIs und Abnahmekriterien.
- `KB-Garbage-Collection-Report.md`: Laufendes Protokoll für markierte Redundanz-/Konfliktfälle gemäß PRD.
- `../Docu/API-Kurzbeschreibungen-Index.md`: Kurzindex der FastAPI- und MCP-Verträge, inkl. Ingestion, dynamischer Settings und Service-Lifecycle.

## Prinzipien
- KISS: Einfacher, auditierbarer Aufbau vor komplexen Optimierungen.
- DRY: Keine doppelte Logik über Reader-, Sync- und API-Schicht.
- YAGNI: Erweiterungen (z. B. Neo4j) erst bei messbarer Notwendigkeit.
- Ein gemeinsamer Ingestion-Service ist die einzige Schreibschnittstelle für API und MCP.
