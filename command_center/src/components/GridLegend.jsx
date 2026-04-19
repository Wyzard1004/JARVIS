/**
 * GridLegend Component
 * 
 * Reference chart for:
 * - Drone types and colors
 * - Entity types (enemies, structures)
 */

import React from 'react'

const DRONE_TYPES = [
  { type: 'soldier', label: 'Soldier Operator', color: '#7B68EE', symbol: 'square', range: '190u / 1.5 sectors' },
  { type: 'compute', label: 'Compute Drone', color: '#4169E1', symbol: 'diamond', range: '420u / 3.4 sectors' },
  { type: 'recon', label: 'Recon Drone', color: '#87CEEB', symbol: 'triangle', range: '140u / 1.1 sectors' },
  { type: 'attack', label: 'Attack Drone', color: '#00BFFF', symbol: 'star', range: '140u / 1.1 sectors' }
]

const ENTITY_TYPES = [
  { name: 'Enemy Tank', color: '#FF4500', shape: 'square' },
  { name: 'Enemy Infantry', color: '#FF6B6B', shape: 'circle' },
  { name: 'Building/Structure', color: '#8B7355', shape: 'square' },
  { name: 'Downed Aircraft', color: '#FFD93D', shape: 'triangle' },
  { name: 'Bridge', color: '#666666', shape: 'circle' }
]

function GridLegend({ activeDrones = [] }) {
  // Helper to render drone symbol shape
  const renderDroneSymbol = (symbol, color) => {
    switch (symbol) {
      case 'square':
        return (
          <div
            className="w-5 h-5 border border-gray-400"
            style={{ backgroundColor: color }}
          />
        )
      case 'diamond':
        return (
          <div
            className="w-5 h-5 border border-gray-400"
            style={{
              backgroundColor: color,
              transform: 'rotate(45deg)'
            }}
          />
        )
      case 'triangle':
        return (
          <div
            className="w-0 h-0"
            style={{
              borderLeft: '2.5px solid transparent',
              borderRight: '2.5px solid transparent',
              borderBottom: '5px solid ' + color
            }}
          />
        )
      case 'star':
        return (
          <div
            className="text-lg"
            style={{ color: color }}
          >
            ★
          </div>
        )
      default:
        return (
          <div
            className="w-4 h-4 rounded-full border border-gray-400"
            style={{ backgroundColor: color }}
          />
        )
    }
  }

  return (
    <div className="w-full space-y-4 p-4 bg-gray-700 border border-gray-600 rounded">
      {/* Drone Types & Colors */}
      <div>
        <h3 className="font-bold text-sm mb-2 text-gray-100">Drone Types & Transmission Range</h3>
        <div className="space-y-1.5">
          {DRONE_TYPES.map((drone) => (
            <div key={drone.type} className="flex items-center gap-3 text-xs">
              {renderDroneSymbol(drone.symbol, drone.color)}
              <span className="font-mono flex-1 text-gray-100">{drone.label}</span>
              <span className="text-gray-400 text-xs">{drone.range}</span>
            </div>
          ))}
        </div>
      </div>

      <hr className="border-gray-600" />

      {/* Entity Types */}
      <div>
        <h3 className="font-bold text-sm mb-2 text-gray-100">Entities (Enemy/Structure)</h3>
        <div className="space-y-1.5">
          {ENTITY_TYPES.map((entity) => (
            <div key={entity.name} className="flex items-center gap-3 text-xs">
              {entity.shape === 'square' ? (
                <div
                  className="w-4 h-4 border border-gray-400"
                  style={{ backgroundColor: entity.color }}
                />
              ) : entity.shape === 'triangle' ? (
                <div
                  className="w-0 h-0 border-l-2 border-r-2 border-b-4 border-l-transparent border-r-transparent"
                  style={{ borderBottomColor: entity.color }}
                />
              ) : (
                <div
                  className="w-4 h-4 rounded-full border border-gray-400"
                  style={{ backgroundColor: entity.color }}
                />
              )}
              <span className="font-mono flex-1 text-gray-100">{entity.name}</span>
            </div>
          ))}
        </div>
      </div>

      <hr className="border-gray-600" />

      {/* Legend */}
      <div>
        <h3 className="font-bold text-sm mb-2 text-gray-100">Interactive Elements</h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 border border-gray-400 rounded text-gray-200">◯</span>
            <span className="text-gray-300">Hover over drone for details</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 border-2 border-yellow-400 rounded text-yellow-400">◯</span>
            <span className="text-gray-300">Click drone to select/highlight</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-6 h-0.5" style={{ backgroundColor: '#CCCCCC' }} />
            <span className="text-gray-300">Transmission link (in range)</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-6 h-0.5" style={{ backgroundColor: '#FFD700' }} />
            <span className="text-gray-300">Spanning tree edge (primary link)</span>
          </div>
        </div>
      </div>

      {/* Active Drones Summary */}
      {activeDrones.length > 0 && (
        <>
          <hr className="border-gray-600" />
          <div>
            <h3 className="font-bold text-sm mb-2 text-gray-100">Active Drones ({activeDrones.length})</h3>
            <div className="text-xs space-y-1 max-h-32 overflow-y-auto">
              {activeDrones.map((drone) => (
                <div key={drone.id} className="font-mono text-gray-300">
                  <span className="font-bold">{drone.id}</span>
                  {drone.health !== undefined && (
                    <span className="text-xs ml-2">Health: {(drone.health * 100).toFixed(0)}%</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default GridLegend
