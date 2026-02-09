"""Datenbereinigung und Validierung des Rohdatensatzes."""

import argparse
import os

import pandas as pd


def load_and_validate(filepath: str) -> pd.DataFrame:
    """Lädt die CSV-Datei und führt grundlegende Validierung durch."""
    print(f"Lade Datensatz: {filepath}")
    df = pd.read_csv(filepath)
    print(f"   → {len(df)} Zeilen, {len(df.columns)} Spalten geladen")
    print(f"   → {df['question_id'].nunique()} einzigartige Fragen")
    return df


def check_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Prüft und dokumentiert fehlende Werte."""
    print("\nFehlende Werte:")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_report = pd.DataFrame({
        'Fehlend': missing,
        'Prozent': missing_pct
    })
    missing_report = missing_report[missing_report['Fehlend'] > 0]
    if len(missing_report) > 0:
        print(missing_report.to_string())
    else:
        print("   Keine fehlenden Werte gefunden!")
    return df


def validate_score_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Validiert, dass Scores im erwarteten Bereich liegen."""
    print("\nScore-Validierung:")

    bert_valid = df['bert_f1'].between(0, 1).all()
    print(f"   BERT F1 im Bereich [0,1]: {'OK' if bert_valid else 'FEHLER'}")

    llm_valid = df['llm_correctness_score'].between(0, 1).all()
    print(f"   LLM Correctness im Bereich [0,1]: {'OK' if llm_valid else 'FEHLER'}")

    time_valid = (df['processing_time_ms'] > 0).all()
    print(f"   Processing Time > 0: {'OK' if time_valid else 'FEHLER'}")

    invalid_mask = (
        ~df['bert_f1'].between(0, 1) |
        ~df['llm_correctness_score'].between(0, 1) |
        (df['processing_time_ms'] <= 0)
    )
    n_invalid = invalid_mask.sum()
    if n_invalid > 0:
        print(f"   WARNUNG: {n_invalid} Zeilen mit ungültigen Werten gefunden")
        df = df[~invalid_mask].copy()
        print(f"   → Nach Bereinigung: {len(df)} Zeilen")
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardisiert Spaltenwerte für konsistente Analyse."""
    print("\nStandardisierung:")

    graph_type_map = {
        'adaptive_rag': 'Adaptive RAG',
        'simple_rag': 'Simple RAG',
        'pure_llm': 'Pure LLM'
    }
    df['architecture'] = df['graph_type'].map(graph_type_map)
    print(f"   Architekturen: {df['architecture'].value_counts().to_dict()}")

    llm_model_map = {
        'gemma3:12b': 'Gemma 3 12B',
        'gemma3:4b': 'Gemma 3 4B',
        'llama3.1:8b': 'Llama 3.1 8B'
    }
    df['model_name'] = df['llm_model'].map(llm_model_map)

    embedding_map = {
        'embeddinggemma:latest': 'embeddinggemma',
        'nomic-embed-text:latest': 'nomic-embed-text'
    }
    df['embedding_name'] = df['embedding_model'].map(embedding_map)

    df['processing_time_s'] = df['processing_time_ms'] / 1000

    df['judge_model'] = df['llm_correctness_model'].map(llm_model_map)

    print(f"   Modelle: {df['model_name'].value_counts().to_dict()}")
    print(f"   Embeddings: {df['embedding_name'].value_counts().to_dict()}")

    return df


def identify_duplicate_evaluations(df: pd.DataFrame) -> pd.DataFrame:
    """Identifiziert und behandelt doppelte Evaluationen."""
    print("\nDuplikat-Prüfung:")

    key_cols = ['question_id', 'graph_type', 'llm_model', 'embedding_model']
    duplicates = df[df.duplicated(subset=key_cols, keep=False)]

    if len(duplicates) > 0:
        n_dup_groups = duplicates.groupby(key_cols).ngroups
        print(f"   WARNUNG: {len(duplicates)} Zeilen in {n_dup_groups} Duplikat-Gruppen")
        print("   → Behalte jeweils die neueste Evaluation (nach created_at)")
        df = df.sort_values('created_at').drop_duplicates(subset=key_cols, keep='last')
        print(f"   → Nach Deduplizierung: {len(df)} Zeilen")
    else:
        print("   Keine Duplikate gefunden")

    return df


def separate_judge_comparison_data(df: pd.DataFrame):
    """Trennt die Daten für die Bewertungsmodell-Vergleichsanalyse."""
    print("\nBewertungsmodell-Trennung:")

    main_df = df[df['llm_correctness_model'] == 'gemma3:12b'].copy()
    print(f"   Hauptdatensatz (Gemma-Judge): {len(main_df)} Zeilen")

    comparison_df = df[df['llm_correctness_model'] == 'llama3.1:8b'].copy()
    print(f"   Vergleichsdatensatz (Llama-Judge): {len(comparison_df)} Zeilen")

    return main_df, comparison_df


def generate_summary(df: pd.DataFrame):
    """Gibt eine Zusammenfassung des bereinigten Datensatzes aus."""
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG DES BEREINIGTEN DATENSATZES")
    print("=" * 60)
    print(f"   Gesamtzeilen: {len(df)}")
    print(f"   Einzigartige Fragen: {df['question_id'].nunique()}")
    print(f"   Architekturen: {sorted(df['architecture'].unique())}")
    print(f"   Modelle: {sorted(df['model_name'].unique())}")
    print(f"\n   LLM Correctness:")
    print(f"     Mean: {df['llm_correctness_score'].mean():.3f}")
    print(f"     Std:  {df['llm_correctness_score'].std():.3f}")
    print(f"\n   BERT F1:")
    print(f"     Mean: {df['bert_f1'].mean():.3f}")
    print(f"     Std:  {df['bert_f1'].std():.3f}")


def main():
    parser = argparse.ArgumentParser(description='Datenbereinigung für Bachelorarbeit-Analyse')
    parser.add_argument('--input', default='export_full_2026-02-08_final.csv',
                        help='Pfad zur CSV-Eingabedatei')
    parser.add_argument('--output', default='cleaned_data.csv',
                        help='Pfad zur bereinigten CSV-Ausgabedatei')
    args = parser.parse_args()

    df = load_and_validate(args.input)
    df = check_missing_values(df)
    df = validate_score_ranges(df)
    df = standardize_columns(df)

    main_df, comparison_df = separate_judge_comparison_data(df)
    main_df = identify_duplicate_evaluations(main_df)
    comparison_df = identify_duplicate_evaluations(comparison_df)

    generate_summary(main_df)

    main_df.to_csv(args.output, index=False)
    print(f"\nBereinigter Datensatz gespeichert: {args.output}")

    if len(comparison_df) > 0:
        output_dir = os.path.dirname(args.output) or '.'
        comparison_path = os.path.join(output_dir, 'judge_comparison_data.csv')
        comparison_df.to_csv(comparison_path, index=False)
        print(f"Judge-Vergleichsdaten gespeichert: {comparison_path}")


if __name__ == '__main__':
    main()
