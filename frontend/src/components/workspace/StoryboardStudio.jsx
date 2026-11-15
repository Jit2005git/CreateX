import { useState } from 'react'
import { RefreshCw, Loader2, AlertCircle, Film, ChevronLeft, ChevronRight, Camera, Mic, Type, Shuffle } from 'lucide-react'
import { generateStoryboard } from '../../services/api'

const PLATFORMS = ['instagram', 'youtube', 'tiktok', 'general']

export default function StoryboardStudio({ campaign, initialStoryboard }) {
  const [storyboard, setStoryboard] = useState(initialStoryboard || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeScene, setActiveScene] = useState(0)
  const [config, setConfig] = useState({ video_duration: 30, num_scenes: 5, platform: 'instagram' })

  async function handleGenerate() {
    if (!campaign) return
    setLoading(true)
    setError(null)
    try {
      const result = await generateStoryboard({ campaign, ...config })
      setStoryboard(result.storyboard)
      setActiveScene(0)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const scenes = storyboard?.scenes || []
  const scene = scenes[activeScene]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="section-title">Storyboard Studio</h2>
          <p className="section-subtitle">Scene-by-scene video storyboard</p>
        </div>
        <button
          id="generate-storyboard-btn"
          onClick={handleGenerate}
          disabled={loading || !campaign}
          className="btn-primary text-xs px-4 py-2"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          {storyboard ? 'Regenerate' : 'Generate Storyboard'}
        </button>
      </div>

      {/* Config */}
      <div className="card p-5">
        <h3 className="text-sm font-medium text-gray-300 mb-4">Video Configuration</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="label text-xs">Duration (seconds)</label>
            <select className="select text-sm" value={config.video_duration} onChange={e => setConfig(c => ({ ...c, video_duration: +e.target.value }))}>
              {[15, 30, 45, 60, 90, 120].map(d => <option key={d} value={d}>{d}s</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs">Number of Scenes</label>
            <select className="select text-sm" value={config.num_scenes} onChange={e => setConfig(c => ({ ...c, num_scenes: +e.target.value }))}>
              {[3, 4, 5, 6, 7, 8, 10].map(n => <option key={n} value={n}>{n} scenes</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs">Platform</label>
            <select className="select text-sm" value={config.platform} onChange={e => setConfig(c => ({ ...c, platform: e.target.value }))}>
              {PLATFORMS.map(p => <option key={p} value={p} className="capitalize">{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="card h-64 flex flex-col items-center justify-center gap-4">
          <Loader2 className="w-8 h-8 text-brand-purple-light animate-spin" />
          <p className="text-white font-medium">Crafting your storyboard...</p>
          <p className="text-gray-500 text-sm">Building {config.num_scenes} scenes for {config.video_duration}s video</p>
        </div>
      ) : error ? (
        <div className="card h-48 flex flex-col items-center justify-center gap-4 p-6">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <p className="text-red-400 text-sm text-center">{error}</p>
          <button onClick={handleGenerate} className="btn-primary text-xs px-4 py-2"><RefreshCw className="w-3.5 h-3.5" /> Retry</button>
        </div>
      ) : storyboard ? (
        <div className="space-y-4">
          {/* Video title */}
          <div className="card p-4 flex items-center gap-3">
            <Film className="w-5 h-5 text-brand-purple-light" />
            <div>
              <p className="font-semibold text-white">{storyboard.video_title}</p>
              <p className="text-xs text-gray-500">{storyboard.total_duration}s · {storyboard.platform} · {scenes.length} scenes</p>
            </div>
          </div>

          {/* Scene navigator */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {scenes.map((s, i) => (
              <button
                key={i}
                id={`scene-tab-${i + 1}`}
                onClick={() => setActiveScene(i)}
                className={`shrink-0 px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 ${
                  activeScene === i
                    ? 'bg-brand-purple text-white shadow-brand-sm'
                    : 'bg-surface-card border border-surface-border text-gray-400 hover:text-white'
                }`}
              >
                Scene {s.scene_number}
                <span className="ml-1.5 text-gray-500">{s.duration_seconds}s</span>
              </button>
            ))}
          </div>

          {/* Active scene */}
          {scene && (
            <div className="card p-6 animate-fade-in space-y-5">
              <div className="flex items-center justify-between">
                <span className="badge-purple">Scene {scene.scene_number} · {scene.duration_seconds}s</span>
                {scene.mood && <span className="badge-amber">{scene.mood}</span>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="space-y-1">
                  <label className="label text-xs flex items-center gap-1.5"><Camera className="w-3.5 h-3.5 text-brand-cyan-light" /> Camera Direction</label>
                  <p className="text-sm text-gray-300 leading-relaxed bg-surface-elevated rounded-xl p-3">{scene.camera_direction}</p>
                </div>
                <div className="space-y-1">
                  <label className="label text-xs flex items-center gap-1.5"><Mic className="w-3.5 h-3.5 text-brand-purple-light" /> Narration</label>
                  <p className="text-sm text-gray-300 leading-relaxed bg-surface-elevated rounded-xl p-3">{scene.narration}</p>
                </div>
              </div>

              <div className="space-y-1">
                <label className="label text-xs">Visual Description</label>
                <p className="text-sm text-gray-300 leading-relaxed bg-surface-elevated rounded-xl p-4">{scene.visual_description}</p>
              </div>

              {scene.on_screen_text && (
                <div className="space-y-1">
                  <label className="label text-xs flex items-center gap-1.5"><Type className="w-3.5 h-3.5 text-brand-amber" /> On-Screen Text</label>
                  <p className="text-sm text-brand-amber font-medium bg-brand-amber/10 rounded-xl p-3 border border-brand-amber/20">{scene.on_screen_text}</p>
                </div>
              )}

              {scene.transition && (
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Shuffle className="w-3.5 h-3.5" />
                  Transition: <span className="text-gray-400">{scene.transition}</span>
                </div>
              )}

              {/* Scene prev/next */}
              <div className="flex items-center justify-between pt-2 border-t border-surface-border">
                <button onClick={() => setActiveScene(i => Math.max(0, i - 1))} disabled={activeScene === 0} className="btn-ghost text-xs disabled:opacity-30">
                  <ChevronLeft className="w-4 h-4" /> Previous
                </button>
                <span className="text-xs text-gray-500">{activeScene + 1} / {scenes.length}</span>
                <button onClick={() => setActiveScene(i => Math.min(scenes.length - 1, i + 1))} disabled={activeScene === scenes.length - 1} className="btn-ghost text-xs disabled:opacity-30">
                  Next <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card h-64 flex flex-col items-center justify-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
            <Film className="w-7 h-7 text-gray-600" />
          </div>
          <div className="text-center">
            <p className="text-white font-medium">No storyboard yet</p>
            <p className="text-gray-500 text-sm mt-1">Configure and generate your video storyboard above</p>
          </div>
        </div>
      )}
    </div>
  )
}
