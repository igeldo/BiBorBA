# Agentic RAG mit LangGraph

## Inhaltsverzeichnis

1. [Projektübersicht](#projektübersicht)
2. [Voraussetzungen](#voraussetzungen)
3. [Installation](#installation)
4. [System starten](#system-starten)
5. [Kollektionen vorbereiten](#kollektionen-vorbereiten)
6. [StackOverflow Scraping](#stackoverflow-scraping)
7. [Nutzung: Einzelabfragen](#nutzung-einzelabfragen)
8. [Nutzung: Batch-Queries](#nutzung-batch-queries)
9. [Auswertung und Evaluierung](#auswertung-und-evaluierung)
10. [Projektstruktur](#projektstruktur)
11. [Troubleshooting](#troubleshooting)
12. [Konfiguration](#konfiguration)
13. [Embedding-Modell wechseln](#embedding-modell-wechseln)

---

## Projektübersicht

Das System implementiert drei verschiedene RAG-Architekturen:

| Graph-Typ | Beschreibung |
|-----------|--------------|
| **Pure LLM** | Direkte LLM-Antwort ohne Retrieval (Baseline) |
| **Simple RAG** | Klassisches RAG: Retrieve → Generate |
| **Adaptive RAG** | Agentic RAG mit Dokumentenbewertung, Halluzinationserkennung und Query-Rewriting |

### Adaptive RAG Workflow

```
START → retrieve → grade_documents → [relevant?]
                                         │
                    ┌────────────────────┴────────────────────┐
                    ↓                                          ↓
              [documents OK]                          [transform_query]
                    ↓                                          │
                generate → [hallucination check] ←────────────┘
                    ↓
            [answer grading] → END
```

Der adaptive Graph führt iterative Verbesserungen durch:
- **Dokumenten-Grading**: Prüft Relevanz der abgerufenen Dokumente
- **Halluzinations-Check**: Verifiziert, dass Antworten im Kontext verankert sind
- **Query-Rewriting**: Optimiert Suchanfragen bei schlechten Ergebnissen

---

## Schnellstart (Mac)

### Voraussetzungen

1. **Docker Desktop** installieren und starten
2. **Ollama** von [ollama.ai/download](https://ollama.ai/download) installieren
3. Ollama starten (erscheint in der Menüleiste)

### Starten

```bash
# Repository klonen
git clone <repository-url>
cd BiBorBA

# Start-Skript ausführen
chmod +x start.sh
./start.sh
```

Das Skript führt automatisch folgende Schritte aus:
1. Prüft ob Ollama läuft
2. Lädt fehlende Ollama-Modelle herunter** (`embeddinggemma`, `gemma3:12b` - ca. 8GB, kann einige Minuten dauern)
3. Startet alle Docker-Container (PostgreSQL, ChromaDB, FastAPI)
4. Installiert Frontend-Dependencies (falls nötig)
5. Startet das Frontend

**Nach dem Start:** http://localhost:5173

---

## Voraussetzungen

### Benötigte Software

| Software | Version | Zweck                                                    |
|----------|---------|----------------------------------------------------------|
| **Docker & Docker Compose** | Latest | Backend-Services (PostgreSQL, ChromaDB)                  |
| **Node.js** | 18+ | Frontend-Entwicklung (optional, für lokale Entwicklung)  |
| **Python** | 3.11+ | Backend-Entwicklung (optional, für lokale Entwicklung)   |
| **Ollama** | Latest | LLM- und Embedding-Modelle                               |

### Ollama Modelle

Das System benötigt zwei Ollama-Modelle:

| Funktion | Modell | Installation |
|----------|--------|--------------|
| **Embedding** | `embeddinggemma:latest` | `ollama pull embeddinggemma` |
| **Chat/Grader/Rewriter** | `gemma3:12b` | `ollama pull gemma3:12b` |

Die Modelle werden in `langgraph-rag/app/config.py` konfiguriert:

```python
ollama_models: Dict[str, str] = Field(default={
    "embedding": "embeddinggemma:latest",
    "chat": "gemma3:12b",
    "grader": "gemma3:12b",
    "rewriter": "gemma3:12b"
})
```

### Ollama Port

**Wichtig:** Ollama muss auf Port **11434** erreichbar sein (Standard-Port). Das Backend verbindet sich mit `http://localhost:11434`. Falls Ollama auf einem anderen Port läuft, muss die Umgebungsvariable `OLLAMA_BASE_URL` in `langgraph-rag/.env` angepasst werden.

---

## Installation

### 1. Repository klonen

```bash
git clone <repository-url>
cd BiBorBA
```

### 2. Ollama installieren und einrichten

#### macOS / Linux (empfohlen)

1. Lade Ollama von [https://ollama.ai/download](https://ollama.ai/download) herunter und installiere es
2. Starte Ollama (läuft als Hintergrundprozess)
3. Installiere die benötigten Modelle:

```bash
ollama pull embeddinggemma
ollama pull gemma3:12b
```

4. Verifiziere die Installation:

```bash
ollama list
# Sollte beide Modelle anzeigen

# Prüfe, ob Ollama auf Port 11434 läuft
curl http://localhost:11434/api/tags
```

#### Windows mit NVIDIA GPU (Docker-Variante)

Für Windows-Nutzer mit NVIDIA-Grafikkarte kann Ollama auch als Docker-Container laufen:

1.Starte Ollama mit Docker:

```bash
cd langgraph-rag
docker-compose --profile ollama up -d
```

2. Installiere die Modelle im Container:

```bash
docker exec langgraph_ollama ollama pull embeddinggemma
docker exec langgraph_ollama ollama pull gemma3:12b
```

### 3. Backend-Dependencies (nur für lokale Entwicklung)

> **Hinweis:** Dieser Schritt ist nur nötig, wenn Sie das Backend außerhalb von Docker entwickeln möchten. Für normales Ausführen überspringen Sie diesen Schritt.

Das Backend verwendet `uv` als Paketmanager:

```bash
cd langgraph-rag

# uv installieren (falls nicht vorhanden)
pip install uv

# Dependencies installieren
uv sync
```

### 4. Frontend-Dependencies (automatisch bei start.sh)

> **Hinweis:** Das Start-Skript installiert diese automatisch. Nur manuell nötig bei Problemen.

```bash
cd frontend
npm install
```

---

## System starten

### Schnellstart mit Shell-Skripten

Das Projekt enthält Skripte für einen einfachen Start:

#### macOS / Linux

```bash
# Ausführbar machen (nur beim ersten Mal)
chmod +x start.sh stop.sh

# System starten
./start.sh
```

#### Windows (PowerShell)

```powershell
.\start.ps1
```

#### Windows mit Ollama Docker Container

```powershell
.\start.ps1 -ollama
```

### Was das Start-Skript macht

1. Prüft, ob Ollama läuft
2. Installiert fehlende Ollama-Modelle automatisch
3. Startet Docker-Container (PostgreSQL, ChromaDB, FastAPI)
4. Installiert Frontend-Dependencies (falls nötig)
5. Startet den Vite-Entwicklungsserver
6. Wartet, bis alle Services bereit sind

### Nach dem Start verfügbare Services

| Service | URL | Beschreibung |
|---------|-----|--------------|
| Frontend | http://localhost:5173 | React-Benutzeroberfläche |
| Backend API | http://localhost:8000 | FastAPI-Backend |
| API Dokumentation | http://localhost:8000/docs | Swagger UI |
| Ollama | http://localhost:11434 | LLM-Server (muss separat laufen) |
| ChromaDB | http://localhost:8002 | Vector Store |
| PostgreSQL | localhost:5432 | Datenbank |

### System beenden

#### macOS / Linux

```bash
./stop.sh
```

#### Windows

```powershell
.\stop.ps1
```
**Hinweis:** Ollama muss separat beendet werden (über die Menüleiste oder `docker-compose --profile ollama down`).

#### Windows mit Ollama Docker Container

```powershell
.\stop.ps1 -ollama
```


---

## Kollektionen vorbereiten

Bevor Abfragen durchgeführt werden können, müssen Dokumenten-Kollektionen erstellt und mit Daten gefüllt werden. Die Kollektionsverwaltung erfolgt über den Tab **Collection Management** im Frontend.

### Kollektionstypen

Das System unterstützt zwei Arten von Kollektionen:

| Typ | Beschreibung |
|-----|--------------|
| **stackoverflow** | StackOverflow Q&A-Paare als Wissensbasis |
| **pdf** | PDF-Dokumente (z.B. SQL-Dokumentation) |

### Neue Kollektion erstellen

1. Navigiere zum Tab **Collection Management**
2. Klicke auf **+ New Collection** in der linken Seitenleiste
3. Fülle das Formular aus:
   - **Collection Name**: Ein aussagekräftiger Name (z.B. "SQL Training Set")
   - **Description**: Optionale Beschreibung
   - **Collection Type**: Wähle zwischen "StackOverflow Questions" oder "PDF Documents"
4. Klicke auf **Create**

### Fragen zu einer StackOverflow-Kollektion hinzufügen

1. Wähle die gewünschte Kollektion in der linken Seitenleiste aus
2. Wechsle zum Tab **Add Questions**
3. Die Tabelle zeigt alle verfügbaren Fragen, die noch nicht in der Kollektion sind
4. Nutze die Filter-Optionen:
   - **Filter by Tags**: Komma-getrennte Tags (z.B. "mysql, postgresql")
   - **Min Score**: Nur Fragen mit Mindest-Score anzeigen
   - **Sortierung**: Nach Score oder Views sortieren
5. Wähle Fragen aus:
   - Einzeln per Checkbox
   - **Select All** für alle auf der aktuellen Seite
6. Klicke auf **Add Selected (n)** um die Fragen hinzuzufügen

### PDF-Dokumente hinzufügen

1. Lege PDF-Dateien im Ordner `langgraph-rag/resources/documents/` ab
2. Wähle eine PDF-Kollektion aus
3. Wechsle zum Tab **Add Documents**
4. Alle verfügbaren PDFs werden angezeigt
5. Wähle die gewünschten Dokumente aus
6. Klicke auf **Add Selected**

### Kollektion neu aufbauen (Rebuild)

Nach dem Hinzufügen oder Entfernen von Inhalten muss die ChromaDB-Vektorkollektion aktualisiert werden:

1. Wähle die Kollektion aus
2. Klicke auf **Rebuild ChromaDB** (orangefarbener Button)
3. Warte, bis der Rebuild abgeschlossen ist (Statusanzeige)

**Wichtig:** Ohne Rebuild werden neue Inhalte nicht für Abfragen verfügbar sein.

### Statistiken und Status

Die Kollektionsübersicht zeigt:
- **Questions/Documents**: Anzahl der Einträge
- **Avg Score**: Durchschnittlicher Score (bei StackOverflow)
- **Avg Views**: Durchschnittliche Aufrufe
- **Last Rebuilt**: Zeitpunkt des letzten Rebuilds

---

## StackOverflow Scraping

Das System kann SQL-bezogene Fragen und Antworten direkt von der StackOverflow API laden. Das Scraping erfolgt über den Tab **Data** im Frontend.

### API-Verbindung testen

Bevor mit dem Scraping begonnen wird, sollte die API-Verbindung getestet werden:

1. Navigiere zum Tab **Data** (Stackoverflow Data Management)
2. Klicke auf **Test API Connection** (grüner Button)
3. Bei erfolgreicher Verbindung wird angezeigt:
   - **API Status**: Connected
   - **Quota Remaining**: Verbleibende API-Aufrufe (StackOverflow limitiert auf 300/Tag ohne API-Key)

### Scraping starten

1. Im Tab **Data** unter **Scrape New Data**:
2. Konfiguriere die Parameter:
   - **Count (1-1000)**: Anzahl der zu ladenden Fragen (z.B. 100)
   - **Days Back (1-3650)**: Zeitraum in Tagen (z.B. 365 für das letzte Jahr)
   - **Min Score**: Minimaler Score der Fragen (z.B. 5 für qualitativ hochwertige Fragen)
   - **Tags**: Komma-getrennte Tags (z.B. "sql, mysql, postgresql")
   - **Start Page**: Startseite für Fortsetzung eines vorherigen Scrapings (100 Fragen pro Seite)
   - **Only accepted answers**: Checkbox für Fragen mit akzeptierter Antwort
3. Klicke auf **Start Scraping** (orangefarbener Button)

### Scraping-Fortschritt

Nach dem Start wird der Fortschritt live angezeigt:
- **Job Status**: running / completed / failed
- **Questions**: Anzahl abgerufener und gespeicherter Fragen
- **Answers**: Anzahl abgerufener und gespeicherter Antworten
- **Errors**: Fehleranzahl (falls vorhanden)

Nach Abschluss erscheint eine grüne Erfolgsmeldung mit der Anzahl gespeicherter Fragen und Antworten.

### Gespeicherte Fragen durchsuchen

Im Bereich **Browse Questions** können alle gespeicherten Fragen durchsucht werden:

1. **Filter by Tags**: Nach Tags filtern
2. **Min Score**: Mindest-Score
3. **Sort By**: Sortierung nach Erstellungsdatum, Score oder Views
4. **Order**: Auf- oder absteigende Sortierung

Die Tabelle zeigt:
- Titel (mit Link zu StackOverflow)
- Tags
- Score
- Views
- Anzahl Antworten
- Erstellungsdatum

### Scraping-Statistiken

Im oberen Bereich werden Gesamtstatistiken angezeigt:
- **Total Questions**: Gesamtzahl gespeicherter Fragen
- **Total Answers**: Gesamtzahl gespeicherter Antworten
- **Accepted Answers**: Anzahl akzeptierter Antworten
- **Avg Question Score**: Durchschnittlicher Score

### Tipps für effektives Scraping

- **Qualität vor Quantität**: Nutze `min_score: 5` oder höher für bessere Fragen
- **Tag-Fokus**: Spezifische Tags wie "mysql" oder "postgresql" liefern gezieltere Ergebnisse
- **API-Quota beachten**: Ohne API-Key sind 300 Anfragen/Tag möglich

---

## Nutzung: Einzelabfragen

Einzelabfragen werden über den Tab **Query** im Frontend durchgeführt.

### Abfrage stellen

1. Navigiere zum Tab **Query** (Standard-Ansicht)
2. Fülle das Formular aus:
   - **Your Question**: Die SQL-bezogene Frage eingeben
   - **Session ID**: Wird automatisch generiert, kann aber angepasst werden
   - **Temperature (0-1)**: Kreativität des LLM (0 = deterministisch, 1 = kreativ)

### Graph-Typ auswählen

Wähle den gewünschten Graph-Typ aus dem Dropdown:

| Graph-Typ | Beschreibung |
|-----------|--------------|
| **Adaptive RAG** | Vollständig mit Grading & Rewriting (empfohlen) |
| **Simple RAG** | Nur Retrieval + Generation |
| **Pure LLM** | Kein Retrieval - Baseline für Vergleiche |

### Kollektionen auswählen

Unter dem Graph-Typ-Dropdown können eine oder mehrere Kollektionen ausgewählt werden:
- Klicke auf die gewünschten Kollektionen (Mehrfachauswahl möglich)
- Ohne Auswahl wird der Standard-StackOverflow-Retriever verwendet

### Abfrage absenden

Klicke auf **Submit Query**. Während der Verarbeitung wird ein Ladeindikator angezeigt.

### Ergebnis-Anzeige

Nach der Verarbeitung wird angezeigt:

1. **Antwort**: Die generierte Antwort
2. **Rewritten Question** (falls angewendet): Zeigt Original- und optimierte Frage
3. **Disclaimer** (falls vorhanden): Warnhinweis bei Qualitätsproblemen
4. **Bewertung**: Sterne-Rating (1-5) zur Qualitätsbewertung
5. **Metadaten**:
   - Documents Retrieved: Anzahl abgerufener Dokumente
   - Graph Type: Verwendeter Graph-Typ
   - Processing Time: Verarbeitungszeit in ms
   - Session ID: Eindeutige Sitzungs-ID

### Graph Iteration Metrics

Bei Adaptive RAG werden zusätzlich angezeigt:
- **Total Iterations**: Anzahl der Durchläufe
- **Generation Attempts**: Generierungsversuche
- **Transform Attempts**: Query-Rewriting-Versuche

### Retrieved Documents

Alle abgerufenen Dokumente werden aufgelistet:
- Klicke auf ein Dokument, um den vollständigen Inhalt anzuzeigen
- Zeigt Quelle (PDF/StackOverflow), Score und Metadaten

### Graph Trace

Die Visualisierung zeigt den Ablauf durch den Graph:
- Jeder Knoten wird mit Nummer und Timing angezeigt
- Zeigt den tatsächlichen Pfad der Verarbeitung

### Antwort bewerten

Nach Erhalt einer Antwort:
1. Klicke auf die Sterne (1-5) im **Rate this answer**-Bereich
2. Die Bewertung wird automatisch gespeichert

---

## Nutzung: Batch-Queries

Batch-Queries ermöglichen die automatisierte Verarbeitung mehrerer StackOverflow-Fragen mit anschließender Evaluierung. Die Batch-Verarbeitung erfolgt über den Tab **Batch** im Frontend.

### Fragen auswählen

1. Navigiere zum Tab **Batch** (Batch Query Processing)
2. Die Tabelle zeigt alle verfügbaren StackOverflow-Fragen
3. Nutze die Filter:
   - **Filter by Tags**: Nach Tags filtern (z.B. "mysql, sql")
   - **Min Score**: Mindest-Score
   - **Sort By**: Sortierung nach Datum, Score oder Views
   - **Show only questions not in collections**: Nur Fragen ohne Kollektionszugehörigkeit
4. Wähle Fragen aus (max. 50):
   - Einzeln per Checkbox
   - Alle auf der Seite über die Header-Checkbox
5. Der Zähler zeigt die Auswahl: "X / 50 selected"

### Kollektionen für Retrieval auswählen

Im Bereich **Select Collections for Retrieval**:
1. Klicke auf die gewünschten Kollektionen
2. Mehrfachauswahl ist möglich
3. Ohne Auswahl wird der Standard-StackOverflow-Retriever verwendet

### Graph-Typen auswählen

Im Bereich **Graph Types to Execute**:
1. Wähle einen oder mehrere Graph-Typen:
   - **Adaptive RAG**: Vollständig mit Grading & Rewriting
   - **Simple RAG**: Nur Retrieval + Generation
   - **Pure LLM**: Kein Retrieval - Baseline
2. Die Anzeige zeigt die Gesamtzahl der Ausführungen:
   - z.B. "10 Fragen × 2 Graph-Typen = 20 Ausführungen"

### Batch starten

1. Klicke auf **Start Batch (n)**
2. Das System wechselt automatisch zur Fortschrittsansicht

**Hinweis:** Es kann immer nur ein Batch-Job gleichzeitig laufen. Falls bereits ein Job läuft, wird eine Warnung angezeigt.

### Fortschritt verfolgen

Nach dem Start zeigt die Fortschrittsansicht:
- **Progress Bar**: Visueller Fortschritt
- **Status**: Running / Completed / Failed
- **Aktuelle Frage**: Titel der gerade verarbeiteten Frage
- **Statistiken**: Verarbeitet, Erfolgreich, Fehlgeschlagen

### Ergebnisse analysieren

Nach Abschluss werden die Ergebnisse tabellarisch angezeigt:

| Spalte | Beschreibung |
|--------|--------------|
| Question | Titel der StackOverflow-Frage |
| Graph Type | Verwendeter Graph-Typ |
| Generated Answer | Generierte Antwort (Vorschau) |
| Reference Answer | Akzeptierte StackOverflow-Antwort |
| BERT F1 | Semantische Ähnlichkeit (0-1) |
| Processing Time | Verarbeitungszeit in ms |

### Batch abbrechen

Während der Verarbeitung kann der Job über **Cancel Job** abgebrochen werden.

---

## Auswertung und Evaluierung

Das System bietet mehrere Mechanismen zur Qualitätsbewertung der generierten Antworten.

### BERT-Score

Der BERT-Score misst die semantische Ähnlichkeit zwischen generierter und Referenz-Antwort. Bei Batch-Queries wird der BERT-Score automatisch berechnet, wenn eine Referenz-Antwort (akzeptierte StackOverflow-Antwort) vorhanden ist.

### Interpretation der BERT-Scores

| F1-Score | Bewertung | Beschreibung |
|----------|-----------|--------------|
| > 0.85 | Ausgezeichnet | Hohe semantische Übereinstimmung |
| 0.70 - 0.85 | Gut | Gute Übereinstimmung mit Referenz |
| 0.50 - 0.70 | Mittelmäßig | Teilweise Übereinstimmung |
| < 0.50 | Niedrig | Geringe Ähnlichkeit zur Referenz |

### Manuelle Bewertung

Bei Einzelabfragen kann jede Antwort manuell bewertet werden:

1. Nach Erhalt einer Antwort im **Query**-Tab
2. Klicke auf die Sterne (1-5) im Bewertungsbereich
3. Die Bewertung wird automatisch gespeichert und der Session zugeordnet

### Auswertungsworkflow für Experimente

Für systematische Evaluierungen wird folgender Workflow empfohlen:

#### 1. Daten sammeln
- Navigiere zum Tab **Data**
- Scrape StackOverflow-Fragen mit hohem Score (z.B. min_score: 10)
- Fokussiere auf spezifische Tags (z.B. "mysql", "postgresql")

#### 2. Training Set erstellen
- Navigiere zum Tab **Collection Management**
- Erstelle eine neue Kollektion (z.B. "SQL Training Set")
- Füge qualitativ hochwertige Fragen hinzu
- Führe einen Rebuild durch

#### 3. Test Set definieren
- Im **Batch**-Tab: Aktiviere "Show only questions not in collections"
- Diese Fragen dienen als ungesehene Testdaten

#### 4. Batch-Evaluation durchführen
- Wähle Test-Fragen aus
- Wähle die Training-Kollektion für Retrieval
- Aktiviere mehrere Graph-Typen für Vergleiche
- Starte den Batch

#### 5. Ergebnisse analysieren
Nach Abschluss des Batch-Jobs:
- Vergleiche BERT-Scores zwischen Graph-Typen
- Identifiziere Fragen mit niedrigen Scores
- Analysiere, ob Adaptive RAG besser abschneidet als Simple RAG

### Vergleich der Graph-Typen

Der Tab **Comparison** ermöglicht den direkten Vergleich der Ergebnisse verschiedener Graph-Typen für dieselbe Frage:

1. Navigiere zum Tab **Comparison**
2. Wähle eine abgeschlossene Batch-Session
3. Die Tabelle zeigt für jede Frage:
   - Ergebnisse aller verwendeten Graph-Typen nebeneinander
   - BERT-Scores für jeden Ansatz
   - Verarbeitungszeiten

### Metriken-Übersicht

Bei Batch-Evaluierungen werden folgende Metriken erfasst:

| Metrik | Beschreibung |
|--------|--------------|
| **BERT Precision** | Wie viel der generierten Antwort in der Referenz enthalten ist |
| **BERT Recall** | Wie viel der Referenz in der generierten Antwort abgedeckt wird |
| **BERT F1** | Harmonisches Mittel aus Precision und Recall |
| **Processing Time** | Gesamtverarbeitungszeit in Millisekunden |
| **Iterations** | Anzahl der Graph-Durchläufe (nur Adaptive RAG) |

---

## Projektstruktur

```
BiBorBA/
├── langgraph-rag/           # Backend (Python/FastAPI)
│   ├── app/
│   │   ├── api/             # API-Routen
│   │   │   ├── routes/      # Endpoint-Definitionen
│   │   │   └── schemas/     # Pydantic-Schemas
│   │   ├── core/            # LangGraph-Kernlogik
│   │   │   └── graph/       # Graph-Definitionen
│   │   │       ├── nodes/   # Retrieve, Generate, Grade, Rewrite
│   │   │       └── tools/   # Dokumenten-Loader
│   │   ├── services/        # Business-Logik
│   │   ├── evaluation/      # BERT-Score, Metriken
│   │   └── tests/           # Unit-Tests
│   ├── resources/
│   │   └── documents/       # PDF-Dokumente
│   ├── docker-compose.yml   # Docker-Services
│   ├── pyproject.toml       # Python-Dependencies
│   └── .env                 # Umgebungsvariablen
│
├── frontend/                # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── components/      # UI-Komponenten
│   │   ├── services/        # API-Client
│   │   └── types/           # TypeScript-Typen
│   └── package.json
│
├── start.sh                 # Start-Skript (Unix)
├── start.ps1                # Start-Skript (Windows)
├── stop.sh                  # Stop-Skript (Unix)
└── stop.ps1                 # Stop-Skript (Windows)
```

---

## Troubleshooting

### Ollama nicht erreichbar

**Problem:** `Error: Ollama is not running!`

**Lösung:**
```bash
# Prüfen ob Ollama läuft
curl http://localhost:11434/api/tags

# Falls nicht, Ollama starten
ollama serve
```

### Modelle fehlen

**Problem:** Modelle `embeddinggemma` oder `gemma3:12b` nicht gefunden

**Lösung:**
```bash
ollama pull embeddinggemma
ollama pull gemma3:12b
```

### Port bereits belegt

**Problem:** `Error: Port 8000/5173/5432 already in use`

**Lösung:**
```bash
# macOS/Linux - Prozess finden und beenden
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Docker-Container starten nicht

**Problem:** Container-Fehler beim Start

**Lösung:**
```bash
cd langgraph-rag

# Logs prüfen
docker-compose logs app

# Container neu bauen
docker-compose down -v
docker-compose up --build
```

### ChromaDB Verbindungsprobleme

**Problem:** Vector Store nicht erreichbar

**Lösung:**
```bash
# ChromaDB-Container prüfen
docker-compose ps chroma

# Neustarten
docker-compose restart chroma
```

### Frontend lädt nicht

**Problem:** Leere Seite oder Fehler

**Lösung:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

## Konfiguration

Die Hauptkonfiguration erfolgt über `langgraph-rag/.env`:

```env
# Datenbank
DATABASE_URL=postgresql://postgres:password@localhost:5432/langgraph_rag

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Vector Store
CHROMA_PERSIST_DIR=./data/chroma

# Text-Verarbeitung
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Features
STACKOVERFLOW_ENABLED=true
ENABLE_MULTI_SOURCE_RETRIEVAL=true
ENABLE_RESULT_CACHING=true
```

---

## Embedding-Modell wechseln

### Warum ist das wichtig?

Jedes Embedding-Modell erzeugt **semantisch unterschiedliche Vektoren**. Ein Text, der mit `nomic-embed-text` eingebettet wurde, ist **nicht kompatibel** mit Vektoren von `embeddinggemma`.

Das bedeutet:
- Query-Embedding (neues Modell) findet keine relevanten Dokumente in Collections (altes Modell)
- Similarity-Search liefert falsche/irrelevante Ergebnisse
- Die RAG-Qualität sinkt drastisch

**Konsequenz:** Bei einem Modellwechsel müssen alle ChromaDB-Collections neu erstellt werden.

### Migrations-Schritte

#### 1. Neues Modell in Ollama installieren

```bash
# Verfügbare Embedding-Modelle anzeigen
ollama list | grep -i embed

# Neues Modell pullen
ollama pull embeddinggemma

# Prüfen ob Embedding-Capability vorhanden
ollama show embeddinggemma:latest
# Sollte "embedding" unter "Capabilities" zeigen
```

#### 2. Konfiguration anpassen

In `langgraph-rag/app/config.py`:

```python
ollama_models: Dict[str, str] = Field(default={
    "embedding": "embeddinggemma:latest",  # Hier ändern
    # ...
})
```

#### 3. Bestehende Collections löschen

**WICHTIG:** Dieser Schritt ist obligatorisch!

```bash
# Server stoppen (falls aktiv)

# ChromaDB-Daten löschen
rm -rf langgraph-rag/data/chroma/*

# Oder spezifische Collection via API löschen (wenn Server läuft)
curl -X DELETE http://localhost:8000/api/collections/pdf_collection
curl -X DELETE http://localhost:8000/api/collections/stackoverflow_collection
```

Die PostgreSQL-Tabelle `document_embeddings` muss nicht manuell bereinigt werden - Einträge werden bei Neuerstellung automatisch aktualisiert.

#### 4. Server neu starten

```bash
cd langgraph-rag
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. Collections neu erstellen

Die Collections werden automatisch neu erstellt, wenn:
- Eine Query mit dem entsprechenden Retriever-Typ ausgeführt wird
- Dokumente über die API hochgeladen werden

```bash
# Health-Check (testet auch Embedding-Modell)
curl http://localhost:8000/health
```

### Unterstützte Embedding-Modelle

| Modell | Dimensionen | Kontext | Hinweise |
|--------|-------------|---------|----------|
| `embeddinggemma:latest` | 768 | 2048 tokens | Gemma3-basiert, empfohlen |
| `nomic-embed-text` | 768 | 2048 tokens | BERT-basiert, bewährt |
| `mxbai-embed-large` | 1024 | 512 tokens | Größere Dimensionen |

**Anforderungen an Embedding-Modelle:**
- Muss "embedding" Capability haben (prüfen mit `ollama show`)
- Kontext-Länge >= 2048 tokens empfohlen
- Dimensionen sind flexibel (ChromaDB unterstützt verschiedene)

---

## API-Dokumentation

Nach dem Start ist die vollständige API-Dokumentation verfügbar:

- **Swagger UI**: http://localhost:8000/docs

---

## Lizenz

Dieses Projekt ist Teil einer Abschlussarbeit zum Thema "Agentic RAG mit LangGraph".
