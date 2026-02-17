# Sprint Backlog (Woche 1-2): Enterprise-Readiness Foundation

Status: `completed`  
Ziel: Phase 0 abschließen und den ersten vertikalen Slice für IAM/RBAC liefern.

## Sprint-Status (laufend)
- `W1-01` done
- `W1-02` done
- `W1-03` done
- `W1-04` done
- `W1-05` done
- `W1-06` done
- `W1-07` done
- `W1-08` done
- `W1-09` done
- `W1-10` done
- `W1-11` done
- `W1-12` done

## Sprint-Ziele
- Architektur- und Sicherheitsentscheidungen verbindlich machen (ADRs).
- Tenant-fähiges Datenmodell vorbereiten (ohne Big-Bang-Migration).
- Ersten AuthN/AuthZ-Slice produktiv im API-Layer verankern.
- Audit-Event-Basis schaffen (jede sensitive Aktion wird protokolliert).

## Priorisierte Issue-Liste

### `W1-01` ADR: Zielarchitektur und Tech-Entscheidungen finalisieren
- Priorität: `P0`
- Aufwand: `0.5 Tag`
- Scope:
  - ADR für `PostgreSQL + Redis + Celery`
  - ADR für `OIDC` (Bearer JWT Validation)
  - ADR für `S3/MinIO` als Artifact-Storage
  - ADR für `OpenTelemetry + Prometheus`
- Akzeptanzkriterien:
  - Datei `docs/adr/ADR-001-enterprise-architecture.md` vorhanden.
  - Entscheidungen enthalten Alternativen + Trade-offs + Rollback-Option.

### `W1-02` Security Baseline: zentrale Settings/Secrets-Härtung
- Priorität: `P0`
- Aufwand: `0.5 Tag`
- Scope:
  - `apps/api/config.py` um OIDC-, RBAC- und Audit-Settings erweitern.
  - Sichere Defaults (deny-by-default, leere Allow-Listen).
  - `.env.example` aktualisieren.
- Akzeptanzkriterien:
  - Neue Settings dokumentiert.
  - App startet mit sicheren Defaults ohne impliziten offenen Modus.

### `W1-03` AuthN Slice: JWT/OIDC Middleware für API
- Priorität: `P0`
- Aufwand: `1.5 Tage`
- Scope:
  - Dependency/Funktion für Token-Parsing und Claims-Extraktion.
  - `RequestContext` mit `subject`, `tenant_id`, `roles`.
  - Konfigurierter Bypass nur für `GET /health`.
- Akzeptanzkriterien:
  - Ohne Token: alle geschützten Endpunkte `401`.
  - Mit ungültigem Token: `401`.
  - Mit gültigem Token: Context verfügbar.
- Tests:
  - `tests/api/test_authn.py` mit positiven/negativen Fällen.

### `W1-04` AuthZ Slice: Rollenmodell und Endpoint-Policies
- Priorität: `P0`
- Aufwand: `1 Tag`
- Scope:
  - Rollen `admin`, `operator`, `auditor`, `viewer`.
  - Policy-Mapping pro Endpoint:
    - `POST /runs`: `operator|admin`
    - `GET /passports/{run_id}`: `viewer|auditor|operator|admin`
    - `GET /profiles*`: `viewer+`
  - Einheitliche `403` Fehlerstruktur.
- Akzeptanzkriterien:
  - Rollenlose Requests werden abgewiesen.
  - Falsche Rolle bekommt `403`.
- Tests:
  - `tests/api/test_authz.py`

### `W1-05` Audit Events V1: unveränderbare Sicherheitsereignisse
- Priorität: `P0`
- Aufwand: `1 Tag`
- Scope:
  - Audit-Event-Schema (`event_id`, `ts`, `actor`, `tenant_id`, `action`, `resource`, `result`).
  - Event-Emission in `POST /runs`, `GET /passports/{run_id}`, `GET /profiles/{name}`.
  - JSONL Sink unter `reports/audit/events.log` (Übergangslösung).
- Akzeptanzkriterien:
  - Jede sensitive Aktion erzeugt Event mit Outcome (`allow|deny`).
  - Keine Secrets oder Rohprompts im Event.
- Tests:
  - `tests/api/test_audit_events.py`

### `W1-06` Tenant-Modell V1: run ownership vorbereiten
- Priorität: `P0`
- Aufwand: `1 Tag`
- Scope:
  - `run.json` um `tenant_id` erweitern.
  - `run_store` um tenant-scoped Hilfsfunktionen ergänzen.
  - Strikte Prüfung: Zugriff nur auf Run mit passender `tenant_id`.
- Akzeptanzkriterien:
  - Cross-Tenant Zugriff auf Run liefert `404` oder `403` (policy-konsistent).
  - Alte Runs ohne `tenant_id` sind über Migrationsregel behandelbar.
- Tests:
  - `tests/api/test_tenant_isolation.py`

### `W1-07` Migrationsstrategie für Legacy-Artefakte
- Priorität: `P1`
- Aufwand: `0.5 Tag`
- Scope:
  - Skript `scripts/migrate_run_tenant.py` für Backfill.
  - Mapping-Regel dokumentieren (`default tenant`, optional CSV-Mapping).
- Akzeptanzkriterien:
  - Dry-run + Apply-Modus.
  - Ergebnisreport mit Anzahl migrierter Runs.

### `W1-08` API-Fehlerkontrakt vereinheitlichen
- Priorität: `P1`
- Aufwand: `0.5 Tag`
- Scope:
  - Einheitliches Error-Format (`code`, `message`, `correlation_id`).
  - AuthN/AuthZ/Audit Fehler integrieren.
- Akzeptanzkriterien:
  - Konsistenter Fehlerbody für `401/403/404/422`.
- Tests:
  - Contract-Tests für Fehlerstruktur.

### `W1-09` Observability Baseline
- Priorität: `P1`
- Aufwand: `1 Tag`
- Scope:
  - Request-ID / Correlation-ID.
  - Basis-Metriken (`http_requests_total`, `http_request_duration_ms`).
  - Structured Logs mit `tenant_id`, `actor`, `route`.
- Akzeptanzkriterien:
  - Metriken auslesbar.
  - Logs maschinenlesbar (JSON).

### `W1-10` Threat-Model & Security-Docs aktualisieren
- Priorität: `P1`
- Aufwand: `0.5 Tag`
- Scope:
  - `docs/threat-model.md` um IAM/Tenant/Audit-Risiken erweitern.
  - `docs/transparency.md` um neue Sicherheitsgrenzen ergänzen.
- Akzeptanzkriterien:
  - Neue Trust-Boundaries und Abuse-Cases dokumentiert.

### `W1-11` CI-Gates für Security-Baseline
- Priorität: `P1`
- Aufwand: `0.5 Tag`
- Scope:
  - Tests für AuthN/AuthZ/Tenant in CI verpflichtend.
  - Fail-fast bei fehlenden Security-Tests.
- Akzeptanzkriterien:
  - `.github/workflows/ci.yml` führt neue Testgruppen aus.

### `W1-12` Demo-Szenario für Stakeholder
- Priorität: `P2`
- Aufwand: `0.5 Tag`
- Scope:
  - Scripted Demo: `401 -> 403 -> 200` sowie Audit-Event-Nachweis.
  - Kurze Runbook-Seite `docs/demo-authz.md`.
- Akzeptanzkriterien:
  - Demo in <10 Minuten reproduzierbar.

## Reihenfolge (Execution Plan)
1. `W1-01`, `W1-02`
2. `W1-03`, `W1-04`
3. `W1-05`, `W1-06`
4. `W1-07`, `W1-08`
5. `W1-09`, `W1-10`
6. `W1-11`, `W1-12`

## Kritischer Pfad
- `W1-01` -> `W1-03` -> `W1-04` -> `W1-06` -> `W1-11`

## Definition of Done (Sprint)
- Alle `P0` Issues sind umgesetzt und getestet.
- Mindestens 90% Testabdeckung auf neue Security-Pfade.
- Kein unautorisierter Zugriff auf geschützte Endpunkte möglich.
- Audit-Events für sensitive Aktionen vollständig vorhanden.
- Dokumentation für Betrieb und Security aktualisiert.

## Risiko-Register (Sprint-spezifisch)
- Risiko: OIDC-Integration blockiert durch fehlenden IdP.
  - Mitigation: lokaler JWT-Test-Provider + JWKS-Stub.
- Risiko: Legacy-Runs ohne Tenant brechen Zugriffspfade.
  - Mitigation: Backfill-Skript + kompatible Fallback-Regel.
- Risiko: Scope Creep in Richtung kompletter Worker-Architektur.
  - Mitigation: Sprint strikt auf Security-Foundation begrenzen.

## Konkrete Deliverables bis Sprint-Ende
- `docs/adr/ADR-001-enterprise-architecture.md`
- AuthN/AuthZ Codepfade in API
- Tenant-Checks auf Run-Ressourcen
- Audit-Event V1 Logger + Tests
- Aktualisierte CI und Security-Dokumentation
