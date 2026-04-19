import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const sourceRoot = process.env.JMS_XML_DIR || process.env.ESRI_JMS_XML_DIR || '/tmp/joint-military-symbology-xml'
const outputDir = path.join(projectRoot, 'public', 'symbology', 'generated')

const SYMBOL_MANIFEST = [
  {
    key: 'allied-soldier-operator',
    title: 'Friendly Infantry / Operator',
    layers: [
      'svg/Frames/0_310_0.svg',
      'svg/Appendices/Land/10121100_1.svg'
    ]
  },
  {
    key: 'allied-compute-drone',
    title: 'Friendly UAV / Airborne Command Relay',
    layers: [
      'svg/Frames/0_301_0.svg',
      'svg/Appendices/Air/01110300.svg',
      'svg/Appendices/Air/mod1/01111.svg'
    ]
  },
  {
    key: 'allied-recon-drone',
    title: 'Friendly UAV / Reconnaissance',
    layers: [
      'svg/Frames/0_301_0.svg',
      'svg/Appendices/Air/01110300.svg',
      'svg/Appendices/Air/mod1/01181.svg'
    ]
  },
  {
    key: 'allied-attack-drone',
    title: 'Friendly UAV / Attack',
    layers: [
      'svg/Frames/0_301_0.svg',
      'svg/Appendices/Air/01110300.svg',
      'svg/Appendices/Air/mod1/01011.svg'
    ]
  },
  {
    key: 'hostile-infantry',
    title: 'Hostile Infantry',
    layers: [
      'svg/Frames/0_610_0.svg',
      'svg/Appendices/Land/10121100_3.svg'
    ]
  },
  {
    key: 'hostile-tank',
    title: 'Hostile Tank',
    layers: [
      'svg/Frames/0_615_0.svg',
      'svg/Appendices/Land/15120200.svg'
    ]
  },
  {
    key: 'hostile-vehicle',
    title: 'Hostile Scout Vehicle',
    layers: [
      'svg/Frames/0_615_0.svg',
      'svg/Appendices/Land/15120110.svg'
    ]
  }
]

if (!existsSync(sourceRoot)) {
  console.error(`[nato-symbols] Source repo not found at ${sourceRoot}`)
  console.error('[nato-symbols] Clone or point JMS_XML_DIR to the Esri joint-military-symbology-xml repository.')
  process.exit(1)
}

mkdirSync(outputDir, { recursive: true })

const getSvgPayload = (absolutePath) => {
  const rawSvg = readFileSync(absolutePath, 'utf8')
  const viewBoxMatch = rawSvg.match(/viewBox="([^"]+)"/i)
  const widthMatch = rawSvg.match(/width="([^"]+)"/i)
  const heightMatch = rawSvg.match(/height="([^"]+)"/i)

  if (!viewBoxMatch) {
    throw new Error(`Missing viewBox in ${absolutePath}`)
  }

  const innerContent = rawSvg
    .replace(/^[\s\S]*?<svg\b[^>]*>/i, '')
    .replace(/<\/svg>[\s\S]*$/i, '')
    .trim()

  return {
    viewBox: viewBoxMatch[1],
    width: widthMatch?.[1] || '612px',
    height: heightMatch?.[1] || '792px',
    innerContent
  }
}

const buildSymbolSvg = ({ title, key, layers }) => {
  const resolvedLayers = layers.map((relativePath) => {
    const absolutePath = path.join(sourceRoot, relativePath)
    if (!existsSync(absolutePath)) {
      throw new Error(`Missing layer ${absolutePath}`)
    }
    return {
      source: relativePath,
      ...getSvgPayload(absolutePath)
    }
  })

  const { viewBox, width, height } = resolvedLayers[0]
  const layerMarkup = resolvedLayers
    .map((layer, index) => `  <g id="layer-${index + 1}" data-source="${layer.source}">\n${layer.innerContent}\n  </g>`)
    .join('\n')

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="${viewBox}" width="${width}" height="${height}" aria-labelledby="${key}-title" role="img">
  <title id="${key}-title">${title}</title>
${layerMarkup}
</svg>
`
}

for (const symbol of SYMBOL_MANIFEST) {
  const filePath = path.join(outputDir, `${symbol.key}.svg`)
  writeFileSync(filePath, buildSymbolSvg(symbol), 'utf8')
  console.log(`[nato-symbols] wrote ${path.relative(projectRoot, filePath)}`)
}

const manifestPath = path.join(outputDir, 'manifest.json')
writeFileSync(
  manifestPath,
  JSON.stringify(
    {
      sourceRoot,
      generatedAt: new Date().toISOString(),
      symbols: SYMBOL_MANIFEST.map(({ key, title, layers }) => ({ key, title, layers }))
    },
    null,
    2
  ) + '\n',
  'utf8'
)
console.log(`[nato-symbols] wrote ${path.relative(projectRoot, manifestPath)}`)
