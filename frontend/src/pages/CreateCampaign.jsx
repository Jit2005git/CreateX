import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles, Lightbulb, Users, Mic, Monitor, Palette,
  ArrowRight, ArrowLeft, Loader2, AlertCircle, CheckCircle2
} from 'lucide-react'
import { generateCampaign, saveProject } from '../services/api'
import { getSessionId } from '../services/session'

const GENERATION_STAGES = [
  { id: 'tone', label: 'Analyzing brand tone...', desc: 'Extracting key themes and emotional positioning' },
  { id: 'angles', label: 'Structuring creative angles...', desc: 'Crafting multi-platform hooks and visual concepts' },
  { id: 'strategy', label: 'Finalizing strategy...', desc: 'Synthesizing complete campaign package' },
]

const INDUSTRIES = [
  'Technology', 'Fashion & Apparel', 'Food & Beverage', 'Health & Wellness',
  'Education', 'Finance', 'Entertainment', 'Travel & Tourism',
  'Real Estate', 'Sports & Fitness', 'Beauty & Cosmetics', 'Automotive',
  'Non-Profit', 'Retail', 'Other'
]

const TONES = [
  { value: 'bold', label: 'Bold & Energetic', emoji: '⚡' },
  { value: 'playful', label: 'Playful & Fun', emoji: '🎉' },
  { value: 'professional', label: 'Professional & Trustworthy', emoji: '💼' },
  { value: 'inspirational', label: 'Inspirational & Uplifting', emoji: '🌟' },
  { value: 'minimalist', label: 'Clean & Minimalist', emoji: '◻️' },
  { value: 'luxurious', label: 'Luxurious & Premium', emoji: '✨' },
]

const PLATFORMS = [
  { value: 'instagram', label: 'Instagram', icon: '📸' },
  { value: 'youtube', label: 'YouTube', icon: '▶️' },
  { value: 'tiktok', label: 'TikTok', icon: '🎵' },
  { value: 'twitter', label: 'X / Twitter', icon: '𝕏' },
  { value: 'linkedin', label: 'LinkedIn', icon: '💼' },
  { value: 'facebook', label: 'Facebook', icon: '👥' },
]

const VISUAL_STYLES = [
  { value: 'modern', label: 'Modern & Bold' },
  { value: 'cinematic', label: 'Cinematic' },
  { value: 'retro', label: 'Retro / Vintage' },
  { value: 'minimalist', label: 'Minimalist' },
  { value: 'vibrant', label: 'Vibrant & Colorful' },
  { value: 'dark', label: 'Dark & Moody' },
]

const STEPS = ['Idea', 'Details', 'Style', 'Review']

export default function CreateCampaign() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [generationStage, setGenerationStage] = useState(0)
  const stageIntervalRef = useRef(null)

  useEffect(() => {
    return () => {
      if (stageIntervalRef.current) {
        clearInterval(stageIntervalRef.current)
      }
    }
  }, [])

  const [form, setForm] = useState({
    idea: '',
    industry: '',
    target_audience: '',
    tone: 'bold',
    platforms: ['instagram'],
    visual_style: 'modern',
  })

  function update(key, val) {
    setForm(prev => ({ ...prev, [key]: val }))
  }

  function togglePlatform(val) {
    setForm(prev => ({
      ...prev,
      platforms: prev.platforms.includes(val)
        ? prev.platforms.filter(p => p !== val)
        : [...prev.platforms, val],
    }))
  }

  function canProceed() {
    if (step === 0) return form.idea.trim().length >= 10
    if (step === 1) return form.industry && form.target_audience.trim().length >= 3
    if (step === 2) return form.platforms.length > 0
    return true
  }

  async function handleGenerate() {
    setLoading(true)
    setError(null)
    setGenerationStage(0)

    // Illustrative progress feedback across 3 stages
    stageIntervalRef.current = setInterval(() => {
      setGenerationStage((prev) => (prev < GENERATION_STAGES.length - 1 ? prev + 1 : prev))
    }, 1500)

    try {
      const result = await generateCampaign(form)
      const campaign = result.campaign

      // Auto-save to Supabase (non-blocking on failure)
      let projectId = 'local'
      try {
        const saved = await saveProject({
          session_id: getSessionId(),
          title: campaign.campaign_name,
          original_idea: form.idea,
          industry: form.industry,
          target_audience: form.target_audience,
          tone: form.tone,
          platforms: form.platforms,
          visual_style: form.visual_style,
          campaign_data: campaign,
        })
        projectId = saved.project_id
      } catch {
        // Supabase not configured — store in sessionStorage and use local ID
        sessionStorage.setItem('createx_campaign_local', JSON.stringify(campaign))
      }

      // Store campaign context for workspace
      sessionStorage.setItem(`campaign_${projectId}`, JSON.stringify(campaign))
      navigate(`/workspace/${projectId}`)
    } catch (err) {
      setError(err.message)
    } finally {
      if (stageIntervalRef.current) {
        clearInterval(stageIntervalRef.current)
      }
      setLoading(false)
      setGenerationStage(0)
    }
  }

  const stepContent = [
    // Step 0: Idea
    <div key="idea" className="animate-slide-up space-y-6">
      <div>
        <label className="label flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-brand-amber" />
          Your Creative Idea
        </label>
        <textarea
          id="idea-input"
          className="textarea h-40 text-base"
          placeholder="Describe your campaign idea in detail... e.g. 'A sustainable sneaker brand targeting Gen Z, emphasizing recycled materials and urban street culture'"
          value={form.idea}
          onChange={e => update('idea', e.target.value)}
          maxLength={2000}
        />
        <p className="text-xs text-gray-600 mt-2 text-right">{form.idea.length} / 2000</p>
      </div>
      <div className="card p-4 border-brand-purple/20 bg-brand-purple/5">
        <p className="text-xs text-gray-400">
          <span className="text-brand-purple-light font-medium">💡 Tip:</span> Be specific about your product, audience, and goals. The more detail you provide, the more tailored your creative assets will be.
        </p>
      </div>
    </div>,

    // Step 1: Details
    <div key="details" className="animate-slide-up space-y-6">
      <div>
        <label className="label flex items-center gap-2">
          <Monitor className="w-4 h-4 text-brand-cyan-light" />
          Industry / Sector
        </label>
        <select
          id="industry-select"
          className="select"
          value={form.industry}
          onChange={e => update('industry', e.target.value)}
        >
          <option value="">Select an industry...</option>
          {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
        </select>
      </div>
      <div>
        <label className="label flex items-center gap-2">
          <Users className="w-4 h-4 text-brand-cyan-light" />
          Target Audience
        </label>
        <input
          id="audience-input"
          type="text"
          className="input"
          placeholder="e.g. Gen Z urban consumers aged 18-24, interested in sustainability"
          value={form.target_audience}
          onChange={e => update('target_audience', e.target.value)}
        />
      </div>
    </div>,

    // Step 2: Style
    <div key="style" className="animate-slide-up space-y-6">
      <div>
        <label className="label flex items-center gap-2">
          <Mic className="w-4 h-4 text-brand-purple-light" />
          Campaign Tone
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {TONES.map(({ value, label, emoji }) => (
            <button
              key={value}
              id={`tone-${value}`}
              onClick={() => update('tone', value)}
              className={`p-3 rounded-xl border text-left transition-all duration-200 ${
                form.tone === value
                  ? 'border-brand-purple bg-brand-purple/20 text-white'
                  : 'border-surface-border bg-surface-elevated text-gray-400 hover:border-surface-border-light hover:text-white'
              }`}
            >
              <span className="text-lg">{emoji}</span>
              <p className="text-xs font-medium mt-1">{label}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="label flex items-center gap-2">
          <Palette className="w-4 h-4 text-brand-purple-light" />
          Visual Style
        </label>
        <div className="grid grid-cols-3 gap-3">
          {VISUAL_STYLES.map(({ value, label }) => (
            <button
              key={value}
              id={`style-${value}`}
              onClick={() => update('visual_style', value)}
              className={`p-3 rounded-xl border text-sm font-medium transition-all duration-200 ${
                form.visual_style === value
                  ? 'border-brand-cyan bg-brand-cyan/20 text-brand-cyan-light'
                  : 'border-surface-border bg-surface-elevated text-gray-400 hover:text-white hover:border-surface-border-light'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="label flex items-center gap-2">
          <Monitor className="w-4 h-4 text-brand-purple-light" />
          Target Platforms
        </label>
        <div className="grid grid-cols-3 gap-3">
          {PLATFORMS.map(({ value, label, icon }) => (
            <button
              key={value}
              id={`platform-${value}`}
              onClick={() => togglePlatform(value)}
              className={`p-3 rounded-xl border text-left transition-all duration-200 ${
                form.platforms.includes(value)
                  ? 'border-brand-purple bg-brand-purple/20 text-white'
                  : 'border-surface-border bg-surface-elevated text-gray-400 hover:border-surface-border-light hover:text-white'
              }`}
            >
              <span>{icon}</span>
              <p className="text-xs font-medium mt-1">{label}</p>
            </button>
          ))}
        </div>
      </div>
    </div>,

    // Step 3: Review
    <div key="review" className="animate-slide-up space-y-4">
      <div className="card p-6 space-y-4">
        {[
          { label: 'Creative Idea', value: form.idea },
          { label: 'Industry', value: form.industry },
          { label: 'Target Audience', value: form.target_audience },
          { label: 'Campaign Tone', value: TONES.find(t => t.value === form.tone)?.label },
          { label: 'Visual Style', value: VISUAL_STYLES.find(s => s.value === form.visual_style)?.label },
          { label: 'Platforms', value: form.platforms.join(', ') },
        ].map(({ label, value }) => (
          <div key={label} className="flex gap-4">
            <span className="text-xs text-gray-500 w-32 shrink-0 pt-0.5">{label}</span>
            <span className="text-sm text-white leading-relaxed">{value || '—'}</span>
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-900/20 border border-red-700/50 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Generation failed</p>
            <p className="text-xs mt-1 text-red-500">{error}</p>
          </div>
        </div>
      )}
    </div>,
  ]

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      {/* Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-purple to-brand-cyan mb-5 shadow-brand">
          <Sparkles className="w-7 h-7 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Create Campaign</h1>
        <p className="text-gray-400 text-sm">Turn your idea into a complete creative package</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-center gap-2 mb-10">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
              i < step  ? 'bg-brand-purple/30 text-brand-purple-light' :
              i === step ? 'bg-brand-purple text-white shadow-brand-sm' :
                           'bg-surface-card text-gray-500 border border-surface-border'
            }`}>
              {i < step ? <CheckCircle2 className="w-3 h-3" /> : <span>{i + 1}</span>}
              {label}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`w-6 h-px transition-all duration-300 ${i < step ? 'bg-brand-purple/50' : 'bg-surface-border'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Form card */}
      <div className="card p-8">
        {stepContent[step]}

        {/* Animated 3-Stage Progress Indicator during Generation */}
        {loading && (
          <div
            data-testid="generation-progress"
            className="mt-6 p-5 rounded-2xl bg-surface-elevated/90 border border-brand-purple/40 backdrop-blur-md animate-fade-in shadow-card"
          >
            <div className="flex items-center justify-between mb-3 text-xs">
              <div className="flex items-center gap-2 text-brand-purple-light font-semibold">
                <Sparkles className="w-4 h-4 text-brand-cyan animate-pulse" />
                <span>AI Campaign Generation</span>
              </div>
              <span className="text-gray-400 font-medium">Stage {generationStage + 1} of {GENERATION_STAGES.length}</span>
            </div>

            {/* Dynamic Progress Bar */}
            <div className="w-full h-2 bg-surface-base rounded-full overflow-hidden p-0.5 border border-surface-border">
              <div
                className="h-full bg-gradient-to-r from-brand-purple via-brand-purple-light to-brand-cyan rounded-full transition-all duration-700 ease-out"
                style={{ width: `${((generationStage + 1) / GENERATION_STAGES.length) * 100}%` }}
              />
            </div>

            {/* Stage Steps */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 mt-1">
              {GENERATION_STAGES.map((s, idx) => (
                <div
                  key={s.id}
                  className={`flex items-start gap-2.5 p-2 rounded-xl transition-all duration-300 ${
                    idx === generationStage
                      ? 'bg-brand-purple/10 border border-brand-purple/30 text-white font-medium'
                      : idx < generationStage
                      ? 'text-emerald-400 opacity-90'
                      : 'text-gray-500 opacity-60'
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {idx < generationStage ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : idx === generationStage ? (
                      <Loader2 className="w-4 h-4 text-brand-cyan animate-spin" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-gray-600 ml-0.5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate">{s.label}</p>
                    <p className="text-[10px] text-gray-400 hidden sm:block truncate mt-0.5">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-surface-border">
          <button
            onClick={() => setStep(s => s - 1)}
            disabled={step === 0}
            className="btn-secondary disabled:opacity-30"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          {step < STEPS.length - 1 ? (
            <button
              id="next-btn"
              onClick={() => setStep(s => s + 1)}
              disabled={!canProceed()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              Continue
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              id="generate-btn"
              onClick={handleGenerate}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate Campaign
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
