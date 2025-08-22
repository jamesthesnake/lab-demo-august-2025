"""
Biology-specific tools and utilities for AIDO-Lab
Provides helper functions for biological data analysis
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class SequenceAnalysis:
    """Container for sequence analysis results"""
    sequence: str
    length: int
    gc_content: float
    molecular_weight: float
    features: Dict[str, Any]

@dataclass
class ProteinStructure:
    """Container for protein structure data"""
    pdb_id: Optional[str]
    sequence: str
    secondary_structure: Optional[str]
    domains: List[Dict[str, Any]]

class BiologyTools:
    """
    Collection of biology-specific analysis tools
    """
    
    @staticmethod
    def analyze_dna_sequence(sequence: str) -> SequenceAnalysis:
        """
        Analyze a DNA sequence for basic properties
        
        Args:
            sequence: DNA sequence string
            
        Returns:
            SequenceAnalysis object with properties
        """
        from Bio import SeqUtils
        from Bio.Seq import Seq
        
        seq_obj = Seq(sequence.upper())
        
        # Calculate properties
        gc_content = SeqUtils.gc_fraction(seq_obj) * 100
        molecular_weight = SeqUtils.molecular_weight(seq_obj, 'DNA')
        
        # Find ORFs
        orfs = []
        for strand, nuc in [(+1, seq_obj), (-1, seq_obj.reverse_complement())]:
            for frame in range(3):
                for start in range(frame, len(nuc) - 2, 3):
                    if nuc[start:start+3] == 'ATG':
                        for end in range(start + 3, len(nuc) - 2, 3):
                            if nuc[end:end+3] in ['TAA', 'TAG', 'TGA']:
                                if end - start > 90:  # Minimum ORF length
                                    orfs.append({
                                        'start': start,
                                        'end': end,
                                        'strand': strand,
                                        'frame': frame,
                                        'length': end - start
                                    })
                                break
        
        features = {
            'orfs': orfs,
            'at_content': 100 - gc_content,
            'melting_temp': SeqUtils.MeltingTemp.Tm_NN(seq_obj)
        }
        
        return SequenceAnalysis(
            sequence=str(seq_obj),
            length=len(seq_obj),
            gc_content=gc_content,
            molecular_weight=molecular_weight,
            features=features
        )
    
    @staticmethod
    def analyze_protein_sequence(sequence: str) -> Dict[str, Any]:
        """
        Analyze a protein sequence for properties
        
        Args:
            sequence: Protein sequence string
            
        Returns:
            Dictionary with protein properties
        """
        from Bio import SeqUtils
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        
        # Clean sequence
        sequence = sequence.upper().replace(' ', '').replace('\n', '')
        
        # Create analysis object
        analyzed_seq = ProteinAnalysis(sequence)
        
        # Calculate properties
        properties = {
            'length': len(sequence),
            'molecular_weight': analyzed_seq.molecular_weight(),
            'isoelectric_point': analyzed_seq.isoelectric_point(),
            'instability_index': analyzed_seq.instability_index(),
            'gravy': analyzed_seq.gravy(),  # Grand average of hydropathy
            'aromaticity': analyzed_seq.aromaticity(),
            'amino_acid_composition': analyzed_seq.get_amino_acids_percent(),
            'secondary_structure': analyzed_seq.secondary_structure_fraction()
        }
        
        # Determine stability
        properties['is_stable'] = properties['instability_index'] < 40
        
        return properties
    
    @staticmethod
    def align_sequences(seq1: str, seq2: str, seq_type: str = 'dna') -> Dict[str, Any]:
        """
        Perform pairwise sequence alignment
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            seq_type: 'dna' or 'protein'
            
        Returns:
            Alignment results
        """
        from Bio import pairwise2
        from Bio.pairwise2 import format_alignment
        
        # Perform alignment
        if seq_type == 'dna':
            alignments = pairwise2.align.globalxx(seq1, seq2)
        else:
            # Use BLOSUM62 for protein alignment
            from Bio.Align import substitution_matrices
            matrix = substitution_matrices.load("BLOSUM62")
            alignments = pairwise2.align.globalds(seq1, seq2, matrix, -10, -0.5)
        
        if alignments:
            best_alignment = alignments[0]
            
            # Calculate identity
            aligned_seq1, aligned_seq2 = best_alignment[0], best_alignment[1]
            matches = sum(1 for a, b in zip(aligned_seq1, aligned_seq2) if a == b)
            identity = (matches / len(aligned_seq1)) * 100
            
            return {
                'aligned_seq1': aligned_seq1,
                'aligned_seq2': aligned_seq2,
                'score': best_alignment[2],
                'identity': identity,
                'length': len(aligned_seq1),
                'formatted': format_alignment(*best_alignment)
            }
        
        return {'error': 'No alignment found'}
    
    @staticmethod
    def parse_fasta(file_content: str) -> List[Dict[str, str]]:
        """
        Parse FASTA format sequences
        
        Args:
            file_content: FASTA format string
            
        Returns:
            List of sequences with headers
        """
        from Bio import SeqIO
        from io import StringIO
        
        sequences = []
        fasta_io = StringIO(file_content)
        
        for record in SeqIO.parse(fasta_io, "fasta"):
            sequences.append({
                'id': record.id,
                'description': record.description,
                'sequence': str(record.seq),
                'length': len(record.seq)
            })
        
        return sequences
    
    @staticmethod
    def design_primers(sequence: str, target_tm: float = 60.0, 
                      primer_length_range: Tuple[int, int] = (18, 25)) -> Dict[str, Any]:
        """
        Design PCR primers for a DNA sequence
        
        Args:
            sequence: Target DNA sequence
            target_tm: Target melting temperature
            primer_length_range: Min and max primer length
            
        Returns:
            Primer design results
        """
        import primer3
        
        # Configure primer3 settings
        settings = {
            'SEQUENCE_ID': 'target',
            'SEQUENCE_TEMPLATE': sequence,
            'PRIMER_MIN_SIZE': primer_length_range[0],
            'PRIMER_MAX_SIZE': primer_length_range[1],
            'PRIMER_OPT_SIZE': 20,
            'PRIMER_MIN_TM': target_tm - 2,
            'PRIMER_MAX_TM': target_tm + 2,
            'PRIMER_OPT_TM': target_tm,
            'PRIMER_MIN_GC': 40.0,
            'PRIMER_MAX_GC': 60.0,
            'PRIMER_PRODUCT_SIZE_RANGE': [[100, 500]],
            'PRIMER_NUM_RETURN': 5
        }
        
        # Design primers
        results = primer3.bindings.designPrimers(settings)
        
        # Format results
        primers = []
        for i in range(results.get('PRIMER_PAIR_NUM_RETURNED', 0)):
            primers.append({
                'forward_sequence': results[f'PRIMER_LEFT_{i}_SEQUENCE'],
                'reverse_sequence': results[f'PRIMER_RIGHT_{i}_SEQUENCE'],
                'forward_tm': results[f'PRIMER_LEFT_{i}_TM'],
                'reverse_tm': results[f'PRIMER_RIGHT_{i}_TM'],
                'forward_gc': results[f'PRIMER_LEFT_{i}_GC_PERCENT'],
                'reverse_gc': results[f'PRIMER_RIGHT_{i}_GC_PERCENT'],
                'product_size': results[f'PRIMER_PAIR_{i}_PRODUCT_SIZE']
            })
        
        return {
            'primers': primers,
            'sequence_length': len(sequence),
            'settings': settings
        }
    
    @staticmethod
    def analyze_molecular_structure(smiles: str) -> Dict[str, Any]:
        """
        Analyze a molecular structure from SMILES
        
        Args:
            smiles: SMILES string representation
            
        Returns:
            Molecular properties
        """
        from rdkit import Chem
        from rdkit.Chem import Descriptors, Lipinski
        
        # Parse molecule
        mol = Chem.MolFromSmiles(smiles)
        
        if mol is None:
            return {'error': 'Invalid SMILES string'}
        
        # Calculate properties
        properties = {
            'molecular_weight': Descriptors.MolWt(mol),
            'logp': Descriptors.MolLogP(mol),
            'num_h_donors': Descriptors.NumHDonors(mol),
            'num_h_acceptors': Descriptors.NumHAcceptors(mol),
            'num_rotatable_bonds': Descriptors.NumRotatableBonds(mol),
            'num_aromatic_rings': Descriptors.NumAromaticRings(mol),
            'tpsa': Descriptors.TPSA(mol),  # Topological polar surface area
            'num_atoms': mol.GetNumAtoms(),
            'num_bonds': mol.GetNumBonds(),
            'formal_charge': Chem.rdmolops.GetFormalCharge(mol)
        }
        
        # Check Lipinski's Rule of Five
        properties['lipinski_violations'] = sum([
            properties['molecular_weight'] > 500,
            properties['logp'] > 5,
            properties['num_h_donors'] > 5,
            properties['num_h_acceptors'] > 10
        ])
        
        properties['drug_like'] = properties['lipinski_violations'] <= 1
        
        return properties
    
    @staticmethod
    def simulate_population_genetics(
        population_size: int = 1000,
        generations: int = 100,
        mutation_rate: float = 0.001,
        selection_coefficient: float = 0.1
    ) -> pd.DataFrame:
        """
        Simulate simple population genetics (Hardy-Weinberg with selection)
        
        Args:
            population_size: Number of individuals
            generations: Number of generations to simulate
            mutation_rate: Mutation rate per generation
            selection_coefficient: Selection strength (0-1)
            
        Returns:
            DataFrame with allele frequencies over time
        """
        # Initialize allele frequencies
        p = 0.5  # Frequency of allele A
        q = 0.5  # Frequency of allele a
        
        results = []
        
        for gen in range(generations):
            # Apply selection (AA has fitness 1, Aa has fitness 1-s/2, aa has fitness 1-s)
            w_AA = 1.0
            w_Aa = 1.0 - selection_coefficient / 2
            w_aa = 1.0 - selection_coefficient
            
            # Calculate mean fitness
            w_mean = p**2 * w_AA + 2*p*q * w_Aa + q**2 * w_aa
            
            # Update frequencies after selection
            p_new = (p**2 * w_AA + p*q * w_Aa) / w_mean
            q_new = (q**2 * w_aa + p*q * w_Aa) / w_mean
            
            # Apply mutation
            p_new = p_new * (1 - mutation_rate) + q_new * mutation_rate
            q_new = 1 - p_new
            
            # Genetic drift (simplified)
            if population_size < float('inf'):
                # Binomial sampling
                num_A = np.random.binomial(2 * population_size, p_new)
                p_new = num_A / (2 * population_size)
                q_new = 1 - p_new
            
            results.append({
                'generation': gen,
                'freq_A': p_new,
                'freq_a': q_new,
                'mean_fitness': w_mean,
                'heterozygosity': 2 * p_new * q_new
            })
            
            p, q = p_new, q_new
            
            # Check for fixation
            if p == 0 or p == 1:
                break
        
        return pd.DataFrame(results)
    
    @staticmethod
    def analyze_gene_expression(expression_matrix: pd.DataFrame, 
                               groups: List[str]) -> Dict[str, Any]:
        """
        Perform basic gene expression analysis
        
        Args:
            expression_matrix: Genes x Samples expression matrix
            groups: List of group labels for samples
            
        Returns:
            Analysis results including DE genes
        """
        from scipy import stats
        
        # Ensure groups is array-like
        groups = np.array(groups)
        unique_groups = np.unique(groups)
        
        if len(unique_groups) != 2:
            return {'error': 'Currently only supports two-group comparison'}
        
        # Separate groups
        group1_mask = groups == unique_groups[0]
        group2_mask = groups == unique_groups[1]
        
        # Perform differential expression analysis
        de_results = []
        
        for gene in expression_matrix.index:
            group1_expr = expression_matrix.loc[gene, group1_mask].values
            group2_expr = expression_matrix.loc[gene, group2_mask].values
            
            # T-test
            t_stat, p_value = stats.ttest_ind(group1_expr, group2_expr)
            
            # Calculate fold change
            mean1 = np.mean(group1_expr)
            mean2 = np.mean(group2_expr)
            
            if mean2 != 0:
                fold_change = mean1 / mean2
                log2_fc = np.log2(fold_change) if fold_change > 0 else np.nan
            else:
                fold_change = np.inf if mean1 > 0 else 0
                log2_fc = np.inf if mean1 > 0 else -np.inf
            
            de_results.append({
                'gene': gene,
                'mean_group1': mean1,
                'mean_group2': mean2,
                'fold_change': fold_change,
                'log2_fold_change': log2_fc,
                't_statistic': t_stat,
                'p_value': p_value
            })
        
        de_df = pd.DataFrame(de_results)
        
        # Multiple testing correction (Benjamini-Hochberg)
        from statsmodels.stats.multitest import multipletests
        de_df['p_adjusted'] = multipletests(de_df['p_value'], method='fdr_bh')[1]
        
        # Mark significant genes
        de_df['significant'] = (de_df['p_adjusted'] < 0.05) & (np.abs(de_df['log2_fold_change']) > 1)
        
        return {
            'de_results': de_df,
            'num_significant': de_df['significant'].sum(),
            'group_names': unique_groups.tolist(),
            'total_genes': len(expression_matrix)
        }


# Export convenient functions for direct use
def quick_sequence_analysis(sequence: str, seq_type: str = 'auto') -> Dict[str, Any]:
    """
    Quick analysis of any biological sequence
    
    Args:
        sequence: Biological sequence
        seq_type: 'dna', 'rna', 'protein', or 'auto'
    
    Returns:
        Analysis results
    """
    tools = BiologyTools()
    
    # Auto-detect sequence type if needed
    if seq_type == 'auto':
        seq_upper = sequence.upper()
        if all(c in 'ATGC' for c in seq_upper.replace(' ', '').replace('\n', '')):
            seq_type = 'dna'
        elif all(c in 'AUGC' for c in seq_upper.replace(' ', '').replace('\n', '')):
            seq_type = 'rna'
        else:
            seq_type = 'protein'
    
    if seq_type == 'dna':
        return tools.analyze_dna_sequence(sequence).__dict__
    elif seq_type == 'protein':
        return tools.analyze_protein_sequence(sequence)
    else:
        return {'error': f'Unsupported sequence type: {seq_type}'}