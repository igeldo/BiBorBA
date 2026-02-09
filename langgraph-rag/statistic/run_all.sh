#!/bin/bash
# ==========================================================
# Gesamte Analyse-Pipeline ausführen
# ==========================================================
# Dieses Skript führt alle vier Analyseschritte nacheinander aus.
#
# Voraussetzungen:
#   pip install pandas numpy scipy matplotlib seaborn
#
# Verwendung:
#   chmod +x run_all.sh
#   ./run_all.sh pfad/zur/export_full_2026-02-08_final.csv
# ==========================================================

set -e

INPUT_FILE="${1:-export_full_2026-02-08_final.csv}"
OUTPUT_DIR="./ergebnisse"
PLOTS_DIR="$OUTPUT_DIR/plots"

echo "============================================"
echo "  Bachelorarbeit Analyse-Pipeline"
echo "============================================"
echo "  Eingabe: $INPUT_FILE"
echo "  Ausgabe: $OUTPUT_DIR"
echo ""

# Verzeichnisse erstellen
mkdir -p "$OUTPUT_DIR" "$PLOTS_DIR"

# Schritt 1: Datenbereinigung
echo "▶ Schritt 1/4: Datenbereinigung..."
python3 01_datenbereinigung.py \
    --input "$INPUT_FILE" \
    --output "$OUTPUT_DIR/cleaned_data.csv"
echo ""

# Schritt 2: Statistische Analyse
echo "▶ Schritt 2/4: Statistische Analyse..."
python3 02_statistische_analyse.py \
    --input "$OUTPUT_DIR/cleaned_data.csv" \
    | tee "$OUTPUT_DIR/analyse_ergebnisse.txt"
echo ""

# Schritt 3: Judge-Vergleich
echo "▶ Schritt 3/4: Bewertungsmodell-Vergleich..."
python3 03_judge_vergleich.py \
    --main "$OUTPUT_DIR/cleaned_data.csv" \
    --comparison "$OUTPUT_DIR/judge_comparison_data.csv" \
    | tee "$OUTPUT_DIR/judge_vergleich.txt" 2>/dev/null || echo "  (Übersprungen - keine Vergleichsdaten)"
echo ""

# Schritt 4: Visualisierungen
echo "▶ Schritt 4/4: Visualisierungen..."
python3 04_visualisierungen.py \
    --input "$OUTPUT_DIR/cleaned_data.csv" \
    --output "$PLOTS_DIR"
echo ""

echo "============================================"
echo "  ✅ Pipeline abgeschlossen!"
echo "  Ergebnisse in: $OUTPUT_DIR"
echo "============================================"
