/**
 * GridLegend Component
 * 
 * Reference chart for:
 * - NATO unit symbology
 * - Non-unit map markers
 */

import React from 'react'
import { getEntityDisplayLabel, getEntityTypeLabel } from '../lib/displayNames'
import { MAP_MARKER_LEGEND_ITEMS, NATO_UNIT_LEGEND_ITEMS } from '../lib/natoSymbols'

function GridLegend({ activeDrones = [], mapMode = 'nato', embedded = false }) {
  const renderUnitPreview = (symbol) => {
    if (mapMode === 'atak') {
      return (
        <div
          className="flex h-10 w-10 items-center justify-center rounded-full border"
          style={{
            borderColor: `${symbol.badgeColor}AA`,
            backgroundColor: `${symbol.badgeColor}33`
          }}
        >
          <img
            src={symbol.atakIconUrl || symbol.url}
            alt=""
            className="max-h-7 max-w-5 object-contain"
            draggable="false"
          />
        </div>
      )
    }

    return (
      <div className="flex h-10 w-10 items-center justify-center rounded border border-gray-600 bg-gray-800/70">
        <img
          src={symbol.url}
          alt=""
          className="max-h-9 max-w-7 object-contain"
          draggable="false"
        />
      </div>
    )
  }

  return (
    <div className={embedded ? 'w-full space-y-4' : 'w-full space-y-4 p-4 bg-gray-700 border border-gray-600 rounded'}>
      {/* Unit Symbology */}
      <div>
        <div className="mb-2">
          <h3 className="font-bold text-sm text-gray-100">Unit Symbology</h3>
          <p className="text-[11px] text-gray-400">
            {mapMode === 'atak'
              ? 'ATAK-inspired badges with inner symbols and labels'
              : 'Full NATO symbols with semi-transparent label chips'}
          </p>
        </div>
        <div className="space-y-1.5">
          {NATO_UNIT_LEGEND_ITEMS.map((symbol) => (
            <div key={symbol.key} className="flex items-center gap-3 text-xs">
              {renderUnitPreview(symbol)}
              <span className="font-mono flex-1 text-gray-100">{symbol.label}</span>
              <span className="text-gray-400 text-xs">{symbol.range || symbol.legendNote}</span>
            </div>
          ))}
        </div>
      </div>

      <hr className="border-gray-600" />

      {/* Entity Types */}
      <div>
        <h3 className="font-bold text-sm mb-2 text-gray-100">Non-Unit Map Markers</h3>
        <div className="space-y-1.5">
          {MAP_MARKER_LEGEND_ITEMS.map((entity) => (
            <div key={entity.key} className="flex items-center gap-3 text-xs">
              <div className="flex h-10 w-10 items-center justify-center rounded border border-gray-600 bg-gray-800/70">
                <img
                  src={mapMode === 'atak' && entity.atakBadge !== false ? (entity.atakIconUrl || entity.url) : entity.url}
                  alt=""
                  className="max-h-8 max-w-8 object-contain"
                  draggable="false"
                />
              </div>
              <span className="font-mono flex-1 text-gray-100">{entity.label}</span>
              <span className="text-gray-400 text-xs">{entity.legendNote}</span>
            </div>
          ))}
          {mapMode === 'atak' && (
            <div className="rounded border border-gray-600 bg-gray-800/40 px-3 py-2 text-[11px] text-gray-400">
              Buildings and fixed structures stay as direct SVG map objects in ATAK mode instead of circular badges.
            </div>
          )}
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
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 border border-sky-300 rounded text-sky-300">◎</span>
            <span className="text-gray-300">Recon visibility is ray-cast and blocked by building footprints</span>
          </div>
        </div>
      </div>

      {/* Active Drones Summary */}
      {activeDrones.length > 0 && (
        <>
          <hr className="border-gray-600" />
          <div>
            <h3 className="font-bold text-sm mb-2 text-gray-100">Active Friendly Units ({activeDrones.length})</h3>
            <div className="text-xs space-y-1 max-h-32 overflow-y-auto">
              {activeDrones.map((drone) => (
                <div key={drone.id} className="text-gray-300">
                  <span className="font-bold">{getEntityDisplayLabel(drone)}</span>
                  <span className="text-xs ml-2 text-gray-400">{getEntityTypeLabel(drone)}</span>
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
