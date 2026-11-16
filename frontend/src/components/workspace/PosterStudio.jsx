import { useState, useEffect } from 'react'
import {
  RefreshCw,
  Download,
  Loader2,
  AlertCircle,
  ImageIcon,
  Sparkles,
  ExternalLink,
  Palette,
} from 'lucide-react'
import { generatePoster } from '../../services/api'

const STYLE_PRESETS = [
  'Modern Minimalist',
  'Vibrant Cyberpunk',
  'Editorial Fashion',
  'Bold Cinematic',
  'Retro Vintage',
  'Dark High-Contrast',
]

export default function PosterStudio({ campaign, initialPoster, onPosterGenerated }) {
  const [poster, setPoster] = useState(initialPoster || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [styleOverride, setStyleOverride] = useState('')
  const [selectedPreset, setSelectedPreset] = useState('')

  useEffect(() => {
    if (initialPoster) {
      setPoster(initialPoster)
    }
  }, [initialPoster])

  async function handleGenerate() {
    if (!campaign) return
    setLoading(true)
    setError(null)

    // Combine preset and custom notes
    const combinedStyle = [selectedPreset, styleOverride.trim()]
      .filter(Boolean)
      .join(' - ')

    try {
      const result = await generatePoster({
        campaign,
        style_override: combinedStyle || null,
      })
      setPoster(result)
      if (onPosterGenerated) {
        onPosterGenerated(result)
      }
    } catch (err) {
      setError(err.message || 'Image generation failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownload() {
    if (!poster?.image_url) return
    try {
      const response = await fetch(poster.image_url)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const safeName = (campaign?.campaign_name || 'poster').replace(/[^a-zA-Z0-9_-]/g, '_')
      a.download = `${safeName}_poster.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      window.open(poster.image_url, '_blank')
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="section-title">Poster Studio</h2>
            <span className="badge-purple text-xs">AI Visuals</span>
          </div>
          <p className="section-subtitle mt-0.5">
            Generates coordinated promotional artwork matching your campaign's brand identity.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {poster && (
            <>
              <a
                href={poster.image_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-xs px-3 py-2 flex items-center gap-1.5"
                title="Open full-resolution image"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View Full
              </a>
              <button
                id="download-poster-btn"
                onClick={handleDownload}
                className="btn-secondary text-xs px-3 py-2 flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                Download
              </button>
            </>
          )}

          <button
            id="generate-poster-btn"
            onClick={handleGenerate}
            disabled={loading || !campaign}
            className="btn-primary text-xs px-4 py-2 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            {poster ? 'Regenerate' : 'Generate Poster'}
          </button>
        </div>
      </div>

      {/* Brand Context Indicator */}
      {campaign && (
        <div className="bg-surface-elevated/70 border border-surface-border rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <span className="text-gray-400 font-medium flex items-center gap-1.5">
              <Palette className="w-3.5 h-3.5 text-brand-purple-light" />
              Palette:
            </span>
            <div className="flex items-center gap-1.5">
              {[
                { label: 'Primary', val: campaign.brand_colors?.primary },
                { label: 'Secondary', val: campaign.brand_colors?.secondary },
                { label: 'Accent', val: campaign.brand_colors?.accent },
                { label: 'Background', val: campaign.brand_colors?.background },
              ]
                .filter(c => Boolean(c.val))
                .map((c, i) => (
                  <span
                    key={i}
                    title={`${c.label}: ${c.val}`}
                    className="w-4 h-4 rounded-full border border-white/20 shadow-sm"
                    style={{ backgroundColor: c.val }}
                  />
                ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-gray-500">Style:</span>
            <span className="px-2 py-0.5 rounded bg-surface-card border border-surface-border text-gray-300">
              {campaign.visual_style || 'Modern'}
            </span>
            <span className="text-gray-500 ml-2">Tone:</span>
            <span className="px-2 py-0.5 rounded bg-surface-card border border-surface-border text-brand-cyan">
              {campaign.tone || campaign.writing_tone || 'Bold'}
            </span>
          </div>
        </div>
      )}

      {/* Style Presets and Override Controls */}
      <div className="card p-4 space-y-3">
        <div>
          <label className="label text-xs mb-1.5 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-brand-cyan" />
            Poster Style Presets (Optional)
          </label>
          <div className="flex flex-wrap gap-2">
            {STYLE_PRESETS.map(preset => {
              const active = selectedPreset === preset
              return (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setSelectedPreset(active ? '' : preset)}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                    active
                      ? 'bg-gradient-to-r from-brand-purple to-brand-cyan text-white border-transparent shadow-brand-sm'
                      : 'bg-surface-elevated border-surface-border text-gray-300 hover:text-white hover:border-surface-border-light'
                  }`}
                >
                  {preset}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <label className="label text-xs">Custom Style Notes (Optional)</label>
          <input
            type="text"
            className="input text-sm"
            placeholder="e.g. Add subtle neon glow, high contrast dramatic shadows, award-winning composition..."
            value={styleOverride}
            onChange={e => setStyleOverride(e.target.value)}
          />
        </div>
      </div>

      {/* Poster Display Area */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="h-96 flex flex-col items-center justify-center gap-4 p-8">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-2 border-brand-purple/20 border-t-brand-purple animate-spin" />
              <Loader2 className="w-6 h-6 text-brand-purple-light absolute inset-0 m-auto animate-pulse" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-white font-medium">Generating your promotional poster...</p>
              <p className="text-gray-400 text-sm">
                Translating brand direction into high-resolution visuals.
              </p>
              <p className="text-gray-500 text-xs">This typically takes 10 to 25 seconds.</p>
            </div>
          </div>
        ) : error ? (
          <div className="h-72 flex flex-col items-center justify-center gap-4 p-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-red-900/20 border border-red-700/30 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-400" />
            </div>
            <div className="max-w-md">
              <p className="text-white font-medium">Image Generation Notice</p>
              <p className="text-red-400 text-sm mt-1">{error}</p>
            </div>
            <button
              onClick={handleGenerate}
              className="btn-primary text-xs px-4 py-2 flex items-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry Generation
            </button>
          </div>
        ) : poster?.image_url ? (
          <div>
            <div className="relative group bg-black/40 flex items-center justify-center p-2">
              <img
                id="generated-poster-img"
                src={poster.image_url}
                alt={`${campaign?.campaign_name || 'Campaign'} promotional poster`}
                className="w-full max-h-[640px] object-contain rounded-xl transition-transform duration-300"
              />
            </div>
            <div className="p-4 border-t border-surface-border bg-surface-elevated/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <p className="text-gray-400 line-clamp-1 max-w-xl">
                <span className="text-gray-500 font-medium">Prompt:</span>{' '}
                {poster.prompt_used || 'Standard campaign prompt'}
              </p>
              <span className="text-brand-cyan font-mono text-[11px] self-end sm:self-auto">
                {poster.storage_path || 'Ready'}
              </span>
            </div>
          </div>
        ) : (
          <div className="h-80 flex flex-col items-center justify-center gap-4 p-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
              <ImageIcon className="w-8 h-8 text-gray-500" />
            </div>
            <div className="max-w-sm">
              <p className="text-white font-medium">No poster generated yet</p>
              <p className="text-gray-400 text-sm mt-1">
                Click <span className="text-brand-purple-light font-medium">Generate Poster</span> to create a promotional poster aligned with your brand identity.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
