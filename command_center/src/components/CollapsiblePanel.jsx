import React from 'react'

function CollapsiblePanel({
  title,
  subtitle = null,
  collapsed = false,
  onToggle,
  children,
  className = '',
  bodyClassName = 'p-4',
  headerContent = null
}) {
  return (
    <div className={`rounded border ${className}`.trim()}>
      <div className="flex items-start justify-between gap-3 border-b border-gray-700 px-4 py-3">
        <div className="min-w-0">
          <h3 className="text-sm font-bold uppercase tracking-[0.18em] text-gray-100">{title}</h3>
          {subtitle && (
            <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {headerContent}
          <button
            type="button"
            onClick={onToggle}
            className="rounded border border-gray-600 bg-gray-900/60 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-gray-200 transition hover:border-gray-500 hover:bg-gray-800"
          >
            {collapsed ? 'Expand' : 'Collapse'}
          </button>
        </div>
      </div>
      {!collapsed && (
        <div className={bodyClassName}>
          {children}
        </div>
      )}
    </div>
  )
}

export default CollapsiblePanel
