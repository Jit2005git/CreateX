import { useState } from 'react'
import { RefreshCw, Download, Loader2, AlertCircle, ImageIcon } from 'lucide-react'
import { generatePoster } from '../../services/api'

export default function PosterStudio({ campaign, initialPoster }) {
  const [poster, setPoster] = useState(initialPoster || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [styleOverride, setStyleOverride] = useState('')

  async function handleGenerate() {
    if (!campaign) return
    setLoading(true)
    setError(null)
    try {
      const result = await generatePoster({ campaign, style_override: styleOverride || null })
      setPoster(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDownload() {
    if (!poster?.image_url) return
    const response = await fetch(poster.image_url)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${campaign?.campaign_name || 'poster'}.png`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">Poster Studio</h2>
          <p className="section-subtitle">AI-generated promotional poster</p>
        </div>
        <div className="flex items-center gap-2">
          {poster && (
            <button id="download-poster-btn" onClick={handleDownload} className="btn-secondary text-xs px-4 py-2">
              <Download className="w-3.5 h-3.5" />
              Download
            </button>
          )}
          <button
            id="generate-poster-btn"
            onClick={handleGenerate}
            disabled={loading || !campaign}
            className="btn-primary text-xs px-4 py-2"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            {poster ? 'Regenerate' : 'Generate Poster'}
          </button>
        </div>
      </div>

      {/* Style override */}
      <div>
        <label className="label text-xs">Style Notes (optional)</label>
        <input
          type="text"
          className="input text-sm"
          placeholder="e.g. Add more contrast, make it more dramatic..."
          value={styleOverride}
          onChange={e => setStyleOverride(e.target.value)}
        />
      </div>

      {/* Poster display */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="h-96 flex flex-col items-center justify-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-2 border-brand-purple/20 border-t-brand-purple animate-spin" />
              <Loader2 className="w-6 h-6 text-brand-purple-light absolute inset-0 m-auto animate-pulse" />
            </div>
            <div className="text-center">
              <p className="text-white font-medium">Generating your poster...</p>
              <p className="text-gray-500 text-sm mt-1">This may take 15-30 seconds</p>
            </div>
          </div>
        ) : error ? (
          <div className="h-64 flex flex-col items-center justify-center gap-4 p-6">
            <div className="w-12 h-12 rounded-xl bg-red-900/20 border border-red-700/30 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-400" />
            </div>
            <div className="text-center">
              <p className="text-white font-medium">Generation failed</p>
              <p className="text-red-400 text-sm mt-1 max-w-sm">{error}</p>
            </div>
            <button onClick={handleGenerate} className="btn-primary text-xs px-4 py-2">
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        ) : poster ? (
          <div>
            <img
              id="generated-poster-img"
              src={poster.image_url}
              alt={`${campaign?.campaign_name} promotional poster`}
              className="w-full object-cover rounded-2xl"
            />
            <div className="p-4 border-t border-surface-border">
              <p className="text-xs text-gray-500">
                <span className="text-gray-400 font-medium">Prompt used:</span> {poster.prompt_used?.slice(0, 120)}...
              </p>
            </div>
          </div>
        ) : (
          <div className="h-80 flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
              <ImageIcon className="w-8 h-8 text-gray-600" />
            </div>
            <div className="text-center">
              <p className="text-white font-medium">No poster generated yet</p>
              <p className="text-gray-500 text-sm mt-1">Click "Generate Poster" to create your AI promotional image</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
