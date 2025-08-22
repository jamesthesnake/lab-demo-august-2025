import React, { useEffect, useRef, useState } from 'react';
import { Network, GitBranch, Zap, Download, Upload, Settings, Play, Pause } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  group: string;
  value?: number;
  color?: string;
  x?: number;
  y?: number;
}

interface Edge {
  from: string;
  to: string;
  label?: string;
  value?: number;
  color?: string;
  width?: number;
}

interface NetworkData {
  nodes: Node[];
  edges: Edge[];
}

interface NetworkVisualizationProps {
  sessionId: string;
}

export default function NetworkVisualization({ sessionId }: NetworkVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [networkData, setNetworkData] = useState<NetworkData>({ nodes: [], edges: [] });
  const [selectedLayout, setSelectedLayout] = useState<string>('hierarchical');
  const [isAnimating, setIsAnimating] = useState(false);
  const [networkStats, setNetworkStats] = useState({
    nodeCount: 0,
    edgeCount: 0,
    density: 0,
    avgDegree: 0
  });

  // Initialize vis.js network
  useEffect(() => {
    const initNetwork = async () => {
      if (!containerRef.current) return;

      try {
        // Load vis.js dynamically
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js';
        script.onload = () => {
          if (containerRef.current && (window as any).vis) {
            createNetwork();
          }
        };
        document.head.appendChild(script);
      } catch (error) {
        console.error('Failed to initialize network visualization:', error);
      }
    };

    initNetwork();
  }, []);

  const createNetwork = () => {
    if (!containerRef.current || !(window as any).vis) return;

    const vis = (window as any).vis;
    
    // Network options
    const options = {
      layout: {
        hierarchical: selectedLayout === 'hierarchical' ? {
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 100,
          nodeSpacing: 100
        } : false
      },
      physics: {
        enabled: selectedLayout !== 'hierarchical',
        forceAtlas2Based: {
          gravitationalConstant: -26,
          centralGravity: 0.005,
          springLength: 230,
          springConstant: 0.18,
          avoidOverlap: 1.5
        },
        solver: 'forceAtlas2Based',
        timestep: 0.35,
        stabilization: { iterations: 150 }
      },
      nodes: {
        shape: 'dot',
        scaling: {
          min: 10,
          max: 30
        },
        font: {
          size: 12,
          face: 'Tahoma'
        }
      },
      edges: {
        width: 0.15,
        color: { inherit: 'from' },
        smooth: {
          type: 'continuous'
        },
        arrows: {
          to: { enabled: true, scaleFactor: 0.5 }
        }
      },
      interaction: {
        hideEdgesOnDrag: true,
        hideNodesOnDrag: true
      }
    };

    // Create DataSets
    const nodes = new vis.DataSet(networkData.nodes);
    const edges = new vis.DataSet(networkData.edges);
    const data = { nodes, edges };

    // Create network
    const network = new vis.Network(containerRef.current, data, options);
    
    // Store network instance
    (containerRef.current as any).network = network;

    // Update stats
    updateNetworkStats(networkData);
  };

  const updateNetworkStats = (data: NetworkData) => {
    const nodeCount = data.nodes.length;
    const edgeCount = data.edges.length;
    const maxEdges = nodeCount * (nodeCount - 1) / 2;
    const density = maxEdges > 0 ? edgeCount / maxEdges : 0;
    const avgDegree = nodeCount > 0 ? (2 * edgeCount) / nodeCount : 0;

    setNetworkStats({
      nodeCount,
      edgeCount,
      density: Math.round(density * 1000) / 1000,
      avgDegree: Math.round(avgDegree * 100) / 100
    });
  };

  const loadSampleNetwork = (type: string) => {
    let sampleData: NetworkData;

    switch (type) {
      case 'protein_interaction':
        sampleData = {
          nodes: [
            { id: '1', label: 'TP53', group: 'tumor_suppressor', value: 25, color: '#ff4444' },
            { id: '2', label: 'MDM2', group: 'oncogene', value: 20, color: '#4444ff' },
            { id: '3', label: 'ATM', group: 'kinase', value: 22, color: '#44ff44' },
            { id: '4', label: 'BRCA1', group: 'tumor_suppressor', value: 18, color: '#ff4444' },
            { id: '5', label: 'PTEN', group: 'tumor_suppressor', value: 16, color: '#ff4444' },
            { id: '6', label: 'AKT1', group: 'oncogene', value: 21, color: '#4444ff' },
            { id: '7', label: 'MYC', group: 'oncogene', value: 19, color: '#4444ff' },
            { id: '8', label: 'RB1', group: 'tumor_suppressor', value: 17, color: '#ff4444' }
          ],
          edges: [
            { from: '1', to: '2', label: 'inhibits', value: 5, color: '#ff0000' },
            { from: '2', to: '1', label: 'degrades', value: 4, color: '#ff0000' },
            { from: '3', to: '1', label: 'phosphorylates', value: 3, color: '#00ff00' },
            { from: '4', to: '3', label: 'activates', value: 4, color: '#00ff00' },
            { from: '5', to: '6', label: 'inhibits', value: 5, color: '#ff0000' },
            { from: '6', to: '7', label: 'activates', value: 3, color: '#00ff00' },
            { from: '1', to: '8', label: 'regulates', value: 2, color: '#0000ff' }
          ]
        };
        break;

      case 'metabolic_pathway':
        sampleData = {
          nodes: [
            { id: 'glc', label: 'Glucose', group: 'substrate', value: 20, color: '#ffaa00' },
            { id: 'g6p', label: 'G6P', group: 'intermediate', value: 15, color: '#00aaff' },
            { id: 'f6p', label: 'F6P', group: 'intermediate', value: 15, color: '#00aaff' },
            { id: 'fbp', label: 'FBP', group: 'intermediate', value: 15, color: '#00aaff' },
            { id: 'pyr', label: 'Pyruvate', group: 'product', value: 20, color: '#aa00ff' },
            { id: 'hk', label: 'Hexokinase', group: 'enzyme', value: 12, color: '#ff0000' },
            { id: 'pgi', label: 'PGI', group: 'enzyme', value: 12, color: '#ff0000' },
            { id: 'pfk', label: 'PFK', group: 'enzyme', value: 12, color: '#ff0000' }
          ],
          edges: [
            { from: 'glc', to: 'hk', label: 'substrate', value: 3 },
            { from: 'hk', to: 'g6p', label: 'product', value: 3 },
            { from: 'g6p', to: 'pgi', label: 'substrate', value: 3 },
            { from: 'pgi', to: 'f6p', label: 'product', value: 3 },
            { from: 'f6p', to: 'pfk', label: 'substrate', value: 3 },
            { from: 'pfk', to: 'fbp', label: 'product', value: 3 },
            { from: 'fbp', to: 'pyr', label: 'pathway', value: 2 }
          ]
        };
        break;

      case 'gene_regulatory':
        sampleData = {
          nodes: [
            { id: 'tf1', label: 'TF1', group: 'transcription_factor', value: 18, color: '#ff6666' },
            { id: 'tf2', label: 'TF2', group: 'transcription_factor', value: 16, color: '#ff6666' },
            { id: 'gene1', label: 'Gene A', group: 'gene', value: 14, color: '#66ff66' },
            { id: 'gene2', label: 'Gene B', group: 'gene', value: 15, color: '#66ff66' },
            { id: 'gene3', label: 'Gene C', group: 'gene', value: 13, color: '#66ff66' },
            { id: 'prot1', label: 'Protein A', group: 'protein', value: 12, color: '#6666ff' },
            { id: 'prot2', label: 'Protein B', group: 'protein', value: 11, color: '#6666ff' }
          ],
          edges: [
            { from: 'tf1', to: 'gene1', label: 'activates', value: 4, color: '#00ff00' },
            { from: 'tf1', to: 'gene2', label: 'represses', value: 3, color: '#ff0000' },
            { from: 'tf2', to: 'gene3', label: 'activates', value: 4, color: '#00ff00' },
            { from: 'gene1', to: 'prot1', label: 'codes for', value: 2, color: '#0000ff' },
            { from: 'gene2', to: 'prot2', label: 'codes for', value: 2, color: '#0000ff' },
            { from: 'prot1', to: 'tf2', label: 'feedback', value: 3, color: '#ffaa00' }
          ]
        };
        break;

      default:
        sampleData = { nodes: [], edges: [] };
    }

    setNetworkData(sampleData);
    
    // Recreate network with new data
    setTimeout(() => {
      createNetwork();
    }, 100);
  };

  const changeLayout = (layout: string) => {
    setSelectedLayout(layout);
    setTimeout(() => {
      createNetwork();
    }, 100);
  };

  const exportNetwork = () => {
    if (containerRef.current && (containerRef.current as any).network) {
      const network = (containerRef.current as any).network;
      const canvas = network.canvas.getContext();
      const link = document.createElement('a');
      link.download = 'network_visualization.png';
      link.href = canvas.canvas.toDataURL();
      link.click();
    }
  };

  const togglePhysics = () => {
    if (containerRef.current && (containerRef.current as any).network) {
      const network = (containerRef.current as any).network;
      const isEnabled = network.physics.physicsEnabled;
      network.setOptions({ physics: { enabled: !isEnabled } });
      setIsAnimating(!isEnabled);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Network className="w-5 h-5 text-purple-400" />
          Network Visualization
        </h3>
        
        <div className="flex items-center gap-2">
          <button
            onClick={togglePhysics}
            className="p-2 text-slate-400 hover:text-white transition-colors"
            title={isAnimating ? "Stop Physics" : "Start Physics"}
          >
            {isAnimating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={exportNetwork}
            className="p-2 text-slate-400 hover:text-white transition-colors"
            title="Export Network"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Sidebar */}
        <div className="w-64 border-r border-white/10 p-4">
          {/* Network Statistics */}
          <div className="mb-4">
            <h4 className="text-white text-sm font-medium mb-2">Network Statistics</h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Nodes:</span>
                <span className="text-white">{networkStats.nodeCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Edges:</span>
                <span className="text-white">{networkStats.edgeCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Density:</span>
                <span className="text-white">{networkStats.density}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Avg Degree:</span>
                <span className="text-white">{networkStats.avgDegree}</span>
              </div>
            </div>
          </div>

          {/* Layout Options */}
          <div className="mb-4">
            <h4 className="text-white text-sm font-medium mb-2">Layout</h4>
            <select
              value={selectedLayout}
              onChange={(e) => changeLayout(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-purple-500 focus:outline-none"
            >
              <option value="hierarchical">Hierarchical</option>
              <option value="force">Force-directed</option>
              <option value="circular">Circular</option>
            </select>
          </div>

          {/* Sample Networks */}
          <div className="mb-4">
            <h4 className="text-white text-sm font-medium mb-2">Load Sample Network</h4>
            <div className="space-y-2">
              <button
                onClick={() => loadSampleNetwork('protein_interaction')}
                className="w-full text-left p-2 text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 rounded"
              >
                Protein Interaction Network
              </button>
              <button
                onClick={() => loadSampleNetwork('metabolic_pathway')}
                className="w-full text-left p-2 text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 rounded"
              >
                Metabolic Pathway
              </button>
              <button
                onClick={() => loadSampleNetwork('gene_regulatory')}
                className="w-full text-left p-2 text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 rounded"
              >
                Gene Regulatory Network
              </button>
            </div>
          </div>

          {/* Legend */}
          <div>
            <h4 className="text-white text-sm font-medium mb-2">Legend</h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-slate-400">Tumor Suppressors</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span className="text-slate-400">Oncogenes</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-slate-400">Enzymes/Kinases</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-0.5 bg-red-500"></div>
                <span className="text-slate-400">Inhibition</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-0.5 bg-green-500"></div>
                <span className="text-slate-400">Activation</span>
              </div>
            </div>
          </div>
        </div>

        {/* Network Visualization */}
        <div className="flex-1 relative">
          <div 
            ref={containerRef}
            className="w-full h-full bg-slate-900"
            style={{ minHeight: '400px' }}
          />
          
          {networkData.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <Network className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">No network loaded</p>
                <p className="text-slate-500 text-xs mt-1">Load a sample network to get started</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}