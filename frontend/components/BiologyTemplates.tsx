import React from 'react';
import { Dna, FlaskConical, Activity, Microscope, TestTube, Brain } from 'lucide-react';

interface Template {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  code: string;
  category: string;
}

const templates: Template[] = [
  {
    id: 'dna-analysis',
    title: 'DNA Sequence Analysis',
    description: 'Analyze GC content, find ORFs, and calculate molecular properties',
    icon: <Dna className="w-5 h-5" />,
    category: 'Genomics',
    code: `# DNA Sequence Analysis
from Bio import SeqIO, SeqUtils
from Bio.Seq import Seq
import matplotlib.pyplot as plt

# Example DNA sequence (replace with your sequence)
dna_sequence = "ATGGCATTGGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGATCGTCCTCACTGCAACCTCCGCCTCCC"

# Create sequence object
seq = Seq(dna_sequence)

# Basic properties
print(f"Sequence length: {len(seq)} bp")
print(f"GC content: {SeqUtils.gc_fraction(seq)*100:.2f}%")
print(f"Molecular weight: {SeqUtils.molecular_weight(seq, 'DNA'):.2f} Da")
print(f"Melting temperature: {SeqUtils.MeltingTemp.Tm_NN(seq):.2f}°C")

# Find all ORFs (Open Reading Frames)
print("\\nOpen Reading Frames:")
for strand, nuc in [(+1, seq), (-1, seq.reverse_complement())]:
    for frame in range(3):
        for start in range(frame, len(nuc) - 2, 3):
            if nuc[start:start+3] == 'ATG':
                for end in range(start + 3, len(nuc) - 2, 3):
                    if nuc[end:end+3] in ['TAA', 'TAG', 'TGA']:
                        if end - start > 90:  # Minimum ORF length
                            print(f"  Strand {strand:+d}, Frame {frame}: {start}-{end} ({end-start} bp)")
                        break

# Visualize nucleotide composition
nucleotides = ['A', 'T', 'G', 'C']
counts = [seq.count(n) for n in nucleotides]

plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.bar(nucleotides, counts, color=['green', 'red', 'blue', 'yellow'])
plt.title('Nucleotide Composition')
plt.xlabel('Nucleotide')
plt.ylabel('Count')

# GC content sliding window
window_size = 10
gc_content = []
positions = []

for i in range(len(seq) - window_size):
    window = seq[i:i+window_size]
    gc = SeqUtils.gc_fraction(window) * 100
    gc_content.append(gc)
    positions.append(i + window_size/2)

plt.subplot(1, 2, 2)
plt.plot(positions, gc_content)
plt.title(f'GC Content (window size: {window_size})')
plt.xlabel('Position')
plt.ylabel('GC %')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()`
  },
  {
    id: 'protein-analysis',
    title: 'Protein Sequence Analysis',
    description: 'Calculate protein properties, predict structure, and analyze composition',
    icon: <FlaskConical className="w-5 h-5" />,
    category: 'Proteomics',
    code: `# Protein Sequence Analysis
from Bio.SeqUtils.ProtParam import ProteinAnalysis
import matplotlib.pyplot as plt
import numpy as np

# Example protein sequence (replace with your sequence)
protein_seq = "MAEGEITTFTALTEKFNLPPGNYKKPKLLYCSNGGHFLRILPDGTVDGTRDRSDQHIQLQLSAESVGEVYIKSTETGQYLAMDTSGLLYGSQTPSEECLFLERLEENHYNTYISKKHAEKNWFVGLKKNGSCKRGPRTHYGQKAILFLPLPV"

# Create analysis object
analyzed_seq = ProteinAnalysis(protein_seq)

# Basic properties
print("=== Protein Properties ===")
print(f"Length: {len(protein_seq)} amino acids")
print(f"Molecular weight: {analyzed_seq.molecular_weight():.2f} Da")
print(f"Isoelectric point (pI): {analyzed_seq.isoelectric_point():.2f}")
print(f"Instability index: {analyzed_seq.instability_index():.2f}")
print(f"Stability: {'Stable' if analyzed_seq.instability_index() < 40 else 'Unstable'}")
print(f"GRAVY (hydropathy): {analyzed_seq.gravy():.3f}")
print(f"Aromaticity: {analyzed_seq.aromaticity():.3f}")

# Secondary structure prediction
helix, turn, sheet = analyzed_seq.secondary_structure_fraction()
print(f"\\n=== Predicted Secondary Structure ===")
print(f"Alpha helix: {helix*100:.1f}%")
print(f"Beta sheet: {sheet*100:.1f}%")
print(f"Turn: {turn*100:.1f}%")

# Amino acid composition
aa_comp = analyzed_seq.get_amino_acids_percent()

# Visualization
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 1. Amino acid composition
ax1 = axes[0, 0]
aa_sorted = sorted(aa_comp.items(), key=lambda x: x[1], reverse=True)
aa_names = [aa[0] for aa in aa_sorted[:10]]
aa_values = [aa[1]*100 for aa in aa_sorted[:10]]
ax1.bar(aa_names, aa_values, color='steelblue')
ax1.set_title('Top 10 Amino Acids')
ax1.set_xlabel('Amino Acid')
ax1.set_ylabel('Percentage')

# 2. Secondary structure pie chart
ax2 = axes[0, 1]
structures = ['Alpha Helix', 'Beta Sheet', 'Turn/Coil']
sizes = [helix*100, sheet*100, turn*100]
colors = ['#ff9999', '#66b3ff', '#99ff99']
ax2.pie(sizes, labels=structures, colors=colors, autopct='%1.1f%%')
ax2.set_title('Secondary Structure Prediction')

# 3. Hydrophobicity plot (Kyte-Doolittle)
ax3 = axes[1, 0]
window = 9
hydro_scale = {'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5,
               'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
               'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6,
               'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2}

hydropathy = []
for i in range(len(protein_seq) - window + 1):
    window_seq = protein_seq[i:i+window]
    score = sum(hydro_scale.get(aa, 0) for aa in window_seq) / window
    hydropathy.append(score)

ax3.plot(range(len(hydropathy)), hydropathy)
ax3.axhline(y=0, color='r', linestyle='--', alpha=0.5)
ax3.set_title('Hydrophobicity Plot (Kyte-Doolittle)')
ax3.set_xlabel('Position')
ax3.set_ylabel('Hydrophobicity Score')
ax3.grid(True, alpha=0.3)

# 4. Charge distribution
ax4 = axes[1, 1]
positive = ['R', 'H', 'K']
negative = ['D', 'E']
charge_dist = []
for i, aa in enumerate(protein_seq):
    if aa in positive:
        charge_dist.append((i, 1, 'Positive'))
    elif aa in negative:
        charge_dist.append((i, -1, 'Negative'))

if charge_dist:
    pos_x = [c[0] for c in charge_dist if c[2] == 'Positive']
    pos_y = [c[1] for c in charge_dist if c[2] == 'Positive']
    neg_x = [c[0] for c in charge_dist if c[2] == 'Negative']
    neg_y = [c[1] for c in charge_dist if c[2] == 'Negative']
    
    ax4.scatter(pos_x, pos_y, color='blue', label='Positive', alpha=0.6)
    ax4.scatter(neg_x, neg_y, color='red', label='Negative', alpha=0.6)
    ax4.set_title('Charge Distribution')
    ax4.set_xlabel('Position')
    ax4.set_ylabel('Charge')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()`
  },
  {
    id: 'sequence-alignment',
    title: 'Sequence Alignment',
    description: 'Perform pairwise or multiple sequence alignment',
    icon: <Activity className="w-5 h-5" />,
    category: 'Comparative Genomics',
    code: `# Sequence Alignment
from Bio import pairwise2, Align
from Bio.pairwise2 import format_alignment
from Bio.Align import substitution_matrices
import matplotlib.pyplot as plt

# Example sequences (replace with your sequences)
seq1 = "ATGGCATTGGCAGCAGCAGCAGCAGCAGCAG"
seq2 = "ATGGCATTGGCAACAGCAGCAGCTGCAGCAG"

print("=== Pairwise DNA Alignment ===")
print(f"Sequence 1 ({len(seq1)} bp): {seq1[:30]}...")
print(f"Sequence 2 ({len(seq2)} bp): {seq2[:30]}...")

# Perform global alignment
alignments = pairwise2.align.globalxx(seq1, seq2)

# Show best alignment
if alignments:
    best = alignments[0]
    aligned_seq1, aligned_seq2, score, begin, end = best
    
    print(f"\\nAlignment Score: {score}")
    print(format_alignment(*best))
    
    # Calculate identity
    matches = sum(1 for a, b in zip(aligned_seq1, aligned_seq2) if a == b and a != '-')
    identity = (matches / len(aligned_seq1.replace('-', ''))) * 100
    print(f"\\nSequence Identity: {identity:.1f}%")
    print(f"Matches: {matches}/{len(aligned_seq1)}")
    
    # Visualize alignment
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
    
    # Plot 1: Identity map
    match_positions = []
    mismatch_positions = []
    gap_positions = []
    
    for i, (a, b) in enumerate(zip(aligned_seq1, aligned_seq2)):
        if a == '-' or b == '-':
            gap_positions.append(i)
        elif a == b:
            match_positions.append(i)
        else:
            mismatch_positions.append(i)
    
    ax1.scatter(match_positions, [1]*len(match_positions), color='green', s=20, label='Match')
    ax1.scatter(mismatch_positions, [1]*len(mismatch_positions), color='red', s=20, label='Mismatch')
    ax1.scatter(gap_positions, [1]*len(gap_positions), color='yellow', s=20, label='Gap')
    ax1.set_ylim(0.5, 1.5)
    ax1.set_xlabel('Position')
    ax1.set_title('Alignment Identity Map')
    ax1.legend()
    ax1.set_yticks([])
    
    # Plot 2: Sliding window identity
    window_size = 10
    identities = []
    positions = []
    
    for i in range(len(aligned_seq1) - window_size):
        window1 = aligned_seq1[i:i+window_size]
        window2 = aligned_seq2[i:i+window_size]
        matches = sum(1 for a, b in zip(window1, window2) if a == b and a != '-')
        identities.append(matches / window_size * 100)
        positions.append(i + window_size/2)
    
    ax2.plot(positions, identities, color='blue')
    ax2.fill_between(positions, identities, alpha=0.3)
    ax2.set_xlabel('Position')
    ax2.set_ylabel('Identity (%)')
    ax2.set_title(f'Sliding Window Identity (window size: {window_size})')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 105)
    
    plt.tight_layout()
    plt.show()

# For protein alignment example
print("\\n=== Protein Alignment Example ===")
protein1 = "MAEGEITTFTALTEKFNLPPGNYKKPKLLYCSNG"
protein2 = "MAEGEITTFTALTEKFNLPPGNYRKPKLLYCSNG"

# Use BLOSUM62 matrix for protein alignment
matrix = substitution_matrices.load("BLOSUM62")
protein_alignments = pairwise2.align.globalds(protein1, protein2, matrix, -10, -0.5)

if protein_alignments:
    best_protein = protein_alignments[0]
    print(format_alignment(*best_protein))`
  },
  {
    id: 'molecular-dynamics',
    title: 'Molecular Structure Analysis',
    description: 'Analyze small molecules and drug-like properties',
    icon: <TestTube className="w-5 h-5" />,
    category: 'Cheminformatics',
    code: `# Molecular Structure Analysis
from rdkit import Chem
from rdkit.Chem import Descriptors, Draw, Lipinski, Crippen
import pandas as pd
import matplotlib.pyplot as plt

# Example molecules (SMILES format)
molecules = {
    'Aspirin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
    'Caffeine': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
    'Glucose': 'C([C@@H]1[C@H]([C@@H]([C@H](C(O1)O)O)O)O)O',
    'Penicillin': 'CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)CC3=CC=CC=C3)C(=O)O)C'
}

results = []

for name, smiles in molecules.items():
    mol = Chem.MolFromSmiles(smiles)
    
    if mol:
        # Calculate molecular properties
        props = {
            'Molecule': name,
            'SMILES': smiles,
            'MW': round(Descriptors.MolWt(mol), 2),
            'LogP': round(Descriptors.MolLogP(mol), 2),
            'HBD': Descriptors.NumHDonors(mol),
            'HBA': Descriptors.NumHAcceptors(mol),
            'TPSA': round(Descriptors.TPSA(mol), 2),
            'Rotatable Bonds': Descriptors.NumRotatableBonds(mol),
            'Aromatic Rings': Descriptors.NumAromaticRings(mol),
            'QED': round(Descriptors.qed(mol), 3)  # Drug-likeness score
        }
        
        # Check Lipinski's Rule of Five
        lipinski_violations = sum([
            props['MW'] > 500,
            props['LogP'] > 5,
            props['HBD'] > 5,
            props['HBA'] > 10
        ])
        props['Lipinski Violations'] = lipinski_violations
        props['Drug-like'] = 'Yes' if lipinski_violations <= 1 else 'No'
        
        results.append(props)

# Create DataFrame
df = pd.DataFrame(results)
print("=== Molecular Properties ===")
print(df.to_string(index=False))

# Visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 1. Molecular Weight Distribution
ax1 = axes[0, 0]
ax1.bar(df['Molecule'], df['MW'], color='skyblue')
ax1.axhline(y=500, color='r', linestyle='--', label='Lipinski limit (500 Da)')
ax1.set_title('Molecular Weight')
ax1.set_ylabel('MW (Da)')
ax1.legend()
ax1.tick_params(axis='x', rotation=45)

# 2. LogP Distribution
ax2 = axes[0, 1]
ax2.bar(df['Molecule'], df['LogP'], color='lightgreen')
ax2.axhline(y=5, color='r', linestyle='--', label='Lipinski limit (5)')
ax2.set_title('Lipophilicity (LogP)')
ax2.set_ylabel('LogP')
ax2.legend()
ax2.tick_params(axis='x', rotation=45)

# 3. Drug-likeness (QED) scores
ax3 = axes[1, 0]
colors = ['green' if x > 0.5 else 'orange' if x > 0.3 else 'red' for x in df['QED']]
ax3.bar(df['Molecule'], df['QED'], color=colors)
ax3.set_title('Drug-likeness Score (QED)')
ax3.set_ylabel('QED Score (0-1)')
ax3.set_ylim(0, 1)
ax3.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
ax3.tick_params(axis='x', rotation=45)

# 4. Radar plot for drug-like properties
ax4 = axes[1, 1]
categories = ['MW/100', 'LogP', 'HBD', 'HBA', 'TPSA/20']

# Select first molecule for radar plot
mol_data = df.iloc[0]
values = [
    min(mol_data['MW']/100, 5),
    min(mol_data['LogP'], 5),
    mol_data['HBD'],
    mol_data['HBA'],
    min(mol_data['TPSA']/20, 5)
]

# Add first value to close the plot
values += values[:1]
angles = [n / 5 * 2 * 3.14159 for n in range(6)]

ax4 = plt.subplot(2, 2, 4, projection='polar')
ax4.plot(angles, values, 'o-', linewidth=2)
ax4.fill(angles, values, alpha=0.25)
ax4.set_xticks(angles[:-1])
ax4.set_xticklabels(categories)
ax4.set_ylim(0, 5)
ax4.set_title(f'Drug Properties: {mol_data["Molecule"]}')

plt.tight_layout()
plt.show()

print(f"\\n=== Drug-likeness Summary ===")
print(f"Drug-like molecules: {df['Drug-like'].value_counts().get('Yes', 0)}/{len(df)}")
print(f"Average QED score: {df['QED'].mean():.3f}")`
  },
  {
    id: 'phylogenetics',
    title: 'Phylogenetic Analysis',
    description: 'Build phylogenetic trees from sequence data',
    icon: <Microscope className="w-5 h-5" />,
    category: 'Evolution',
    code: `# Phylogenetic Analysis
from Bio import AlignIO, Phylo
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import matplotlib.pyplot as plt

# Example sequences (replace with your aligned sequences)
sequences = [
    SeqRecord(Seq("ATGGCATTGGCAGCAGCAGCAGCAGCAGCAG"), id="Species_A"),
    SeqRecord(Seq("ATGGCATTGGCAACAGCAGCAGCTGCAGCAG"), id="Species_B"),
    SeqRecord(Seq("ATGGCATTGGCAACAGCAGCAGCAGCAGCAG"), id="Species_C"),
    SeqRecord(Seq("ATGGCGTTGGCAGCAGCAGCAGCAGCAGCAG"), id="Species_D"),
    SeqRecord(Seq("ATGGCATTGGCAGCAGCAGCAGCAGCAGCGG"), id="Species_E")
]

# Create alignment
alignment = MultipleSeqAlignment(sequences)

print("=== Multiple Sequence Alignment ===")
for record in alignment:
    print(f"{record.id:12} {record.seq}")

# Calculate distance matrix
calculator = DistanceCalculator('identity')
distance_matrix = calculator.get_distance(alignment)

print("\\n=== Distance Matrix ===")
print(distance_matrix)

# Build tree using UPGMA
constructor = DistanceTreeConstructor()
tree = constructor.upgma(distance_matrix)

# Alternative: Neighbor-Joining
nj_tree = constructor.nj(distance_matrix)

# Visualize trees
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# UPGMA tree
ax1.set_title("UPGMA Tree")
Phylo.draw(tree, axes=ax1, do_show=False)

# Neighbor-Joining tree
ax2.set_title("Neighbor-Joining Tree")
Phylo.draw(nj_tree, axes=ax2, do_show=False)

plt.tight_layout()
plt.show()

# Tree statistics
print("\\n=== Tree Statistics ===")
print(f"Number of terminals: {len(tree.get_terminals())}")
print(f"Total branch length: {tree.total_branch_length():.4f}")

# Find common ancestors
terminals = tree.get_terminals()
if len(terminals) >= 2:
    common_ancestor = tree.common_ancestor(terminals[0], terminals[1])
    print(f"Common ancestor of {terminals[0].name} and {terminals[1].name}: {common_ancestor}")

# Export tree in Newick format
from io import StringIO
output = StringIO()
Phylo.write(tree, output, "newick")
print(f"\\nNewick format: {output.getvalue()}")`
  },
  {
    id: 'gene-expression',
    title: 'Gene Expression Analysis',
    description: 'Analyze differential gene expression and create heatmaps',
    icon: <Brain className="w-5 h-5" />,
    category: 'Transcriptomics',
    code: `# Gene Expression Analysis
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from scipy.cluster import hierarchy
from statsmodels.stats.multitest import multipletests

# Generate example gene expression data (replace with your data)
np.random.seed(42)
n_genes = 100
n_samples = 12

# Create sample groups (6 control, 6 treatment)
groups = ['Control'] * 6 + ['Treatment'] * 6

# Generate expression data with some differentially expressed genes
expression_data = np.random.randn(n_genes, n_samples) * 2 + 10

# Make 20% of genes differentially expressed
de_genes = np.random.choice(n_genes, size=n_genes//5, replace=False)
for gene in de_genes:
    expression_data[gene, 6:] += np.random.uniform(2, 5)  # Upregulate in treatment

# Create DataFrame
gene_names = [f'Gene_{i+1}' for i in range(n_genes)]
sample_names = [f'{g}_{i+1}' for i, g in enumerate(groups)]
df = pd.DataFrame(expression_data, index=gene_names, columns=sample_names)

print("=== Gene Expression Matrix ===")
print(f"Shape: {df.shape[0]} genes x {df.shape[1]} samples")
print(df.iloc[:5, :6])  # Show first 5 genes, 6 samples

# Differential Expression Analysis
print("\\n=== Differential Expression Analysis ===")
de_results = []

for gene in df.index:
    control_expr = df.loc[gene, :6].values
    treatment_expr = df.loc[gene, 6:].values
    
    # T-test
    t_stat, p_value = stats.ttest_ind(control_expr, treatment_expr)
    
    # Calculate fold change
    mean_control = np.mean(control_expr)
    mean_treatment = np.mean(treatment_expr)
    fold_change = mean_treatment / mean_control if mean_control != 0 else np.inf
    log2_fc = np.log2(fold_change) if fold_change > 0 else -np.inf
    
    de_results.append({
        'Gene': gene,
        'Mean_Control': mean_control,
        'Mean_Treatment': mean_treatment,
        'Log2FC': log2_fc,
        'P_value': p_value
    })

de_df = pd.DataFrame(de_results)

# Multiple testing correction
de_df['P_adjusted'] = multipletests(de_df['P_value'], method='fdr_bh')[1]
de_df['Significant'] = (de_df['P_adjusted'] < 0.05) & (np.abs(de_df['Log2FC']) > 1)

print(f"Significant genes: {de_df['Significant'].sum()}/{len(de_df)}")
print("\\nTop 10 differentially expressed genes:")
de_df_sorted = de_df.sort_values('P_adjusted')
print(de_df_sorted[['Gene', 'Log2FC', 'P_value', 'P_adjusted', 'Significant']].head(10))

# Visualizations
fig = plt.figure(figsize=(15, 12))

# 1. Volcano Plot
ax1 = plt.subplot(2, 3, 1)
colors = ['red' if sig else 'gray' for sig in de_df['Significant']]
ax1.scatter(de_df['Log2FC'], -np.log10(de_df['P_value']), c=colors, alpha=0.5)
ax1.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5)
ax1.axvline(x=1, color='black', linestyle='--', alpha=0.5)
ax1.axvline(x=-1, color='black', linestyle='--', alpha=0.5)
ax1.set_xlabel('Log2 Fold Change')
ax1.set_ylabel('-Log10(P-value)')
ax1.set_title('Volcano Plot')

# 2. MA Plot
ax2 = plt.subplot(2, 3, 2)
mean_expr = (de_df['Mean_Control'] + de_df['Mean_Treatment']) / 2
ax2.scatter(mean_expr, de_df['Log2FC'], c=colors, alpha=0.5)
ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
ax2.axhline(y=1, color='black', linestyle='--', alpha=0.5)
ax2.axhline(y=-1, color='black', linestyle='--', alpha=0.5)
ax2.set_xlabel('Mean Expression')
ax2.set_ylabel('Log2 Fold Change')
ax2.set_title('MA Plot')

# 3. Heatmap of top DE genes
ax3 = plt.subplot(2, 3, 3)
top_genes = de_df_sorted.head(20)['Gene'].values
heatmap_data = df.loc[top_genes]

# Z-score normalization
heatmap_zscore = (heatmap_data.T - heatmap_data.mean(axis=1)) / heatmap_data.std(axis=1)
heatmap_zscore = heatmap_zscore.T

sns.heatmap(heatmap_zscore, cmap='RdBu_r', center=0, 
            xticklabels=True, yticklabels=True, ax=ax3, cbar_kws={'label': 'Z-score'})
ax3.set_title('Top 20 DE Genes Heatmap')

# 4. PCA
ax4 = plt.subplot(2, 3, 4)
from sklearn.decomposition import PCA
pca = PCA(n_components=2)
pca_result = pca.fit_transform(df.T)

colors_pca = ['blue' if g == 'Control' else 'red' for g in groups]
ax4.scatter(pca_result[:, 0], pca_result[:, 1], c=colors_pca, s=100)
for i, sample in enumerate(sample_names):
    ax4.annotate(sample.split('_')[0][0], (pca_result[i, 0], pca_result[i, 1]))
ax4.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
ax4.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
ax4.set_title('PCA Plot')

# 5. Expression distribution
ax5 = plt.subplot(2, 3, 5)
df_melt = pd.DataFrame({
    'Expression': df.values.flatten(),
    'Group': np.repeat(groups, n_genes)
})
ax5.violinplot([df.iloc[:, :6].values.flatten(), 
                df.iloc[:, 6:].values.flatten()],
               positions=[1, 2])
ax5.set_xticks([1, 2])
ax5.set_xticklabels(['Control', 'Treatment'])
ax5.set_ylabel('Expression Level')
ax5.set_title('Expression Distribution')

# 6. Hierarchical clustering
ax6 = plt.subplot(2, 3, 6)
linkage = hierarchy.linkage(df.T, method='ward')
hierarchy.dendrogram(linkage, labels=sample_names, ax=ax6)
ax6.set_title('Sample Clustering')
ax6.set_xlabel('Sample')
ax6.set_ylabel('Distance')

plt.tight_layout()
plt.show()`
  }
];

interface BiologyTemplatesProps {
  onSelectTemplate: (code: string) => void;
}

export default function BiologyTemplates({ onSelectTemplate }: BiologyTemplatesProps) {
  const [selectedCategory, setSelectedCategory] = React.useState<string>('all');
  
  const categories = ['all', ...Array.from(new Set(templates.map(t => t.category)))];
  
  const filteredTemplates = selectedCategory === 'all' 
    ? templates 
    : templates.filter(t => t.category === selectedCategory);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-green-400" />
          Biology Analysis Templates
        </h3>
        
        {/* Category Filter */}
        <div className="flex gap-2 flex-wrap mb-4">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                selectedCategory === cat 
                  ? 'bg-green-600 text-white' 
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {cat === 'all' ? 'All' : cat}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filteredTemplates.map(template => (
          <div
            key={template.id}
            className="bg-slate-800 rounded-lg p-4 hover:bg-slate-700 transition-colors cursor-pointer border border-slate-600 hover:border-green-500"
            onClick={() => onSelectTemplate(template.code)}
          >
            <div className="flex items-start gap-3">
              <div className="text-green-400 mt-1">
                {template.icon}
              </div>
              <div className="flex-1">
                <h4 className="text-white font-medium mb-1">{template.title}</h4>
                <p className="text-slate-400 text-sm mb-2">{template.description}</p>
                <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">
                  {template.category}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-slate-800 rounded-lg">
        <p className="text-xs text-slate-400">
          💡 <strong>Tip:</strong> These templates use BioPython, RDKit, and other specialized libraries. 
          Make sure they're installed in your environment. Click any template to load it into the editor.
        </p>
      </div>
    </div>
  );
}