import React, { useState, useEffect } from 'react';
import { Flask, Target, Zap, ChevronRight, Plus, Trash2, Play, FileText, BarChart3 } from 'lucide-react';

interface Hypothesis {
  id: string;
  statement: string;
  confidence: number;
  priority: 'high' | 'medium' | 'low';
  tags: string[];
}

interface ExperimentTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  parameters: ExperimentParameter[];
  expectedOutputs: string[];
  codeTemplate: string;
}

interface ExperimentParameter {
  name: string;
  type: 'number' | 'string' | 'boolean' | 'select' | 'range';
  default: any;
  options?: string[];
  min?: number;
  max?: number;
  required: boolean;
  description: string;
}

interface Experiment {
  id: string;
  name: string;
  template: string;
  parameters: Record<string, any>;
  status: 'draft' | 'running' | 'completed' | 'failed';
  hypothesis?: string;
  results?: any;
  createdAt: Date;
}

const experimentTemplates: ExperimentTemplate[] = [
  {
    id: 'drug_screening',
    name: 'Virtual Drug Screening',
    category: 'Drug Discovery',
    description: 'Screen compounds against target proteins using molecular docking',
    parameters: [
      {
        name: 'target_protein',
        type: 'string',
        default: '1a0m',
        required: true,
        description: 'PDB ID of target protein'
      },
      {
        name: 'compound_library',
        type: 'select',
        default: 'approved_drugs',
        options: ['approved_drugs', 'natural_products', 'custom'],
        required: true,
        description: 'Compound library to screen'
      },
      {
        name: 'num_compounds',
        type: 'number',
        default: 100,
        min: 10,
        max: 10000,
        required: true,
        description: 'Number of compounds to screen'
      },
      {
        name: 'binding_threshold',
        type: 'number',
        default: -7.0,
        min: -15.0,
        max: 0.0,
        required: true,
        description: 'Binding affinity threshold (kcal/mol)'
      }
    ],
    expectedOutputs: ['binding_scores.csv', 'top_hits.png', 'docking_results.json'],
    codeTemplate: `
# Virtual Drug Screening Experiment
import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors
import matplotlib.pyplot as plt

# Experiment parameters
target_protein = "{{target_protein}}"
compound_library = "{{compound_library}}"
num_compounds = {{num_compounds}}
binding_threshold = {{binding_threshold}}

print(f"=== Virtual Drug Screening ===")
print(f"Target: {target_protein}")
print(f"Library: {compound_library}")
print(f"Compounds: {num_compounds}")
print(f"Threshold: {binding_threshold} kcal/mol")

# Simulate molecular docking results
np.random.seed(42)
compounds = []
for i in range(num_compounds):
    # Generate synthetic SMILES and properties
    smiles = f"C{'C' * np.random.randint(5, 20)}N{'O' * np.random.randint(1, 3)}"
    binding_score = np.random.normal(-6.0, 2.0)
    
    compounds.append({
        'compound_id': f'COMP_{i+1:04d}',
        'smiles': smiles,
        'binding_score': binding_score,
        'molecular_weight': np.random.uniform(150, 500),
        'logp': np.random.uniform(-2, 5),
        'drug_like': binding_score < binding_threshold
    })

results_df = pd.DataFrame(compounds)

# Filter hits
hits = results_df[results_df['binding_score'] < binding_threshold].copy()
hits = hits.sort_values('binding_score')

print(f"\\nScreening Results:")
print(f"Total compounds: {len(results_df)}")
print(f"Hits (< {binding_threshold}): {len(hits)}")
print(f"Hit rate: {len(hits)/len(results_df)*100:.1f}%")

# Visualize results
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Binding score distribution
axes[0,0].hist(results_df['binding_score'], bins=30, alpha=0.7, color='blue')
axes[0,0].axvline(binding_threshold, color='red', linestyle='--', label='Threshold')
axes[0,0].set_xlabel('Binding Score (kcal/mol)')
axes[0,0].set_ylabel('Count')
axes[0,0].set_title('Binding Score Distribution')
axes[0,0].legend()

# MW vs LogP
scatter = axes[0,1].scatter(results_df['molecular_weight'], results_df['logp'], 
                          c=results_df['binding_score'], cmap='RdYlBu', alpha=0.6)
axes[0,1].set_xlabel('Molecular Weight')
axes[0,1].set_ylabel('LogP')
axes[0,1].set_title('Chemical Space Coverage')
plt.colorbar(scatter, ax=axes[0,1], label='Binding Score')

# Top hits
if len(hits) > 0:
    top_10 = hits.head(10)
    axes[1,0].barh(range(len(top_10)), top_10['binding_score'])
    axes[1,0].set_yticks(range(len(top_10)))
    axes[1,0].set_yticklabels(top_10['compound_id'])
    axes[1,0].set_xlabel('Binding Score (kcal/mol)')
    axes[1,0].set_title('Top 10 Hits')

# Drug-likeness pie chart
drug_like_counts = results_df['drug_like'].value_counts()
axes[1,1].pie(drug_like_counts.values, labels=['Non-drug-like', 'Drug-like'], autopct='%1.1f%%')
axes[1,1].set_title('Drug-likeness Distribution')

plt.tight_layout()
plt.savefig('/workspace/outputs/drug_screening_results.png', dpi=300, bbox_inches='tight')
plt.show()

# Save results
results_df.to_csv('/workspace/outputs/screening_results.csv', index=False)
hits.to_csv('/workspace/outputs/top_hits.csv', index=False)

print(f"\\nTop 5 Hits:")
print(hits[['compound_id', 'binding_score', 'molecular_weight', 'logp']].head())
`
  },
  {
    id: 'gene_expression',
    name: 'Gene Expression Perturbation',
    category: 'Functional Genomics',
    description: 'Simulate gene knockout/overexpression effects on cellular pathways',
    parameters: [
      {
        name: 'target_gene',
        type: 'string',
        default: 'TP53',
        required: true,
        description: 'Gene to perturb'
      },
      {
        name: 'perturbation_type',
        type: 'select',
        default: 'knockout',
        options: ['knockout', 'overexpression', 'knockdown'],
        required: true,
        description: 'Type of perturbation'
      },
      {
        name: 'fold_change',
        type: 'range',
        default: [0.1, 10.0],
        min: 0.01,
        max: 100.0,
        required: true,
        description: 'Expression fold change range'
      },
      {
        name: 'num_samples',
        type: 'number',
        default: 20,
        min: 5,
        max: 100,
        required: true,
        description: 'Number of samples per condition'
      }
    ],
    expectedOutputs: ['expression_heatmap.png', 'pathway_analysis.csv', 'de_genes.csv'],
    codeTemplate: `
# Gene Expression Perturbation Experiment
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats

# Experiment parameters
target_gene = "{{target_gene}}"
perturbation_type = "{{perturbation_type}}"
fold_change_range = {{fold_change}}
num_samples = {{num_samples}}

print(f"=== Gene Expression Perturbation Experiment ===")
print(f"Target Gene: {target_gene}")
print(f"Perturbation: {perturbation_type}")
print(f"Samples: {num_samples} per condition")

# Simulate gene expression data
np.random.seed(42)
genes = ['TP53', 'MDM2', 'CDKN1A', 'BAX', 'BCL2', 'MYC', 'RB1', 'E2F1', 
         'CCND1', 'CDK4', 'PTEN', 'AKT1', 'PIK3CA', 'EGFR', 'KRAS']

# Control samples
control_data = np.random.lognormal(mean=5, sigma=1, size=(len(genes), num_samples))
control_df = pd.DataFrame(control_data, index=genes, 
                         columns=[f'Control_{i+1}' for i in range(num_samples)])

# Perturbed samples
perturbed_data = control_data.copy()

# Apply perturbation to target gene and downstream effects
if perturbation_type == 'knockout':
    perturbed_data[genes.index(target_gene), :] *= 0.1
elif perturbation_type == 'overexpression':
    perturbed_data[genes.index(target_gene), :] *= 10.0
else:  # knockdown
    perturbed_data[genes.index(target_gene), :] *= 0.3

# Simulate downstream effects
downstream_effects = {
    'TP53': {'MDM2': -0.5, 'CDKN1A': 2.0, 'BAX': 1.5, 'BCL2': -1.2},
    'MYC': {'E2F1': 1.8, 'CCND1': 1.5, 'CDK4': 1.3},
    'PTEN': {'AKT1': -1.5, 'PIK3CA': -1.2}
}

if target_gene in downstream_effects:
    for gene, effect in downstream_effects[target_gene].items():
        if gene in genes:
            gene_idx = genes.index(gene)
            if perturbation_type == 'knockout':
                perturbed_data[gene_idx, :] *= (1 + effect * 0.1)
            else:
                perturbed_data[gene_idx, :] *= (1 + effect)

perturbed_df = pd.DataFrame(perturbed_data, index=genes,
                           columns=[f'Perturbed_{i+1}' for i in range(num_samples)])

# Combine data
combined_df = pd.concat([control_df, perturbed_df], axis=1)

# Differential expression analysis
de_results = []
for gene in genes:
    control_vals = control_df.loc[gene].values
    perturbed_vals = perturbed_df.loc[gene].values
    
    # t-test
    t_stat, p_val = stats.ttest_ind(control_vals, perturbed_vals)
    
    # Calculate fold change
    fc = np.mean(perturbed_vals) / np.mean(control_vals)
    log2_fc = np.log2(fc)
    
    de_results.append({
        'Gene': gene,
        'Control_Mean': np.mean(control_vals),
        'Perturbed_Mean': np.mean(perturbed_vals),
        'Fold_Change': fc,
        'Log2_FC': log2_fc,
        'P_value': p_val,
        'Significant': p_val < 0.05 and abs(log2_fc) > 1
    })

de_df = pd.DataFrame(de_results)

# Visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Expression heatmap
log_data = np.log2(combined_df + 1)
sns.heatmap(log_data, ax=axes[0,0], cmap='RdBu_r', center=0, 
            cbar_kws={'label': 'Log2 Expression'})
axes[0,0].set_title('Gene Expression Heatmap')

# Volcano plot
axes[0,1].scatter(de_df['Log2_FC'], -np.log10(de_df['P_value']), 
                 c=['red' if sig else 'gray' for sig in de_df['Significant']])
axes[0,1].axhline(-np.log10(0.05), color='black', linestyle='--', alpha=0.5)
axes[0,1].axvline(1, color='black', linestyle='--', alpha=0.5)
axes[0,1].axvline(-1, color='black', linestyle='--', alpha=0.5)
axes[0,1].set_xlabel('Log2 Fold Change')
axes[0,1].set_ylabel('-Log10(P-value)')
axes[0,1].set_title('Volcano Plot')

# Target gene expression
target_idx = genes.index(target_gene)
axes[1,0].boxplot([control_df.iloc[target_idx].values, perturbed_df.iloc[target_idx].values],
                  labels=['Control', 'Perturbed'])
axes[1,0].set_ylabel('Expression Level')
axes[1,0].set_title(f'{target_gene} Expression')

# Pathway enrichment (simplified)
significant_genes = de_df[de_df['Significant']]['Gene'].tolist()
pathway_scores = np.random.uniform(0, 5, 5)
pathways = ['Cell Cycle', 'Apoptosis', 'DNA Repair', 'Growth Signaling', 'Metabolism']

axes[1,1].barh(pathways, pathway_scores)
axes[1,1].set_xlabel('Enrichment Score')
axes[1,1].set_title('Pathway Enrichment')

plt.tight_layout()
plt.savefig('/workspace/outputs/gene_perturbation_results.png', dpi=300, bbox_inches='tight')
plt.show()

# Save results
combined_df.to_csv('/workspace/outputs/expression_data.csv')
de_df.to_csv('/workspace/outputs/differential_expression.csv', index=False)

print(f"\\nDifferential Expression Results:")
print(f"Significantly changed genes: {de_df['Significant'].sum()}/{len(genes)}")
print("\\nTop changed genes:")
print(de_df.sort_values('P_value')[['Gene', 'Log2_FC', 'P_value', 'Significant']].head())
`
  },
  {
    id: 'population_genetics',
    name: 'Population Genetics Simulation',
    category: 'Evolution',
    description: 'Simulate allele frequency changes under selection, drift, and mutation',
    parameters: [
      {
        name: 'population_size',
        type: 'number',
        default: 1000,
        min: 10,
        max: 100000,
        required: true,
        description: 'Population size (Ne)'
      },
      {
        name: 'generations',
        type: 'number',
        default: 100,
        min: 10,
        max: 1000,
        required: true,
        description: 'Number of generations'
      },
      {
        name: 'selection_coefficient',
        type: 'number',
        default: 0.1,
        min: 0.0,
        max: 1.0,
        required: true,
        description: 'Selection coefficient (s)'
      },
      {
        name: 'mutation_rate',
        type: 'number',
        default: 1e-4,
        min: 1e-6,
        max: 1e-2,
        required: true,
        description: 'Mutation rate per generation'
      }
    ],
    expectedOutputs: ['allele_frequencies.png', 'evolution_summary.csv'],
    codeTemplate: `
# Population Genetics Simulation
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Parameters
population_size = {{population_size}}
generations = {{generations}}
selection_coefficient = {{selection_coefficient}}
mutation_rate = {{mutation_rate}}

print(f"=== Population Genetics Simulation ===")
print(f"Population size: {population_size}")
print(f"Generations: {generations}")
print(f"Selection coefficient: {selection_coefficient}")
print(f"Mutation rate: {mutation_rate}")

# Initialize
np.random.seed(42)
p = 0.5  # Initial allele frequency
results = []

for gen in range(generations):
    # Selection (assuming AA=1, Aa=1-s/2, aa=1-s fitness)
    w_AA = 1.0
    w_Aa = 1.0 - selection_coefficient/2
    w_aa = 1.0 - selection_coefficient
    
    q = 1 - p
    w_mean = p**2 * w_AA + 2*p*q * w_Aa + q**2 * w_aa
    
    # Update after selection
    p_new = (p**2 * w_AA + p*q * w_Aa) / w_mean
    
    # Mutation
    p_new = p_new * (1 - mutation_rate) + (1 - p_new) * mutation_rate
    
    # Genetic drift (binomial sampling)
    if population_size < float('inf'):
        num_A = np.random.binomial(2 * population_size, p_new)
        p_new = num_A / (2 * population_size)
    
    results.append({
        'Generation': gen,
        'Allele_A_Freq': p_new,
        'Allele_a_Freq': 1 - p_new,
        'Heterozygosity': 2 * p_new * (1 - p_new),
        'Mean_Fitness': w_mean
    })
    
    p = p_new
    
    # Check for fixation
    if p == 0 or p == 1:
        print(f"Allele fixed at generation {gen}")
        break

results_df = pd.DataFrame(results)

# Visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Allele frequencies over time
axes[0,0].plot(results_df['Generation'], results_df['Allele_A_Freq'], 'b-', label='Allele A', linewidth=2)
axes[0,0].plot(results_df['Generation'], results_df['Allele_a_Freq'], 'r-', label='Allele a', linewidth=2)
axes[0,0].set_xlabel('Generation')
axes[0,0].set_ylabel('Allele Frequency')
axes[0,0].set_title('Allele Frequency Evolution')
axes[0,0].legend()
axes[0,0].grid(True, alpha=0.3)

# Heterozygosity
axes[0,1].plot(results_df['Generation'], results_df['Heterozygosity'], 'g-', linewidth=2)
axes[0,1].set_xlabel('Generation')
axes[0,1].set_ylabel('Heterozygosity')
axes[0,1].set_title('Heterozygosity Over Time')
axes[0,1].grid(True, alpha=0.3)

# Mean fitness
axes[1,0].plot(results_df['Generation'], results_df['Mean_Fitness'], 'purple', linewidth=2)
axes[1,0].set_xlabel('Generation')
axes[1,0].set_ylabel('Mean Population Fitness')
axes[1,0].set_title('Population Fitness')
axes[1,0].grid(True, alpha=0.3)

# Phase plot
axes[1,1].plot(results_df['Allele_A_Freq'], results_df['Heterozygosity'], 'o-', markersize=3)
axes[1,1].set_xlabel('Allele A Frequency')
axes[1,1].set_ylabel('Heterozygosity')
axes[1,1].set_title('Frequency vs Heterozygosity')
axes[1,1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/workspace/outputs/population_genetics.png', dpi=300, bbox_inches='tight')
plt.show()

# Summary statistics
final_freq = results_df.iloc[-1]['Allele_A_Freq']
print(f"\\nSimulation Summary:")
print(f"Final allele A frequency: {final_freq:.4f}")
print(f"Change from initial: {final_freq - 0.5:.4f}")
print(f"Final heterozygosity: {results_df.iloc[-1]['Heterozygosity']:.4f}")

results_df.to_csv('/workspace/outputs/evolution_results.csv', index=False)
`
  }
];

interface VirtualExperimentDesignerProps {
  sessionId: string;
  onGenerateCode: (code: string) => void;
}

export default function VirtualExperimentDesigner({ sessionId, onGenerateCode }: VirtualExperimentDesignerProps) {
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<ExperimentTemplate | null>(null);
  const [experimentParameters, setExperimentParameters] = useState<Record<string, any>>({});
  const [newHypothesis, setNewHypothesis] = useState('');
  const [activeTab, setActiveTab] = useState<'hypotheses' | 'experiments' | 'templates'>('hypotheses');

  // Load saved data
  useEffect(() => {
    loadSavedData();
  }, [sessionId]);

  const loadSavedData = () => {
    // In production, load from API
    const savedHypotheses = localStorage.getItem(`hypotheses_${sessionId}`);
    const savedExperiments = localStorage.getItem(`experiments_${sessionId}`);

    if (savedHypotheses) {
      setHypotheses(JSON.parse(savedHypotheses));
    }
    if (savedExperiments) {
      setExperiments(JSON.parse(savedExperiments));
    }
  };

  const saveData = (type: 'hypotheses' | 'experiments', data: any[]) => {
    localStorage.setItem(`${type}_${sessionId}`, JSON.stringify(data));
  };

  const addHypothesis = () => {
    if (!newHypothesis.trim()) return;

    const hypothesis: Hypothesis = {
      id: Date.now().toString(),
      statement: newHypothesis,
      confidence: 0.5,
      priority: 'medium',
      tags: []
    };

    const updated = [...hypotheses, hypothesis];
    setHypotheses(updated);
    saveData('hypotheses', updated);
    setNewHypothesis('');
  };

  const removeHypothesis = (id: string) => {
    const updated = hypotheses.filter(h => h.id !== id);
    setHypotheses(updated);
    saveData('hypotheses', updated);
  };

  const selectTemplate = (template: ExperimentTemplate) => {
    setSelectedTemplate(template);
    
    // Initialize parameters with defaults
    const params: Record<string, any> = {};
    template.parameters.forEach(param => {
      params[param.name] = param.default;
    });
    setExperimentParameters(params);
  };

  const updateParameter = (paramName: string, value: any) => {
    setExperimentParameters(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const generateExperimentCode = () => {
    if (!selectedTemplate) return;

    let code = selectedTemplate.codeTemplate;
    
    // Replace parameter placeholders
    Object.entries(experimentParameters).forEach(([key, value]) => {
      const placeholder = `{{${key}}}`;
      const replacement = Array.isArray(value) ? JSON.stringify(value) : value.toString();
      code = code.replace(new RegExp(placeholder, 'g'), replacement);
    });

    onGenerateCode(code);

    // Create experiment record
    const experiment: Experiment = {
      id: Date.now().toString(),
      name: `${selectedTemplate.name} - ${new Date().toLocaleString()}`,
      template: selectedTemplate.id,
      parameters: { ...experimentParameters },
      status: 'draft',
      createdAt: new Date()
    };

    const updated = [...experiments, experiment];
    setExperiments(updated);
    saveData('experiments', updated);
  };

  const renderParameterInput = (param: ExperimentParameter) => {
    const value = experimentParameters[param.name] ?? param.default;

    switch (param.type) {
      case 'number':
        return (
          <input
            type="number"
            value={value}
            min={param.min}
            max={param.max}
            onChange={(e) => updateParameter(param.name, parseFloat(e.target.value))}
            className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
          />
        );
      case 'string':
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => updateParameter(param.name, e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
          />
        );
      case 'boolean':
        return (
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={value}
              onChange={(e) => updateParameter(param.name, e.target.checked)}
              className="mr-2"
            />
            <span className="text-white text-sm">{value ? 'True' : 'False'}</span>
          </label>
        );
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => updateParameter(param.name, e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
          >
            {param.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        );
      case 'range':
        return (
          <div className="flex gap-2">
            <input
              type="number"
              value={value[0]}
              min={param.min}
              max={param.max}
              onChange={(e) => updateParameter(param.name, [parseFloat(e.target.value), value[1]])}
              className="flex-1 px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
            />
            <span className="text-white self-center">to</span>
            <input
              type="number"
              value={value[1]}
              min={param.min}
              max={param.max}
              onChange={(e) => updateParameter(param.name, [value[0], parseFloat(e.target.value)])}
              className="flex-1 px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Flask className="w-5 h-5 text-green-400" />
          Virtual Experiment Designer
        </h3>
        
        {/* Tab Navigation */}
        <div className="flex items-center gap-1">
          {[
            { id: 'hypotheses', label: 'Hypotheses', icon: Target },
            { id: 'templates', label: 'Templates', icon: FileText },
            { id: 'experiments', label: 'Experiments', icon: BarChart3 }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`px-3 py-1 rounded text-sm flex items-center gap-2 ${
                activeTab === id
                  ? 'bg-green-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 p-4">
        {/* Hypotheses Tab */}
        {activeTab === 'hypotheses' && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={newHypothesis}
                onChange={(e) => setNewHypothesis(e.target.value)}
                placeholder="Enter a hypothesis to test..."
                className="flex-1 px-3 py-2 bg-slate-800 text-white rounded border border-slate-600 focus:border-green-500 focus:outline-none"
                onKeyPress={(e) => e.key === 'Enter' && addHypothesis()}
              />
              <button
                onClick={addHypothesis}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>

            <div className="space-y-2">
              {hypotheses.map((hypothesis) => (
                <div key={hypothesis.id} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <p className="text-white font-medium mb-2">{hypothesis.statement}</p>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-slate-400">
                          Confidence: {(hypothesis.confidence * 100).toFixed(0)}%
                        </span>
                        <span className={`px-2 py-1 rounded text-xs ${
                          hypothesis.priority === 'high' ? 'bg-red-600 text-white' :
                          hypothesis.priority === 'medium' ? 'bg-yellow-600 text-white' :
                          'bg-gray-600 text-white'
                        }`}>
                          {hypothesis.priority} priority
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => removeHypothesis(hypothesis.id)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
              
              {hypotheses.length === 0 && (
                <div className="text-center py-8">
                  <Target className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">No hypotheses yet</p>
                  <p className="text-slate-500 text-sm mt-1">Add hypotheses to guide your experiments</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <h4 className="text-white font-medium mb-3">Experiment Templates</h4>
              <div className="space-y-2">
                {experimentTemplates.map((template) => (
                  <div
                    key={template.id}
                    onClick={() => selectTemplate(template)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedTemplate?.id === template.id
                        ? 'bg-green-600/20 border-green-500'
                        : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h5 className="text-white font-medium">{template.name}</h5>
                        <p className="text-slate-400 text-sm mt-1">{template.description}</p>
                        <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded mt-2 inline-block">
                          {template.category}
                        </span>
                      </div>
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Parameter Configuration */}
            {selectedTemplate && (
              <div>
                <h4 className="text-white font-medium mb-3">Configure Parameters</h4>
                <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                  <h5 className="text-white font-medium mb-3">{selectedTemplate.name}</h5>
                  
                  <div className="space-y-4">
                    {selectedTemplate.parameters.map((param) => (
                      <div key={param.name}>
                        <label className="block text-white text-sm font-medium mb-1">
                          {param.name.replace(/_/g, ' ').toUpperCase()}
                          {param.required && <span className="text-red-400 ml-1">*</span>}
                        </label>
                        <p className="text-slate-400 text-xs mb-2">{param.description}</p>
                        {renderParameterInput(param)}
                      </div>
                    ))}
                  </div>

                  <div className="mt-6">
                    <button
                      onClick={generateExperimentCode}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center justify-center gap-2"
                    >
                      <Play className="w-4 h-4" />
                      Generate Experiment Code
                    </button>
                  </div>

                  <div className="mt-4 text-xs text-slate-400">
                    <p className="font-medium mb-1">Expected Outputs:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {selectedTemplate.expectedOutputs.map((output, idx) => (
                        <li key={idx}>{output}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Experiments Tab */}
        {activeTab === 'experiments' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {experiments.map((experiment) => (
                <div key={experiment.id} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                  <div className="flex justify-between items-start mb-2">
                    <h5 className="text-white font-medium">{experiment.name}</h5>
                    <span className={`px-2 py-1 rounded text-xs ${
                      experiment.status === 'completed' ? 'bg-green-600 text-white' :
                      experiment.status === 'running' ? 'bg-blue-600 text-white' :
                      experiment.status === 'failed' ? 'bg-red-600 text-white' :
                      'bg-gray-600 text-white'
                    }`}>
                      {experiment.status}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm mb-2">
                    Created: {experiment.createdAt.toLocaleDateString()}
                  </p>
                  <p className="text-slate-400 text-xs">
                    Template: {experimentTemplates.find(t => t.id === experiment.template)?.name}
                  </p>
                </div>
              ))}
            </div>

            {experiments.length === 0 && (
              <div className="text-center py-8">
                <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">No experiments yet</p>
                <p className="text-slate-500 text-sm mt-1">Create experiments from templates</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}