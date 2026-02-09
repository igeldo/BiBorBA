"""Visualisierungen der Analyseergebnisse (7 Diagramme)."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import argparse
import os


COLORS = {
    'Pure LLM': '#2196F3',
    'Adaptive RAG': '#4CAF50',
    'Simple RAG': '#FF9800',
}

ARCH_ORDER = ['Pure LLM', 'Adaptive RAG', 'Simple RAG']


def setup_style():
    """Einheitlicher Plot-Stil."""
    plt.rcParams.update({
        'figure.figsize': (10, 6),
        'font.size': 11,
        'axes.titlesize': 14,
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.dpi': 150,
    })
    sns.set_style("whitegrid")


def plot_boxplot_architektur(df: pd.DataFrame, output_dir: str):
    """Boxplot der LLM Correctness nach Architektur."""
    fig, ax = plt.subplots(figsize=(10, 6))

    palette = [COLORS[a] for a in ARCH_ORDER if a in df['architecture'].unique()]
    order = [a for a in ARCH_ORDER if a in df['architecture'].unique()]

    sns.boxplot(data=df, x='architecture', y='llm_correctness_score',
                order=order, palette=palette, ax=ax, width=0.6)

    means = df.groupby('architecture')['llm_correctness_score'].mean()
    for i, arch in enumerate(order):
        ax.scatter(i, means[arch], marker='D', color='red', s=60, zorder=5,
                   label='Mittelwert' if i == 0 else '')

    ax.set_xlabel('Systemarchitektur')
    ax.set_ylabel('LLM Correctness')
    ax.set_title('LLM Correctness nach Systemarchitektur')
    ax.legend()

    plt.tight_layout()
    path = os.path.join(output_dir, '01_boxplot_architektur.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def plot_heatmap_architektur_modell(df: pd.DataFrame, output_dir: str):
    """Heatmap der Kreuzanalyse Architektur x Modell."""
    pivot = df.pivot_table(
        values='llm_correctness_score',
        index='architecture',
        columns='model_name',
        aggfunc='mean'
    ).round(3)

    arch_order = [a for a in ARCH_ORDER if a in pivot.index]
    pivot = pivot.reindex(arch_order)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlGn',
                vmin=0.3, vmax=0.8, ax=ax, linewidths=1,
                cbar_kws={'label': 'LLM Correctness'})

    ax.set_title('LLM Correctness: Architektur × Sprachmodell')
    ax.set_xlabel('Sprachmodell')
    ax.set_ylabel('Architektur')

    plt.tight_layout()
    path = os.path.join(output_dir, '02_heatmap_architektur_modell.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def plot_embedding_vergleich(df: pd.DataFrame, output_dir: str):
    """Balkendiagramm Embedding-Vergleich nach Sprachmodell."""
    rag_df = df[df['architecture'].isin(['Adaptive RAG', 'Simple RAG'])].copy()
    rag_df = rag_df[rag_df['embedding_name'].notna()]

    pivot = rag_df.pivot_table(
        values='llm_correctness_score',
        index='model_name',
        columns='embedding_name',
        aggfunc='mean'
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(pivot.index))
    width = 0.35

    if 'embeddinggemma' in pivot.columns:
        bars1 = ax.bar(x - width/2, pivot['embeddinggemma'], width,
                        label='embeddinggemma', color='#42A5F5')
    if 'nomic-embed-text' in pivot.columns:
        bars2 = ax.bar(x + width/2, pivot['nomic-embed-text'], width,
                        label='nomic-embed-text', color='#66BB6A')

    ax.set_xlabel('Sprachmodell')
    ax.set_ylabel('LLM Correctness')
    ax.set_title('Embedding-Vergleich nach Sprachmodell (nur RAG)')
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.legend()
    ax.set_ylim(0, 0.7)

    plt.tight_layout()
    path = os.path.join(output_dir, '03_embedding_vergleich.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def plot_verarbeitungszeit(df: pd.DataFrame, output_dir: str):
    """Boxplot Verarbeitungszeit nach Architektur und Modell."""
    fig, ax = plt.subplots(figsize=(12, 6))

    order = [a for a in ARCH_ORDER if a in df['architecture'].unique()]
    palette = [COLORS[a] for a in order]

    sns.boxplot(data=df, x='model_name', y='processing_time_s',
                hue='architecture', hue_order=order,
                palette=palette, ax=ax, showfliers=False)

    ax.set_xlabel('Sprachmodell')
    ax.set_ylabel('Verarbeitungszeit (Sekunden)')
    ax.set_title('Verarbeitungszeit nach Architektur und Sprachmodell')
    ax.legend(title='Architektur')

    plt.tight_layout()
    path = os.path.join(output_dir, '04_verarbeitungszeit.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def plot_score_verteilung(df: pd.DataFrame, output_dir: str):
    """Grouped Bar Chart (LLM Correctness) und KDE Plot (BERT F1)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    order = [a for a in ARCH_ORDER if a in df['architecture'].unique()]
    linestyles = ['-', '--', ':']

    stufen = [0, 0.25, 0.5, 0.75, 1.0]
    stufen_labels = ['0', '0.25', '0.5', '0.75', '1.0']
    x = np.arange(len(stufen))
    width = 0.25

    for i, arch in enumerate(order):
        subset = df[df['architecture'] == arch]
        total = len(subset)
        counts = []
        for s in stufen:
            n = ((subset['llm_correctness_score'] - s).abs() < 0.001).sum()
            counts.append(n / total * 100 if total > 0 else 0)
        bars = axes[0].bar(x + i * width - width, counts, width,
                           label=arch, color=COLORS[arch],
                           edgecolor='white', linewidth=0.5)

    axes[0].set_xlabel('LLM Correctness')
    axes[0].set_ylabel('Anteil (%)')
    axes[0].set_title('Verteilung LLM Correctness')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(stufen_labels)
    axes[0].legend()

    for i, arch in enumerate(order):
        subset = df[df['architecture'] == arch]
        sns.kdeplot(subset['bert_f1'], ax=axes[1], label=arch,
                    color=COLORS[arch], linestyle=linestyles[i], linewidth=2)
    axes[1].set_xlabel('BERT F1')
    axes[1].set_ylabel('Dichte')
    axes[1].set_title('Verteilung BERTScore F1')
    axes[1].legend()

    plt.tight_layout()
    path = os.path.join(output_dir, '05_score_verteilung.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def plot_bert_vs_correctness(df: pd.DataFrame, output_dir: str):
    """Jitter-Plot BERTScore vs. LLM Correctness."""
    from scipy.stats import pearsonr

    fig, ax = plt.subplots(figsize=(10, 8))

    order = [a for a in ARCH_ORDER if a in df['architecture'].unique()]

    rng = np.random.default_rng(42)
    for arch in order:
        subset = df[df['architecture'] == arch]
        jitter = rng.uniform(-0.03, 0.03, size=len(subset))
        ax.scatter(subset['bert_f1'].values,
                   subset['llm_correctness_score'].values + jitter,
                   alpha=0.4, s=15, color=COLORS[arch], label=arch)

    ax.set_xlabel('BERTScore F1')
    ax.set_ylabel('LLM Correctness')
    ax.set_title('BERTScore F1 vs. LLM Correctness')
    ax.legend()

    r, p = pearsonr(df['bert_f1'], df['llm_correctness_score'])
    ax.text(0.05, 0.95, f'r = {r:.3f}', transform=ax.transAxes,
            fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    path = os.path.join(output_dir, '06_bert_vs_correctness.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def plot_alle_konfigurationen(df: pd.DataFrame, output_dir: str):
    """Horizontales Balkendiagramm aller Konfigurationen."""
    df = df.copy()
    df['embedding_name'] = df['embedding_name'].fillna('keine')

    configs = df.groupby(['architecture', 'model_name', 'embedding_name']).agg(
        Correctness=('llm_correctness_score', 'mean')
    ).reset_index().sort_values('Correctness', ascending=True)

    configs['label'] = configs.apply(
        lambda r: f"{r['architecture']} | {r['model_name']} | {r['embedding_name']}"
        if pd.notna(r['embedding_name'])
        else f"{r['architecture']} | {r['model_name']} | —",
        axis=1
    )

    fig, ax = plt.subplots(figsize=(12, 8))

    colors = [COLORS.get(a, '#999999') for a in configs['architecture']]
    ax.barh(range(len(configs)), configs['Correctness'], color=colors, height=0.7)

    ax.set_yticks(range(len(configs)))
    ax.set_yticklabels(configs['label'], fontsize=9)
    ax.set_xlabel('LLM Correctness')
    ax.set_title('LLM Correctness aller Konfigurationen')

    for i, v in enumerate(configs['Correctness']):
        ax.text(v + 0.005, i, f'{v:.3f}', va='center', fontsize=8)

    plt.tight_layout()
    path = os.path.join(output_dir, '07_alle_konfigurationen.png')
    plt.savefig(path)
    plt.close()
    print(f"  Gespeichert: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='cleaned_data.csv')
    parser.add_argument('--output', default='./plots/')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    setup_style()

    df = pd.read_csv(args.input)
    print(f"Erstelle Visualisierungen ({len(df)} Datenpunkte)...\n")

    plot_boxplot_architektur(df, args.output)
    plot_heatmap_architektur_modell(df, args.output)
    plot_embedding_vergleich(df, args.output)
    plot_verarbeitungszeit(df, args.output)
    plot_score_verteilung(df, args.output)
    plot_bert_vs_correctness(df, args.output)
    plot_alle_konfigurationen(df, args.output)

    print(f"\nAlle {7} Diagramme erstellt in {args.output}")


if __name__ == '__main__':
    main()
