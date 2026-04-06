# ADR-Entscheidungen v1 – LLM KB System

## Status
Accepted (2026-04-06)

## ADR-001: Provider-Strategie
- Entscheidung: Primary + Fallback.
- Absicht: Höhere Verfügbarkeit bei überschaubarer Komplexität.

## ADR-002: Ingestion-Ausführung
- Entscheidung: Ingestion-Worker und Sync-Scheduler als verwaltete Dienste.
- Absicht: Schreibpfad und Delta-Sync betrieblich steuerbar machen.

## ADR-003: Aktive Knowledge Base
- Entscheidung: aktive KB pro API-Key/Client.
- Absicht: Mandantenähnliche Trennung ohne komplexes Multi-Tenant-Sicherheitsmodell in v1.

## ADR-004: Auth-Startniveau
- Entscheidung: zunächst kein Auth (nur internes Netz).
- Absicht: Schneller Start in kontrollierter Infrastruktur.
- Hinweis: Auth als Ausbaustufe frühzeitig designen (Schnittstellen kompatibel halten).

## ADR-005: Limits
- Entscheidung: konservative Defaults plus pro-KB-Override.
- Absicht: stabile Latenz und kontrollierter Ressourcenverbrauch.

## ADR-006: Qualitätssicherung
- Entscheidung: Minimal-CI ab sofort; Performance-Benchmarks bleiben Stage-Gate M8.
- Absicht: frühe Qualitätssicherung ohne Implementierungsgeschwindigkeit zu bremsen.

## Architekturklarstellung Ingestion
Es gibt zwei Eingangswege für neues Wissen:
1. Online-Eingang über API/MCP,
2. Offline/Batch-Eingang über separate Ingestion-Pipeline.

Beide Wege verwenden dieselbe Ingestion-Service-Schicht für Validierung, Normalisierung,
Persistenz, Delta-Sync-Trigger und GC-Prüfung. Dadurch bleiben Verhalten und Audit-Trail
identisch (DRY), obwohl mehrere Eingänge unterstützt werden.
