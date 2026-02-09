"""Bewertungsmodell-Vergleich: Gemma vs. Llama als LLM-as-Judge (Robustheitsanalyse)."""

import argparse

import pandas as pd
from scipy import stats


def find_paired_evaluations(main_df: pd.DataFrame, comp_df: pd.DataFrame) -> pd.DataFrame:
    """Findet identische Antworten, die von beiden Judges bewertet wurden."""
    print("Suche gepaarte Bewertungen...")

    emb_col = 'embedding_name' if 'embedding_name' in main_df.columns else 'embedding_model'

    fill = '__keine__'
    main_copy = main_df.copy()
    comp_copy = comp_df.copy()
    main_copy[emb_col] = main_copy[emb_col].fillna(fill)
    comp_copy[emb_col] = comp_copy[emb_col].fillna(fill)

    merge_keys = ['question_id', 'graph_type', 'llm_model', emb_col]

    paired = main_copy.merge(comp_copy, on=merge_keys,
                             suffixes=('_gemma', '_llama'), how='inner')
    paired[emb_col] = paired[emb_col].replace(fill, pd.NA)

    print(f"   → {len(paired)} gepaarte Bewertungen gefunden")
    return paired


def analyse_judge_differences(paired: pd.DataFrame):
    """Tabelle 6.17: Vergleich der Bewertungsmodelle."""
    print("\n" + "=" * 70)
    print("ANALYSE: Bewertungsmodell-Vergleich (Tabelle 6.17)")
    print("=" * 70)

    gemma_scores = paired['llm_correctness_score_gemma']
    llama_scores = paired['llm_correctness_score_llama']
    diff = llama_scores - gemma_scores

    print(f"\n  Gemma-Judge Ø: {gemma_scores.mean():.3f}")
    print(f"  Llama-Judge Ø: {llama_scores.mean():.3f}")
    print(f"  Systematische Differenz: {diff.mean():+.3f}")

    r, p = stats.pearsonr(gemma_scores, llama_scores)
    print(f"\n  Korrelation: r = {r:.3f} (p = {'<0.001' if p < 0.001 else f'{p:.3f}'})")

    exact_match = (gemma_scores == llama_scores).mean() * 100
    within_025 = (diff.abs() <= 0.25).mean() * 100
    print(f"  Exakte Übereinstimmung: {exact_match:.1f}%")
    print(f"  Übereinstimmung ±0.25: {within_025:.1f}%")

    if 'architecture_gemma' in paired.columns:
        arch_col = 'architecture_gemma'
    elif 'graph_type' in paired.columns:
        arch_col = 'graph_type'
    else:
        return

    print(f"\n  Nach Architektur:")
    for arch in paired[arch_col].unique():
        mask = paired[arch_col] == arch
        g = gemma_scores[mask].mean()
        l = llama_scores[mask].mean()
        n = mask.sum()
        print(f"    {arch}: Gemma={g:.3f}, Llama={l:.3f}, Δ={l-g:+.3f} (N={n})")


def analyse_score_distribution(paired: pd.DataFrame):
    """Tabelle 6.18: Verteilung der Score-Differenzen."""
    print("\n" + "=" * 70)
    print("ANALYSE: Score-Differenzen-Verteilung (Tabelle 6.18)")
    print("=" * 70)

    diff = paired['llm_correctness_score_llama'] - paired['llm_correctness_score_gemma']

    bins = [-1, -0.375, -0.125, 0.125, 0.375, 0.625, 0.875, 1.1]
    labels = ['-0.50', '-0.25', '0.00', '+0.25', '+0.50', '+0.75', '+1.00']
    diff_binned = pd.cut(diff, bins=bins, labels=labels)

    dist = diff_binned.value_counts().sort_index()
    print("\n  Differenz (Llama−Gemma)  |  Anzahl  |  Anteil")
    print("  " + "-" * 50)
    for label, count in dist.items():
        pct = count / len(diff) * 100
        print(f"  {label:>25s}  |  {count:5d}   |  {pct:.1f}%")


def analyse_self_enhancement_bias(paired: pd.DataFrame):
    """Tabelle 6.19: Pruefung auf Self-Enhancement Bias."""
    print("\n" + "=" * 70)
    print("ANALYSE: Self-Enhancement Bias (Tabelle 6.19)")
    print("=" * 70)

    if 'llm_model' not in paired.columns:
        print("  Generator-Modell nicht verfügbar")
        return

    print("\n  Generator-Modell  |  Gemma-Judge  |  Llama-Judge  |  N")
    print("  " + "-" * 55)

    for generator in paired['llm_model'].unique():
        mask = paired['llm_model'] == generator
        g = paired.loc[mask, 'llm_correctness_score_gemma'].mean()
        l = paired.loc[mask, 'llm_correctness_score_llama'].mean()
        n = mask.sum()
        print(f"  {generator:18s}  |  {g:.3f}        |  {l:.3f}        |  {n}")

    print("\n  Self-Enhancement Bias:")

    if 'gemma3:12b' in paired['llm_model'].values and 'llama3.1:8b' in paired['llm_model'].values:
        gemma_on_gemma = paired.loc[paired['llm_model'] == 'gemma3:12b', 'llm_correctness_score_gemma'].mean()
        gemma_on_llama = paired.loc[paired['llm_model'] == 'llama3.1:8b', 'llm_correctness_score_gemma'].mean()
        print(f"    Gemma als Judge: Eigene={gemma_on_gemma:.3f}, Llama={gemma_on_llama:.3f}, Δ={gemma_on_gemma-gemma_on_llama:+.3f}")

        llama_on_llama = paired.loc[paired['llm_model'] == 'llama3.1:8b', 'llm_correctness_score_llama'].mean()
        llama_on_gemma = paired.loc[paired['llm_model'] == 'gemma3:12b', 'llm_correctness_score_llama'].mean()
        print(f"    Llama als Judge: Eigene={llama_on_llama:.3f}, Gemma={llama_on_gemma:.3f}, Δ={llama_on_llama-llama_on_gemma:+.3f}")


def check_ranking_robustness(paired: pd.DataFrame):
    """Prueft Stabilitaet der Kernaussagen ueber beide Judges."""
    print("\n" + "=" * 70)
    print("ROBUSTHEITSPRÜFUNG: Rangordnung über beide Judges")
    print("=" * 70)

    if 'graph_type' not in paired.columns:
        return

    for judge, score_col in [('Gemma', 'llm_correctness_score_gemma'),
                              ('Llama', 'llm_correctness_score_llama')]:
        print(f"\n  {judge}-Judge Rangordnung:")
        ranking = paired.groupby('graph_type')[score_col].mean().sort_values(ascending=False)
        for arch, score in ranking.items():
            print(f"    {arch}: {score:.3f}")

    print("\n  Kernaussagen-Check:")
    for arch_col in ['graph_type']:
        for g_col, l_col in [('llm_correctness_score_gemma', 'llm_correctness_score_llama')]:
            means_g = paired.groupby(arch_col)[g_col].mean()
            means_l = paired.groupby(arch_col)[l_col].mean()

            checks = [
                ('Simple RAG < Pure LLM',
                 means_g.get('simple_rag', 0) < means_g.get('pure_llm', 1),
                 means_l.get('simple_rag', 0) < means_l.get('pure_llm', 1)),
                ('Simple RAG < Adaptive RAG',
                 means_g.get('simple_rag', 0) < means_g.get('adaptive_rag', 1),
                 means_l.get('simple_rag', 0) < means_l.get('adaptive_rag', 1)),
            ]

            for label, gemma_holds, llama_holds in checks:
                status = "Bestaetigt" if (gemma_holds and llama_holds) else "Widerspruch"
                print(f"    {label}: {status} (Gemma: {gemma_holds}, Llama: {llama_holds})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main', default='cleaned_data.csv')
    parser.add_argument('--comparison', default='ergebnisse/judge_comparison_data.csv')
    args = parser.parse_args()

    main_df = pd.read_csv(args.main)
    try:
        comp_df = pd.read_csv(args.comparison)
    except FileNotFoundError:
        print("Keine separaten Judge-Vergleichsdaten gefunden.")
        print("   Versuche Daten aus Hauptdatensatz zu extrahieren...")
        full_df = pd.read_csv(args.main.replace('cleaned_', 'export_full_'))
        comp_df = full_df[full_df['llm_correctness_model'] == 'llama3.1:8b']
        if len(comp_df) == 0:
            print("   Keine Llama-Judge-Daten verfügbar. Abbruch.")
            return

    paired = find_paired_evaluations(main_df, comp_df)
    if len(paired) == 0:
        print("Keine gepaarten Daten gefunden.")
        return

    analyse_judge_differences(paired)
    analyse_score_distribution(paired)
    analyse_self_enhancement_bias(paired)
    check_ranking_robustness(paired)

    print("\nJudge-Vergleichsanalyse abgeschlossen!")


if __name__ == '__main__':
    main()
