const FRIENDLY_TYPE_LABELS = {
  soldier: 'Soldier Operator',
  compute: 'Compute Drone',
  recon: 'Recon Drone',
  attack: 'Attack Drone'
}

export const formatLabelText = (rawValue) => {
  if (!rawValue) return ''
  return String(rawValue)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export const sanitizeUnitIdentifiers = (text) => {
  if (!text) return ''

  return String(text)
    .replace(/\bsoldier-(\d+)\b/gi, 'Soldier $1')
    .replace(/\bcompute-(\d+)\b/gi, 'Compute Drone $1')
    .replace(/\brecon-(\d+)\b/gi, 'Recon Drone $1')
    .replace(/\battack-(\d+)\b/gi, 'Attack Drone $1')
}

export const getEntityTypeLabel = (entity) => {
  if (!entity) return 'Unit'

  const rawType = entity.droneType || entity.type || entity.subtype || entity.poiType || entity.enemyType || entity.structureType
  const normalizedType = String(rawType || '').toLowerCase()

  if (entity.type === 'drone' || FRIENDLY_TYPE_LABELS[normalizedType]) {
    return FRIENDLY_TYPE_LABELS[normalizedType] || 'Friendly Unit'
  }

  if (entity.type === 'enemy') {
    return `Hostile ${formatLabelText(entity.enemyType || entity.subtype || 'Unit')}`
  }

  if (entity.type === 'structure') {
    return formatLabelText(entity.structureType || entity.subtype || 'Structure')
  }

  if (entity.type === 'poi') {
    return formatLabelText(entity.poiType || entity.subtype || 'Point of Interest')
  }

  return formatLabelText(rawType || 'Unit')
}

export const getEntityDisplayLabel = (entity) => {
  if (!entity) return 'Unit'

  const label = typeof entity.label === 'string' ? entity.label.trim() : ''
  if (label) {
    return sanitizeUnitIdentifiers(label)
  }

  if (entity.type === 'drone' || FRIENDLY_TYPE_LABELS[String(entity.type || '').toLowerCase()]) {
    const friendlyLabel = getEntityTypeLabel(entity)
    const match = /-(\d+)$/.exec(String(entity.id || ''))
    return match ? `${friendlyLabel} ${match[1]}` : friendlyLabel
  }

  if (entity.id) {
    return sanitizeUnitIdentifiers(entity.id)
  }

  return getEntityTypeLabel(entity)
}
