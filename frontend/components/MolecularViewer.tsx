import React, { useEffect, useRef, useState } from 'react';
import { Molecule, RotateCcw, ZoomIn, ZoomOut, Download, Upload, Eye, EyeOff } from 'lucide-react';

interface MolecularViewerProps {
  sessionId: string;
}

interface MoleculeData {
  id: string;
  name: string;
  pdb_data?: string;
  smiles?: string;
  type: 'protein' | 'small_molecule' | 'dna' | 'rna';
  visible: boolean;
}

export default function MolecularViewer({ sessionId }: MolecularViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const [molecules, setMolecules] = useState<MoleculeData[]>([]);
  const [selectedMolecule, setSelectedMolecule] = useState<string>('');
  const [viewerReady, setViewerReady] = useState(false);
  const [loading, setLoading] = useState(false);

  // Initialize 3Dmol viewer
  useEffect(() => {
    const initViewer = async () => {
      if (!viewerRef.current || viewerReady) return;

      try {
        // Load 3Dmol.js dynamically
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/3dmol@latest/build/3Dmol-min.js';
        script.onload = () => {
          if (viewerRef.current && (window as any).$3Dmol) {
            const viewer = (window as any).$3Dmol.createViewer(viewerRef.current, {
              width: '100%',
              height: 400,
              backgroundColor: '#1a1a1a'
            });
            
            // Store viewer reference
            (viewerRef.current as any).viewer = viewer;
            setViewerReady(true);
          }
        };
        document.head.appendChild(script);
      } catch (error) {
        console.error('Failed to initialize 3Dmol viewer:', error);
      }
    };

    initViewer();

    return () => {
      // Cleanup
      const scripts = document.querySelectorAll('script[src*="3Dmol"]');
      scripts.forEach(script => script.remove());
    };
  }, [viewerReady]);

  const loadMoleculeFromPDB = async (pdbId: string) => {
    if (!viewerReady || !viewerRef.current) return;

    setLoading(true);
    try {
      const response = await fetch(`https://files.rcsb.org/view/${pdbId}.pdb`);
      const pdbData = await response.text();
      
      const viewer = (viewerRef.current as any).viewer;
      viewer.clear();
      viewer.addModel(pdbData, 'pdb');
      viewer.setStyle({}, { cartoon: { color: 'spectrum' } });
      viewer.zoomTo();
      viewer.render();

      const newMolecule: MoleculeData = {
        id: pdbId,
        name: `PDB: ${pdbId.toUpperCase()}`,
        pdb_data: pdbData,
        type: 'protein',
        visible: true
      };

      setMolecules(prev => [...prev.filter(m => m.id !== pdbId), newMolecule]);
      setSelectedMolecule(pdbId);
    } catch (error) {
      console.error('Failed to load PDB:', error);
    }
    setLoading(false);
  };

  const loadMoleculeFromSMILES = async (smiles: string, name: string) => {
    if (!viewerReady || !viewerRef.current) return;

    setLoading(true);
    try {
      // Generate 3D coordinates for SMILES (simplified approach)
      const viewer = (viewerRef.current as any).viewer;
      viewer.clear();
      
      // For demo purposes, we'll create a simple representation
      // In production, you'd use RDKit or similar to generate 3D coords
      viewer.addModel(`
HETATM    1  C   LIG A   1      -2.014   1.435   0.000  1.00  0.00           C
HETATM    2  C   LIG A   1      -0.514   1.435   0.000  1.00  0.00           C
HETATM    3  C   LIG A   1       0.236   0.248   0.000  1.00  0.00           C
HETATM    4  C   LIG A   1      -0.514  -0.939   0.000  1.00  0.00           C
HETATM    5  C   LIG A   1      -2.014  -0.939   0.000  1.00  0.00           C
HETATM    6  C   LIG A   1      -2.764   0.248   0.000  1.00  0.00           C
CONECT    1    2    6
CONECT    2    1    3
CONECT    3    2    4
CONECT    4    3    5
CONECT    5    4    6
CONECT    6    5    1
END
`, 'pdb');
      
      viewer.setStyle({}, { stick: { colorscheme: 'Jmol' }, sphere: { scale: 0.3 } });
      viewer.zoomTo();
      viewer.render();

      const newMolecule: MoleculeData = {
        id: name.toLowerCase().replace(/\s+/g, '_'),
        name: name,
        smiles: smiles,
        type: 'small_molecule',
        visible: true
      };

      setMolecules(prev => [...prev, newMolecule]);
      setSelectedMolecule(newMolecule.id);
    } catch (error) {
      console.error('Failed to load SMILES:', error);
    }
    setLoading(false);
  };

  const toggleMoleculeVisibility = (moleculeId: string) => {
    setMolecules(prev => prev.map(mol => 
      mol.id === moleculeId ? { ...mol, visible: !mol.visible } : mol
    ));
    
    // Update viewer
    if (viewerReady && viewerRef.current) {
      const viewer = (viewerRef.current as any).viewer;
      const molecule = molecules.find(m => m.id === moleculeId);
      if (molecule) {
        viewer.setStyle({ model: molecules.indexOf(molecule) }, 
          molecule.visible ? {} : { cartoon: { hidden: true }, stick: { hidden: true } }
        );
        viewer.render();
      }
    }
  };

  const resetView = () => {
    if (viewerReady && viewerRef.current) {
      const viewer = (viewerRef.current as any).viewer;
      viewer.zoomTo();
      viewer.render();
    }
  };

  const changeRepresentation = (style: string) => {
    if (!viewerReady || !viewerRef.current) return;

    const viewer = (viewerRef.current as any).viewer;
    viewer.setStyle({}, {});

    switch (style) {
      case 'cartoon':
        viewer.setStyle({}, { cartoon: { color: 'spectrum' } });
        break;
      case 'surface':
        viewer.setStyle({}, { surface: { opacity: 0.8, color: 'white' } });
        break;
      case 'stick':
        viewer.setStyle({}, { stick: { colorscheme: 'Jmol' } });
        break;
      case 'sphere':
        viewer.setStyle({}, { sphere: { colorscheme: 'Jmol' } });
        break;
    }
    viewer.render();
  };

  const downloadImage = () => {
    if (viewerReady && viewerRef.current) {
      const viewer = (viewerRef.current as any).viewer;
      const imgData = viewer.pngURI();
      const link = document.createElement('a');
      link.download = 'molecular_structure.png';
      link.href = imgData;
      link.click();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Molecule className="w-5 h-5 text-blue-400" />
          3D Molecular Viewer
        </h3>
        
        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={resetView}
            className="p-2 text-slate-400 hover:text-white transition-colors"
            title="Reset View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={downloadImage}
            className="p-2 text-slate-400 hover:text-white transition-colors"
            title="Download Image"
            disabled={!viewerReady}
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Sidebar */}
        <div className="w-64 border-r border-white/10 p-4">
          {/* Load Molecule */}
          <div className="mb-4">
            <h4 className="text-white text-sm font-medium mb-2">Load Structure</h4>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="PDB ID (e.g., 1crn)"
                className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    const value = (e.target as HTMLInputElement).value.trim();
                    if (value) loadMoleculeFromPDB(value);
                  }
                }}
              />
              <input
                type="text"
                placeholder="SMILES (e.g., CCO)"
                className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    const value = (e.target as HTMLInputElement).value.trim();
                    if (value) loadMoleculeFromSMILES(value, 'Custom Molecule');
                  }
                }}
              />
            </div>
          </div>

          {/* Representation Style */}
          <div className="mb-4">
            <h4 className="text-white text-sm font-medium mb-2">Style</h4>
            <select
              onChange={(e) => changeRepresentation(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
            >
              <option value="cartoon">Cartoon</option>
              <option value="surface">Surface</option>
              <option value="stick">Stick</option>
              <option value="sphere">Space-filling</option>
            </select>
          </div>

          {/* Loaded Molecules */}
          <div>
            <h4 className="text-white text-sm font-medium mb-2">Loaded Structures</h4>
            <div className="space-y-1">
              {molecules.map((molecule) => (
                <div
                  key={molecule.id}
                  className="flex items-center justify-between p-2 bg-slate-800 rounded text-sm"
                >
                  <span className="text-white truncate">{molecule.name}</span>
                  <button
                    onClick={() => toggleMoleculeVisibility(molecule.id)}
                    className="text-slate-400 hover:text-white"
                  >
                    {molecule.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                </div>
              ))}
              {molecules.length === 0 && (
                <p className="text-slate-400 text-xs">No structures loaded</p>
              )}
            </div>
          </div>

          {/* Quick Examples */}
          <div className="mt-4 pt-4 border-t border-slate-600">
            <h4 className="text-white text-sm font-medium mb-2">Examples</h4>
            <div className="space-y-1">
              <button
                onClick={() => loadMoleculeFromPDB('1crn')}
                className="w-full text-left p-2 text-xs text-slate-300 hover:bg-slate-800 rounded"
                disabled={loading}
              >
                Crambin (1CRN)
              </button>
              <button
                onClick={() => loadMoleculeFromPDB('1a0m')}
                className="w-full text-left p-2 text-xs text-slate-300 hover:bg-slate-800 rounded"
                disabled={loading}
              >
                Insulin (1A0M)
              </button>
              <button
                onClick={() => loadMoleculeFromSMILES('CC(=O)OC1=CC=CC=C1C(=O)O', 'Aspirin')}
                className="w-full text-left p-2 text-xs text-slate-300 hover:bg-slate-800 rounded"
                disabled={loading}
              >
                Aspirin
              </button>
            </div>
          </div>
        </div>

        {/* 3D Viewer */}
        <div className="flex-1 relative">
          <div 
            ref={viewerRef}
            className="w-full h-full bg-slate-900"
            style={{ minHeight: '400px' }}
          />
          
          {!viewerReady && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-slate-400 text-sm">Loading 3D viewer...</p>
              </div>
            </div>
          )}
          
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-white text-sm">Loading structure...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}