"""Statistische Analyse: Wilcoxon-Tests, Effektstaerken und Subgruppenvergleiche."""

import pandas as pd
import numpy as np
from scipy import stats
import argparse
import warnings
warnings.filterwarnings('ignore')


def cohens_d_paired(x: np.ndarray, y: np.ndarray) -> float:
    """Cohen's d fuer gepaarte Stichproben (d = mean(x-y) / std(x-y))."""
    diff = x - y
    return np.mean(diff) / np.std(diff, ddof=1)


def interpret_effect_size(d: float) -> str:
    """Interpretiert Cohen's d nach Konventionen."""
    abs_d = abs(d)
    if abs_d < 0.5:
        return "klein"
    elif abs_d < 0.8:
        return "mittel"
    else:
        return "groß"


def wilcoxon_test(x: np.ndarray, y: np.ndarray) -> tuple:
    """Wilcoxon signed-rank Test fuer gepaarte, nicht-normalverteilte Stichproben."""
    diff = x - y
    non_zero_mask = diff != 0
    if non_zero_mask.sum() < 10:
        return np.nan, np.nan
    stat, p = stats.wilcoxon(x[non_zero_mask], y[non_zero_mask])
    return stat, p


def analyse_architektur_performance(df: pd.DataFrame):
    """Tabelle 6.3: Hauptergebnisse nach Architektur."""
    print("\n" + "=" * 70)
    print("ANALYSE 1: Performance nach Architektur (Tabelle 6.3)")
    print("=" * 70)

    results = df.groupby('architecture').agg(
        Correctness=('llm_correctness_score', 'mean'),
        Std=('llm_correctness_score', 'std'),
        BERT_F1=('bert_f1', 'mean'),
        Zeit_s=('processing_time_s', 'mean'),
        N=('llm_correctness_score', 'count')
    ).round(3)

    results = results.sort_values('Correctness', ascending=False)
    print(results.to_string())
    return results


def analyse_architektur_vergleiche(df: pd.DataFrame):
    """Tabelle 6.4: Wilcoxon signed-rank Tests für Architekturvergleiche."""
    print("\n" + "=" * 70)
    print("ANALYSE 2: Statistische Architekturvergleiche (Tabelle 6.4)")
    print("=" * 70)
    print("Methode: Wilcoxon signed-rank Test, N=110 gepaarte Fragen")
    print("Effektstärke: Cohen's d für gepaarte Stichproben\n")

    question_means = df.groupby(['question_id', 'architecture'])['llm_correctness_score'].mean().unstack()

    comparisons = [
        ('Pure LLM', 'Simple RAG'),
        ('Adaptive RAG', 'Simple RAG'),
        ('Pure LLM', 'Adaptive RAG'),
    ]

    results = []
    for arch_a, arch_b in comparisons:
        if arch_a not in question_means.columns or arch_b not in question_means.columns:
            continue

        valid = question_means[[arch_a, arch_b]].dropna()
        x = valid[arch_a].values
        y = valid[arch_b].values

        delta = np.mean(x) - np.mean(y)
        stat, p = wilcoxon_test(x, y)
        d = cohens_d_paired(x, y)
        effect = interpret_effect_size(d)

        results.append({
            'Vergleich': f'{arch_a} vs. {arch_b}',
            'ΔCorrectness': f'+{delta:.3f}' if delta > 0 else f'{delta:.3f}',
            'p-Wert': f'<0.001' if p < 0.001 else f'{p:.3f}',
            'Cohen d': f'{d:.2f}',
            'Effekt': effect,
            'N': len(valid)
        })

        print(f"  {arch_a} vs. {arch_b}:")
        print(f"    ΔCorrectness = {delta:.3f}")
        print(f"    p-Wert = {'<0.001' if p < 0.001 else f'{p:.3f}'}")
        print(f"    Cohen's d = {d:.2f} ({effect})")
        print()

    return pd.DataFrame(results)


def analyse_modell_performance(df: pd.DataFrame):
    """Tabelle 6.5: Ergebnisse nach Sprachmodell."""
    print("\n" + "=" * 70)
    print("ANALYSE 3: Performance nach Sprachmodell (Tabelle 6.5)")
    print("=" * 70)

    results = df.groupby('model_name').agg(
        Correctness=('llm_correctness_score', 'mean'),
        BERT_F1=('bert_f1', 'mean'),
        N=('llm_correctness_score', 'count')
    ).round(3).sort_values('Correctness', ascending=False)

    print(results.to_string())

    print("\n  Paarweise Modellvergleiche:")
    models = results.index.tolist()
    question_means = df.groupby(['question_id', 'model_name'])['llm_correctness_score'].mean().unstack()

    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            m_a, m_b = models[i], models[j]
            valid = question_means[[m_a, m_b]].dropna()
            if len(valid) < 10:
                continue
            x, y = valid[m_a].values, valid[m_b].values
            _, p = wilcoxon_test(x, y)
            print(f"    {m_a} vs. {m_b}: p = {'<0.001' if p < 0.001 else f'{p:.3f}'}")

    return results


def analyse_kreuz_architektur_modell(df: pd.DataFrame):
    """Tabelle 6.6: LLM Correctness nach Architektur und Modell."""
    print("\n" + "=" * 70)
    print("ANALYSE 4: Kreuzanalyse Architektur × Modell (Tabelle 6.6)")
    print("=" * 70)

    pivot = df.pivot_table(
        values='llm_correctness_score',
        index='architecture',
        columns='model_name',
        aggfunc='mean'
    ).round(3)

    arch_order = ['Pure LLM', 'Adaptive RAG', 'Simple RAG']
    pivot = pivot.reindex([a for a in arch_order if a in pivot.index])

    print(pivot.to_string())

    print("\nBERT F1 nach Architektur × Modell:")
    bert_pivot = df.pivot_table(values='bert_f1', index='architecture', columns='model_name', aggfunc='mean').round(3)
    bert_pivot = bert_pivot.reindex([a for a in arch_order if a in bert_pivot.index])
    print(bert_pivot.to_string())

    print("\n  Distracting Effect (Verlust Simple RAG vs. Pure LLM):")
    if 'Pure LLM' in pivot.index and 'Simple RAG' in pivot.index:
        for model in pivot.columns:
            pure = pivot.loc['Pure LLM', model]
            simple = pivot.loc['Simple RAG', model]
            loss = (simple - pure) / pure * 100
            print(f"    {model}: {loss:.1f}%")

    return pivot


def analyse_embedding_vergleich(df: pd.DataFrame):
    """Tabelle 6.7 & 6.8: Ergebnisse nach Embedding-Modell."""
    print("\n" + "=" * 70)
    print("ANALYSE 5: Embedding-Vergleich (Tabelle 6.7 / 6.8)")
    print("=" * 70)

    rag_df = df[df['architecture'].isin(['Adaptive RAG', 'Simple RAG'])].copy()

    emb_results = rag_df.groupby('embedding_name').agg(
        Correctness=('llm_correctness_score', 'mean'),
        BERT_F1=('bert_f1', 'mean'),
        N=('llm_correctness_score', 'count')
    ).round(3)
    print("Aggregiert:")
    print(emb_results.to_string())

    print("\nNach Sprachmodell:")
    pivot = rag_df.pivot_table(
        values='llm_correctness_score',
        index='model_name',
        columns='embedding_name',
        aggfunc='mean'
    ).round(3)
    if 'embeddinggemma' in pivot.columns and 'nomic-embed-text' in pivot.columns:
        pivot['Differenz'] = (pivot['embeddinggemma'] - pivot['nomic-embed-text']).round(3)
    print(pivot.to_string())

    return emb_results


def analyse_adaptive_rag_pfade(df: pd.DataFrame):
    """Tabelle 6.9 & 6.10: Analyse der Adaptive-RAG-Pfade."""
    print("\n" + "=" * 70)
    print("ANALYSE 6: Adaptive-RAG-Pfad-Analyse (Tabelle 6.9 / 6.10)")
    print("=" * 70)

    adaptive_df = df[df['architecture'] == 'Adaptive RAG'].copy()

    if 'graph_trace' not in adaptive_df.columns:
        print("  graph_trace Spalte nicht verfügbar")
        return

    def classify_path(trace):
        if pd.isna(trace):
            return 'unbekannt'
        trace = str(trace).lower()
        if 'transform' in trace and 'no_docs_fallback' in trace:
            return 'transform → no_docs_fallback'
        elif 'transform' in trace and 'fallback' in trace:
            return 'transform → fallback'
        elif 'fallback' in trace and 'transform' not in trace:
            return 'generate → fallback'
        elif 'transform' in trace:
            return 'mit Transform'
        else:
            return 'direkt (retrieve→grade→generate)'

    adaptive_df['pfad_typ'] = adaptive_df['graph_trace'].apply(classify_path)

    pfad_stats = adaptive_df.groupby('pfad_typ').agg(
        Anteil=('llm_correctness_score', lambda x: f'{len(x)/len(adaptive_df)*100:.1f}%'),
        Correctness=('llm_correctness_score', 'mean'),
        BERT_F1=('bert_f1', 'mean'),
        N=('llm_correctness_score', 'count')
    ).round(3).sort_values('N', ascending=False)

    print(pfad_stats.to_string())

    simple_mean = df[df['architecture'] == 'Simple RAG']['llm_correctness_score'].mean()
    print(f"\n  Simple RAG Baseline Correctness: {simple_mean:.3f}")
    print("  Alle Adaptive-RAG-Pfade vs. Simple RAG:")
    for pfad in pfad_stats.index:
        corr = pfad_stats.loc[pfad, 'Correctness']
        improvement = (corr - simple_mean) / simple_mean * 100
        print(f"    {pfad}: {corr:.3f} ({improvement:+.1f}% vs. Simple RAG)")


def analyse_wissensbasis_abdeckung(df: pd.DataFrame):
    """Tabelle 6.11: Performance nach Wissensbasis-Abdeckung."""
    print("\n" + "=" * 70)
    print("ANALYSE 7: Wissensbasis-Abdeckung (Tabelle 6.11)")
    print("=" * 70)

    def in_knowledge_base(tags):
        if pd.isna(tags):
            return False
        tags_lower = str(tags).lower()
        return 'postgresql' in tags_lower or 'mysql' in tags_lower

    df = df.copy()
    df['in_wissensbasis'] = df['tags'].apply(in_knowledge_base)

    print(f"\n  Fragen in Wissensbasis: {df[df['in_wissensbasis']]['question_id'].nunique()}")
    print(f"  Fragen nicht in Wissensbasis: {df[~df['in_wissensbasis']]['question_id'].nunique()}")

    for in_kb, label in [(True, 'In Wissensbasis'), (False, 'Nicht in Wissensbasis')]:
        subset = df[df['in_wissensbasis'] == in_kb]
        print(f"\n  {label}:")
        for arch in ['Pure LLM', 'Adaptive RAG', 'Simple RAG']:
            arch_data = subset[subset['architecture'] == arch]
            corr_mean = arch_data['llm_correctness_score'].mean()
            bert_mean = arch_data['bert_f1'].mean()
            if not np.isnan(corr_mean):
                print(f"    {arch}: Correctness={corr_mean:.3f}, BERT_F1={bert_mean:.3f}")

    kb_df = df[df['in_wissensbasis']]
    q_means = kb_df.groupby(['question_id', 'architecture'])['llm_correctness_score'].mean().unstack()
    if 'Adaptive RAG' in q_means.columns and 'Pure LLM' in q_means.columns:
        valid = q_means[['Adaptive RAG', 'Pure LLM']].dropna()
        if len(valid) >= 10:
            x, y = valid['Adaptive RAG'].values, valid['Pure LLM'].values
            _, p = wilcoxon_test(x, y)
            d = cohens_d_paired(x, y)
            print(f"\n  Adaptive RAG vs. Pure LLM (nur Wissensbasis-Fragen):")
            print(f"    p = {p:.3f}, Cohen's d = {d:.2f}")

            print(f"\n  Fragen-Differenzanalyse (nur Wissensbasis, N={len(valid)}):")
            valid['delta'] = valid['Adaptive RAG'] - valid['Pure LLM']

            categories = {
                'Adaptive deutlich besser (Δ > +0.1)': valid['delta'] > 0.1,
                'Adaptive leicht besser (0 < Δ ≤ +0.1)': (valid['delta'] > 0) & (valid['delta'] <= 0.1),
                'Praktisch gleichwertig (|Δ| ≤ 0.05)': valid['delta'].abs() <= 0.05,
                'Adaptive leicht schlechter (-0.1 ≤ Δ < 0)': (valid['delta'] < 0) & (valid['delta'] >= -0.1),
                'Adaptive deutlich schlechter (Δ < -0.1)': valid['delta'] < -0.1,
            }

            for label, mask in categories.items():
                n = mask.sum()
                pct = n / len(valid) * 100
                print(f"    {label}: {n} ({pct:.1f}%)")


def analyse_verarbeitungszeit(df: pd.DataFrame):
    """Tabelle 6.15 & 6.16: Verarbeitungszeit und Overhead."""
    print("\n" + "=" * 70)
    print("ANALYSE 8: Verarbeitungszeit (Tabelle 6.15 / 6.16)")
    print("=" * 70)

    pivot = df.pivot_table(
        values='processing_time_s',
        index='architecture',
        columns='model_name',
        aggfunc=['mean', 'std']
    ).round(1)

    print("Verarbeitungszeit (Sekunden):")
    mean_pivot = df.pivot_table(
        values='processing_time_s',
        index='architecture',
        columns='model_name',
        aggfunc='mean'
    ).round(1)
    std_pivot = df.pivot_table(
        values='processing_time_s',
        index='architecture',
        columns='model_name',
        aggfunc='std'
    ).round(1)

    arch_order = ['Pure LLM', 'Simple RAG', 'Adaptive RAG']
    for arch in arch_order:
        if arch not in mean_pivot.index:
            continue
        row_str = f"  {arch:15s}  "
        for model in mean_pivot.columns:
            m = mean_pivot.loc[arch, model]
            s = std_pivot.loc[arch, model]
            row_str += f"{model}: {m:.0f}±{s:.0f}s  "
        print(row_str)

    print("\nOverhead-Faktoren gegenüber Pure LLM:")
    if 'Pure LLM' in mean_pivot.index:
        pure_times = mean_pivot.loc['Pure LLM']
        for arch in ['Simple RAG', 'Adaptive RAG']:
            if arch not in mean_pivot.index:
                continue
            row_str = f"  {arch:15s}  "
            for model in mean_pivot.columns:
                overhead = mean_pivot.loc[arch, model] / pure_times[model]
                row_str += f"{model}: {overhead:.1f}×  "
            print(row_str)


def analyse_alle_konfigurationen(df: pd.DataFrame):
    """Tabelle A.2: LLM Correctness aller 15 Konfigurationen."""
    print("\n" + "=" * 70)
    print("ANALYSE 9: Alle Konfigurationen (Tabelle A.2)")
    print("=" * 70)

    df = df.copy()
    df['embedding_name'] = df['embedding_name'].fillna('keine')

    configs = df.groupby(['architecture', 'model_name', 'embedding_name']).agg(
        Correctness=('llm_correctness_score', 'mean'),
        BERT_F1=('bert_f1', 'mean'),
        N=('llm_correctness_score', 'count')
    ).round(3).sort_values('Correctness', ascending=False)

    print(configs.to_string())
    return configs


def analyse_fragen_differenz(df: pd.DataFrame):
    """Tabelle A.4: Verteilung der Fragen nach Adaptive-RAG vs. Pure LLM."""
    print("\n" + "=" * 70)
    print("ANALYSE 10: Fragen-Differenzanalyse (Tabelle A.4)")
    print("=" * 70)

    q_means = df.groupby(['question_id', 'architecture'])['llm_correctness_score'].mean().unstack()

    if 'Adaptive RAG' not in q_means.columns or 'Pure LLM' not in q_means.columns:
        print("  Nicht genügend Daten für Vergleich")
        return

    valid = q_means[['Adaptive RAG', 'Pure LLM']].dropna()
    valid['delta'] = valid['Adaptive RAG'] - valid['Pure LLM']

    categories = {
        'Adaptive deutlich besser (Δ > +0.1)': valid['delta'] > 0.1,
        'Adaptive leicht besser (0 < Δ ≤ +0.1)': (valid['delta'] > 0) & (valid['delta'] <= 0.1),
        'Praktisch gleichwertig (|Δ| ≤ 0.05)': valid['delta'].abs() <= 0.05,
        'Adaptive leicht schlechter (-0.1 ≤ Δ < 0)': (valid['delta'] < 0) & (valid['delta'] >= -0.1),
        'Adaptive deutlich schlechter (Δ < -0.1)': valid['delta'] < -0.1,
    }

    for label, mask in categories.items():
        n = mask.sum()
        pct = n / len(valid) * 100
        print(f"  {label}: {n} ({pct:.1f}%)")

    print("\n  Top 5 Adaptive-RAG-Vorteile:")
    top_pos = valid.nlargest(5, 'delta')
    for qid, row in top_pos.iterrows():
        q_title = df[df['question_id'] == qid]['question_title'].iloc[0][:60]
        print(f"    Δ={row['delta']:+.3f} | {q_title}")

    print("\n  Top 5 Adaptive-RAG-Nachteile:")
    top_neg = valid.nsmallest(5, 'delta')
    for qid, row in top_neg.iterrows():
        q_title = df[df['question_id'] == qid]['question_title'].iloc[0][:60]
        print(f"    Δ={row['delta']:+.3f} | {q_title}")


def analyse_bert_score_vergleich(df: pd.DataFrame):
    """ANALYSE 11: BERTScore-basierte Architekturvergleiche (Triangulation)."""
    print("\n" + "=" * 70)
    print("ANALYSE 11: BERTScore Architekturvergleiche (Triangulation)")
    print("=" * 70)
    print("Gleiche Tests wie Analyse 2, aber mit BERT F1 statt LLM Correctness\n")

    question_means = df.groupby(['question_id', 'architecture'])['bert_f1'].mean().unstack()

    comparisons = [
        ('Pure LLM', 'Simple RAG'),
        ('Adaptive RAG', 'Simple RAG'),
        ('Pure LLM', 'Adaptive RAG'),
    ]

    for arch_a, arch_b in comparisons:
        if arch_a not in question_means.columns or arch_b not in question_means.columns:
            continue
        valid = question_means[[arch_a, arch_b]].dropna()
        x, y = valid[arch_a].values, valid[arch_b].values

        delta = np.mean(x) - np.mean(y)
        stat, p = wilcoxon_test(x, y)
        d = cohens_d_paired(x, y)
        effect = interpret_effect_size(d)

        print(f"  {arch_a} vs. {arch_b}:")
        print(f"    ΔBERT_F1 = {delta:.3f}")
        print(f"    p-Wert = {'<0.001' if p < 0.001 else f'{p:.3f}'}")
        print(f"    Cohen's d = {d:.2f} ({effect})")
        print()


def main():
    parser = argparse.ArgumentParser(description='Statistische Analyse der Bachelorarbeit')
    parser.add_argument('--input', default='cleaned_data.csv', help='Bereinigter Datensatz')
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    print(f"Datensatz geladen: {len(df)} Zeilen, {df['question_id'].nunique()} Fragen")

    analyse_architektur_performance(df)
    analyse_architektur_vergleiche(df)
    analyse_modell_performance(df)
    analyse_kreuz_architektur_modell(df)
    analyse_embedding_vergleich(df)
    analyse_adaptive_rag_pfade(df)
    analyse_wissensbasis_abdeckung(df)
    analyse_verarbeitungszeit(df)
    analyse_alle_konfigurationen(df)
    analyse_fragen_differenz(df)
    analyse_bert_score_vergleich(df)

    print("\nAlle Analysen abgeschlossen!")


if __name__ == '__main__':
    main()
