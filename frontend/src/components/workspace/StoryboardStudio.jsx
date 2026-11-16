import { useState, useEffect } from 'react'
import {
  RefreshCw,
  Loader2,
  AlertCircle,
  Film,
  ChevronLeft,
  ChevronRight,
  Camera,
  Mic,
  Type,
  Shuffle,
  Edit3,
  Check,
  Copy,
  Clock,
  Sparkles,
} from 'lucide-react'
import { generateStoryboard } from '../../services/api'

const PLATFORMS = ['instagram', 'youtube', 'tiktok', 'general']

export default function StoryboardStudio({ campaign, initialStoryboard, onStoryboardGenerated }) {
  const [storyboard, setStoryboard] = useState(initialStoryboard || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeScene, setActiveScene] = useState(0)
  const [editingScene, setEditingScene] = useState(false)
  const [copiedScene, setCopiedScene] = useState(false)
  const [config, setConfig] = useState({
    video_duration: 30,
    num_scenes: 5,
    platform: 'instagram',
  })

  useEffect(() => {
    if (initialStoryboard) {
      setStoryboard(initialStoryboard)
    }
  }, [initialStoryboard])

  async function handleGenerate() {
    if (!campaign) return
    setLoading(true)
    setError(null)
    try {
      const result = await generateStoryboard({ campaign, ...config })
      const sb = result.storyboard
      setStoryboard(sb)
      setActiveScene(0)
      if (onStoryboardGenerated) {
        onStoryboardGenerated(sb)
      }
    } catch (err) {
      setError(err.message || 'Storyboard generation failed.')
    } finally {
      setLoading(false)
    }
  }

  const scenes = storyboard?.scenes || []
  const scene = scenes[activeScene]

  function updateCurrentScene(field, value) {
    if (!storyboard || !scene) return
    const updatedScenes = [...scenes]
    updatedScenes[activeScene] = {
      ...scene,
      [field]: value,
    }
    const updatedStoryboard = {
      ...storyboard,
      scenes: updatedScenes,
    }
    setStoryboard(updatedStoryboard)
    if (onStoryboardGenerated) {
      onStoryboardGenerated(updatedStoryboard)
    }
  }

  async function copySceneDetails() {
    if (!scene) return
    const text = `Scene ${scene.scene_number} (${scene.duration_seconds}s)
Camera: ${scene.camera_direction}
Visual: ${scene.visual_description}
Narration: ${scene.narration}
On-Screen Text: ${scene.on_screen_text || 'None'}
Transition: ${scene.transition || 'None'}`
    await navigator.clipboard.writeText(text)
    setCopiedScene(true)
    setTimeout(() => setCopiedScene(false), 2000)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="section-title">Storyboard Studio</h2>
            <span className="badge-purple text-xs">Video Narrative</span>
          </div>
          <p className="section-subtitle mt-0.5">
            Scene-by-scene video script, camera choreography, and narration.
          </p>
        </div>

        <button
          id="generate-storyboard-btn"
          onClick={handleGenerate}
          disabled={loading || !campaign}
          className="btn-primary text-xs px-4 py-2 flex items-center gap-2 self-start sm:self-auto"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          {storyboard ? 'Regenerate Storyboard' : 'Generate Storyboard'}
        </button>
      </div>

      {/* Video Configuration Card */}
      <div className="card p-5 space-y-3">
        <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
          <Film className="w-3.5 h-3.5 text-brand-purple-light" />
          Video Specifications
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="label text-xs">Duration</label>
            <select
              className="select text-sm"
              value={config.video_duration}
              onChange={e => setConfig(c => ({ ...c, video_duration: +e.target.value }))}
            >
              {[15, 30, 45, 60, 90, 120].map(d => (
                <option key={d} value={d}>
                  {d} seconds
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label text-xs">Number of Scenes</label>
            <select
              className="select text-sm"
              value={config.num_scenes}
              onChange={e => setConfig(c => ({ ...c, num_scenes: +e.target.value }))}
            >
              {[3, 4, 5, 6, 7, 8, 10].map(n => (
                <option key={n} value={n}>
                  {n} scenes
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label text-xs">Format & Platform</label>
            <select
              className="select text-sm capitalize"
              value={config.platform}
              onChange={e => setConfig(c => ({ ...c, platform: e.target.value }))}
            >
              {PLATFORMS.map(p => (
                <option key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)} (
                  {p === 'instagram' ? 'Reels / 9:16' : p === 'youtube' ? '16:9 Landscape' : 'Adaptive'}
                  )
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="card h-80 flex flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="w-16 h-16 rounded-full border-2 border-brand-purple/20 border-t-brand-purple animate-spin" />
          <div className="space-y-1">
            <p className="text-white font-medium">Directing video narrative...</p>
            <p className="text-gray-400 text-sm">
              Scripting {config.num_scenes} synchronized scenes across {config.video_duration} seconds.
            </p>
          </div>
        </div>
      ) : error ? (
        <div className="card h-64 flex flex-col items-center justify-center gap-4 p-6 text-center">
          <div className="w-12 h-12 rounded-xl bg-red-900/20 border border-red-700/30 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-red-400" />
          </div>
          <div className="max-w-md">
            <p className="text-white font-medium">Generation Error</p>
            <p className="text-red-400 text-sm mt-1">{error}</p>
          </div>
          <button
            onClick={handleGenerate}
            className="btn-primary text-xs px-4 py-2 flex items-center gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Try Again
          </button>
        </div>
      ) : storyboard ? (
        <div className="space-y-5">
          {/* Storyboard Header / Video Title */}
          <div className="card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gradient-to-r from-surface-card to-surface-elevated/70">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-brand-purple/20 border border-brand-purple/30 flex items-center justify-center text-brand-purple-light shrink-0">
                <Film className="w-5 h-5" />
              </div>
              <div>
                <p className="font-bold text-white text-base sm:text-lg">
                  {storyboard.video_title}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  <span className="text-brand-cyan-light font-mono font-semibold">
                    {storyboard.total_duration}s total
                  </span>{' '}
                  · <span className="capitalize">{storyboard.platform}</span> ·{' '}
                  {scenes.length} scenes
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-auto">
              <button
                type="button"
                onClick={() => setEditingScene(!editingScene)}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
              >
                <Edit3 className="w-3.5 h-3.5 text-brand-cyan" />
                {editingScene ? 'Done Editing' : 'Edit Scene'}
              </button>
              <button
                type="button"
                onClick={copySceneDetails}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
                title="Copy current scene script"
              >
                {copiedScene ? (
                  <Check className="w-3.5 h-3.5 text-green-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                Copy Scene
              </button>
            </div>
          </div>

          {/* Scene Navigator Bar */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1.5">
            {scenes.map((s, i) => {
              const active = activeScene === i
              return (
                <button
                  key={i}
                  id={`scene-tab-${i + 1}`}
                  onClick={() => setActiveScene(i)}
                  className={`shrink-0 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-2 border ${
                    active
                      ? 'bg-gradient-to-r from-brand-purple to-brand-cyan text-white border-transparent shadow-brand-sm'
                      : 'bg-surface-card border-surface-border text-gray-400 hover:text-white hover:border-surface-border-light'
                  }`}
                >
                  <span>Scene {s.scene_number}</span>
                  <span
                    className={`text-[11px] px-1.5 py-0.5 rounded font-mono ${
                      active ? 'bg-white/20 text-white' : 'bg-surface-elevated text-gray-400'
                    }`}
                  >
                    {s.duration_seconds}s
                  </span>
                </button>
              )
            })}
          </div>

          {/* Active Scene Card */}
          {scene && (
            <div className="card p-6 space-y-5 animate-fade-in border border-surface-border">
              {/* Scene Info Subheader */}
              <div className="flex items-center justify-between pb-3 border-b border-surface-border flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="badge-purple font-mono text-xs">
                    Scene #{scene.scene_number}
                  </span>
                  <span className="badge-cyan font-mono text-xs flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {scene.duration_seconds} seconds
                  </span>
                  {scene.mood && (
                    <span className="badge-amber text-xs flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      Mood: {scene.mood}
                    </span>
                  )}
                </div>

                <span className="text-xs text-gray-500">
                  Scene {activeScene + 1} of {scenes.length}
                </span>
              </div>

              {/* Visual Description */}
              <div className="space-y-1.5">
                <label className="label text-xs">Visual Description</label>
                {editingScene ? (
                  <textarea
                    className="textarea text-sm h-24"
                    value={scene.visual_description || ''}
                    onChange={e => updateCurrentScene('visual_description', e.target.value)}
                  />
                ) : (
                  <p className="text-sm text-gray-200 leading-relaxed bg-surface-elevated/70 rounded-xl p-4 border border-surface-border">
                    {scene.visual_description}
                  </p>
                )}
              </div>

              {/* Camera Direction & Narration Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="label text-xs flex items-center gap-1.5">
                    <Camera className="w-3.5 h-3.5 text-brand-cyan-light" />
                    Camera Direction & Motion
                  </label>
                  {editingScene ? (
                    <textarea
                      className="textarea text-xs h-24"
                      value={scene.camera_direction || ''}
                      onChange={e => updateCurrentScene('camera_direction', e.target.value)}
                    />
                  ) : (
                    <p className="text-xs text-gray-300 leading-relaxed bg-surface-elevated/60 rounded-xl p-3.5 border border-surface-border min-h-[5rem]">
                      {scene.camera_direction}
                    </p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="label text-xs flex items-center gap-1.5">
                    <Mic className="w-3.5 h-3.5 text-brand-purple-light" />
                    Voiceover & Dialogue
                  </label>
                  {editingScene ? (
                    <textarea
                      className="textarea text-xs h-24"
                      value={scene.narration || ''}
                      onChange={e => updateCurrentScene('narration', e.target.value)}
                    />
                  ) : (
                    <p className="text-xs text-gray-300 leading-relaxed bg-surface-elevated/60 rounded-xl p-3.5 border border-surface-border min-h-[5rem]">
                      {scene.narration}
                    </p>
                  )}
                </div>
              </div>

              {/* On-Screen Text Overlay */}
              <div className="space-y-1.5">
                <label className="label text-xs flex items-center gap-1.5">
                  <Type className="w-3.5 h-3.5 text-brand-amber" />
                  On-Screen Typography & Graphic Overlay
                </label>
                {editingScene ? (
                  <input
                    type="text"
                    className="input text-xs"
                    value={scene.on_screen_text || ''}
                    onChange={e => updateCurrentScene('on_screen_text', e.target.value)}
                  />
                ) : scene.on_screen_text ? (
                  <p className="text-xs font-semibold text-brand-amber bg-brand-amber/10 rounded-xl p-3 border border-brand-amber/20">
                    "{scene.on_screen_text}"
                  </p>
                ) : (
                  <p className="text-xs text-gray-500 italic p-2">None</p>
                )}
              </div>

              {/* Transition */}
              <div className="flex items-center gap-2 text-xs text-gray-400 pt-2 border-t border-surface-border">
                <Shuffle className="w-3.5 h-3.5 text-brand-purple-light" />
                <span className="text-gray-500 font-medium">Transition:</span>
                {editingScene ? (
                  <input
                    type="text"
                    className="input text-xs py-1 px-2 h-7 w-64"
                    value={scene.transition || ''}
                    onChange={e => updateCurrentScene('transition', e.target.value)}
                  />
                ) : (
                  <span className="text-gray-300">{scene.transition || 'Cut'}</span>
                )}
              </div>

              {/* Scene Navigation Footer */}
              <div className="flex items-center justify-between pt-3 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setActiveScene(i => Math.max(0, i - 1))}
                  disabled={activeScene === 0}
                  className="btn-ghost text-xs disabled:opacity-30 flex items-center gap-1"
                >
                  <ChevronLeft className="w-4 h-4" /> Previous Scene
                </button>

                <div className="flex gap-1.5">
                  {scenes.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveScene(idx)}
                      className={`w-2.5 h-2.5 rounded-full transition-all ${
                        activeScene === idx
                          ? 'bg-brand-cyan w-5'
                          : 'bg-surface-border hover:bg-gray-500'
                      }`}
                      title={`Jump to Scene ${idx + 1}`}
                    />
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => setActiveScene(i => Math.min(scenes.length - 1, i + 1))}
                  disabled={activeScene === scenes.length - 1}
                  className="btn-ghost text-xs disabled:opacity-30 flex items-center gap-1"
                >
                  Next Scene <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card h-72 flex flex-col items-center justify-center gap-4 p-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
            <Film className="w-8 h-8 text-gray-500" />
          </div>
          <div className="max-w-sm">
            <p className="text-white font-medium">No storyboard generated yet</p>
            <p className="text-gray-400 text-sm mt-1">
              Select your target platform and duration above, then click{' '}
              <span className="text-brand-purple-light font-medium">Generate Storyboard</span>.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
