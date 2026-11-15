import { Copy, Check } from 'lucide-react'
import { useState } from 'react'

function ColorSwatch({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className="color-swatch"
        style={{ backgroundColor: color }}
        title={color}
      />
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-xs font-mono text-gray-500">{color}</p>
      </div>
    </div>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-surface-elevated transition-all duration-200" title="Copy">
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export default function CampaignOverview({ campaign }) {
  if (!campaign) return null

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="card p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-brand-purple/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-3xl font-bold text-white">{campaign.campaign_name}</h2>
              <p className="text-brand-cyan-light text-lg font-medium mt-1 italic">"{campaign.tagline}"</p>
            </div>
            <CopyButton text={`${campaign.campaign_name}\n${campaign.tagline}`} />
          </div>
          <p className="text-gray-400 mt-4 leading-relaxed">{campaign.description}</p>
          <div className="flex items-center gap-2 mt-4">
            <span className="badge-purple">🎯 {campaign.target_audience}</span>
          </div>
        </div>
      </div>

      {/* Brand Colors */}
      <div className="card p-6">
        <h3 className="font-semibold text-white mb-4">Brand Colors</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <ColorSwatch color={campaign.brand_colors?.primary}    label="Primary" />
          <ColorSwatch color={campaign.brand_colors?.secondary}  label="Secondary" />
          <ColorSwatch color={campaign.brand_colors?.accent}     label="Accent" />
          <ColorSwatch color={campaign.brand_colors?.background} label="Background" />
        </div>
      </div>

      {/* Creative Concepts */}
      {campaign.creative_concepts?.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold text-white mb-4">Creative Concepts</h3>
          <div className="space-y-3">
            {campaign.creative_concepts.map((concept, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-brand-purple/30 text-brand-purple-light text-xs flex items-center justify-center shrink-0 font-bold mt-0.5">
                  {i + 1}
                </span>
                <p className="text-gray-300 text-sm leading-relaxed">{concept}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Visual Direction */}
      {campaign.visual_direction && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-white">Visual Direction</h3>
            <CopyButton text={campaign.visual_direction} />
          </div>
          <p className="text-gray-400 text-sm leading-relaxed">{campaign.visual_direction}</p>
        </div>
      )}

      {/* Key Messages */}
      {campaign.key_messages?.length > 0 && (
        <div className="card p-6">
          <h3 className="font-semibold text-white mb-4">Key Messages</h3>
          <div className="flex flex-wrap gap-2">
            {campaign.key_messages.map((msg, i) => (
              <span key={i} className="badge-cyan text-xs">{msg}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
