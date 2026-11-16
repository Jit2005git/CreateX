import { useState, useEffect } from 'react'
import {
  Copy,
  Check,
  Edit3,
  Save,
  X,
  Plus,
  Trash2,
  Sparkles,
  Palette,
  Target,
  FileText,
  Eye,
  Sliders,
} from 'lucide-react'

function ColorSwatch({ color, label, onChange, isEditing }) {
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-xl bg-surface-elevated/70 border border-surface-border">
      {isEditing ? (
        <input
          type="color"
          value={color || '#000000'}
          onChange={e => onChange(e.target.value)}
          className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0"
        />
      ) : (
        <div
          className="w-8 h-8 rounded-lg border border-white/20 shadow-sm shrink-0"
          style={{ backgroundColor: color }}
          title={color}
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-[11px] text-gray-400 font-medium">{label}</p>
        {isEditing ? (
          <input
            type="text"
            value={color || ''}
            onChange={e => onChange(e.target.value)}
            className="input text-xs py-1 px-2 font-mono h-7 mt-0.5"
            placeholder="#HEX"
          />
        ) : (
          <p className="text-xs font-mono text-gray-300 font-semibold">{color || 'N/A'}</p>
        )}
      </div>
    </div>
  )
}

function CopyButton({ text, id }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    if (!text) return
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      id={id}
      onClick={copy}
      className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-surface-elevated transition-all duration-200"
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export default function CampaignOverview({ campaign, onUpdateCampaign }) {
  if (!campaign) return null

  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({ ...campaign })
  const [newConcept, setNewConcept] = useState('')
  const [newMessage, setNewMessage] = useState('')

  useEffect(() => {
    setFormData({ ...campaign })
  }, [campaign])

  function handleSave() {
    if (onUpdateCampaign) {
      onUpdateCampaign(formData)
    }
    setIsEditing(false)
  }

  function handleCancel() {
    setFormData({ ...campaign })
    setIsEditing(false)
  }

  function handleColorChange(field, val) {
    setFormData(prev => ({
      ...prev,
      brand_colors: {
        ...(prev.brand_colors || {}),
        [field]: val,
      },
    }))
  }

  function addConcept() {
    if (!newConcept.trim()) return
    setFormData(prev => ({
      ...prev,
      creative_concepts: [...(prev.creative_concepts || []), newConcept.trim()],
    }))
    setNewConcept('')
  }

  function removeConcept(index) {
    setFormData(prev => ({
      ...prev,
      creative_concepts: prev.creative_concepts.filter((_, i) => i !== index),
    }))
  }

  function addMessage() {
    if (!newMessage.trim()) return
    setFormData(prev => ({
      ...prev,
      key_messages: [...(prev.key_messages || []), newMessage.trim()],
    }))
    setNewMessage('')
  }

  function removeMessage(index) {
    setFormData(prev => ({
      ...prev,
      key_messages: prev.key_messages.filter((_, i) => i !== index),
    }))
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
        <div>
          <h2 className="section-title">Campaign Overview</h2>
          <p className="section-subtitle">
            Shared strategic context, brand identity, and core messaging.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                id="cancel-campaign-edit-btn"
                onClick={handleCancel}
                className="btn-secondary text-xs px-3.5 py-2 flex items-center gap-1.5"
              >
                <X className="w-3.5 h-3.5" />
                Cancel
              </button>
              <button
                id="save-campaign-edit-btn"
                onClick={handleSave}
                className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5"
              >
                <Save className="w-3.5 h-3.5" />
                Save Changes
              </button>
            </>
          ) : (
            <button
              id="edit-campaign-btn"
              onClick={() => setIsEditing(true)}
              className="btn-secondary text-xs px-4 py-2 flex items-center gap-1.5 hover:border-brand-purple/50"
            >
              <Edit3 className="w-3.5 h-3.5 text-brand-purple-light" />
              Edit Details
            </button>
          )}
        </div>
      </div>

      {/* Main Campaign Identity Header Card */}
      <div className="card p-6 sm:p-8 relative overflow-hidden border border-surface-border">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-brand-purple/15 to-brand-cyan/15 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-4">
          {isEditing ? (
            <div className="space-y-4">
              <div>
                <label className="label text-xs">Campaign Name</label>
                <input
                  type="text"
                  className="input text-lg font-bold"
                  value={formData.campaign_name || ''}
                  onChange={e => setFormData({ ...formData, campaign_name: e.target.value })}
                  placeholder="Campaign Name"
                />
              </div>

              <div>
                <label className="label text-xs">Tagline</label>
                <input
                  type="text"
                  className="input text-sm italic"
                  value={formData.tagline || ''}
                  onChange={e => setFormData({ ...formData, tagline: e.target.value })}
                  placeholder="Memorable Tagline"
                />
              </div>

              <div>
                <label className="label text-xs">Campaign Description</label>
                <textarea
                  className="textarea text-sm h-24"
                  value={formData.description || ''}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  placeholder="2-3 sentence overview"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="label text-xs">Target Audience</label>
                  <input
                    type="text"
                    className="input text-xs"
                    value={formData.target_audience || ''}
                    onChange={e => setFormData({ ...formData, target_audience: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label text-xs">Tone of Voice</label>
                  <input
                    type="text"
                    className="input text-xs"
                    value={formData.tone || formData.writing_tone || ''}
                    onChange={e =>
                      setFormData({
                        ...formData,
                        tone: e.target.value,
                        writing_tone: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {campaign.campaign_name}
                  </h2>
                  <p className="text-brand-cyan-light text-base sm:text-lg font-medium mt-1 italic">
                    "{campaign.tagline}"
                  </p>
                </div>
                <CopyButton
                  id="copy-campaign-summary"
                  text={`${campaign.campaign_name} - "${campaign.tagline}"\n\n${campaign.description}`}
                />
              </div>

              <p className="text-gray-300 mt-4 leading-relaxed text-sm sm:text-base max-w-3xl">
                {campaign.description}
              </p>

              <div className="flex flex-wrap items-center gap-2 mt-5">
                <span className="badge-purple flex items-center gap-1.5 text-xs">
                  <Target className="w-3 h-3 text-brand-purple-light" />
                  Audience: {campaign.target_audience}
                </span>
                <span className="badge-cyan flex items-center gap-1.5 text-xs">
                  <Sliders className="w-3 h-3 text-brand-cyan" />
                  Tone: {campaign.tone || campaign.writing_tone || 'Bold'}
                </span>
                {campaign.visual_style && (
                  <span className="badge-amber flex items-center gap-1.5 text-xs">
                    <Sparkles className="w-3 h-3 text-brand-amber" />
                    Style: {campaign.visual_style}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Original Idea & Strategic Foundation */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
            <FileText className="w-4 h-4 text-brand-amber" />
            Original Creative Concept
          </h3>
          {!isEditing && <CopyButton id="copy-orig-idea" text={campaign.original_idea} />}
        </div>
        {isEditing ? (
          <textarea
            className="textarea text-sm h-20"
            value={formData.original_idea || ''}
            onChange={e => setFormData({ ...formData, original_idea: e.target.value })}
            placeholder="The original inspiration or prompt idea..."
          />
        ) : (
          <p className="text-gray-300 text-sm leading-relaxed bg-surface-elevated/60 p-3.5 rounded-xl border border-surface-border">
            {campaign.original_idea || campaign.description}
          </p>
        )}
      </div>

      {/* Brand Color Palette */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
            <Palette className="w-4 h-4 text-brand-purple-light" />
            Brand Color Palette
          </h3>
          <span className="text-xs text-gray-500">
            {isEditing ? 'Click swatch or edit hex to change' : 'Harmonized across all creative outputs'}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <ColorSwatch
            color={formData.brand_colors?.primary}
            label="Primary Brand"
            isEditing={isEditing}
            onChange={v => handleColorChange('primary', v)}
          />
          <ColorSwatch
            color={formData.brand_colors?.secondary}
            label="Secondary Brand"
            isEditing={isEditing}
            onChange={v => handleColorChange('secondary', v)}
          />
          <ColorSwatch
            color={formData.brand_colors?.accent}
            label="Accent Highlight"
            isEditing={isEditing}
            onChange={v => handleColorChange('accent', v)}
          />
          <ColorSwatch
            color={formData.brand_colors?.background}
            label="Canvas Background"
            isEditing={isEditing}
            onChange={v => handleColorChange('background', v)}
          />
        </div>
      </div>

      {/* Creative Concepts */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
            <Sparkles className="w-4 h-4 text-brand-cyan-light" />
            Creative Concepts
          </h3>
          {!isEditing && (
            <CopyButton
              id="copy-concepts"
              text={(campaign.creative_concepts || []).join('\n')}
            />
          )}
        </div>

        {isEditing ? (
          <div className="space-y-3">
            {(formData.creative_concepts || []).map((concept, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-purple/30 text-brand-purple-light text-xs flex items-center justify-center shrink-0 font-bold">
                  {i + 1}
                </span>
                <input
                  type="text"
                  className="input text-xs flex-1"
                  value={concept}
                  onChange={e => {
                    const updated = [...formData.creative_concepts]
                    updated[i] = e.target.value
                    setFormData({ ...formData, creative_concepts: updated })
                  }}
                />
                <button
                  type="button"
                  onClick={() => removeConcept(i)}
                  className="p-1.5 text-gray-500 hover:text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2 pt-2 border-t border-surface-border">
              <input
                type="text"
                placeholder="Add another creative concept..."
                className="input text-xs flex-1"
                value={newConcept}
                onChange={e => setNewConcept(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addConcept())}
              />
              <button type="button" onClick={addConcept} className="btn-secondary text-xs px-3 py-2">
                <Plus className="w-3.5 h-3.5" /> Add
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {(campaign.creative_concepts || []).map((concept, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-surface-elevated/40 border border-surface-border/60">
                <span className="w-6 h-6 rounded-full bg-brand-purple/20 text-brand-purple-light text-xs flex items-center justify-center shrink-0 font-bold mt-0.5">
                  {i + 1}
                </span>
                <p className="text-gray-200 text-sm leading-relaxed">{concept}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Visual Direction */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
            <Eye className="w-4 h-4 text-brand-purple-light" />
            Visual Direction
          </h3>
          {!isEditing && <CopyButton id="copy-visual-direction" text={campaign.visual_direction} />}
        </div>
        {isEditing ? (
          <textarea
            className="textarea text-sm h-28"
            value={formData.visual_direction || ''}
            onChange={e => setFormData({ ...formData, visual_direction: e.target.value })}
            placeholder="Detailed description of lighting, photography style, visual metaphors..."
          />
        ) : (
          <p className="text-gray-300 text-sm leading-relaxed bg-surface-elevated/40 p-4 rounded-xl border border-surface-border/60">
            {campaign.visual_direction}
          </p>
        )}
      </div>

      {/* Key Messages */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-white text-sm">Key Brand Messages</h3>
          {!isEditing && (
            <CopyButton id="copy-messages" text={(campaign.key_messages || []).join(' | ')} />
          )}
        </div>

        {isEditing ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {(formData.key_messages || []).map((msg, i) => (
                <span
                  key={i}
                  className="badge-cyan text-xs flex items-center gap-1.5 py-1 px-2.5"
                >
                  {msg}
                  <button
                    type="button"
                    onClick={() => removeMessage(i)}
                    className="hover:text-red-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2 pt-2">
              <input
                type="text"
                placeholder="Add a key message..."
                className="input text-xs flex-1"
                value={newMessage}
                onChange={e => setNewMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addMessage())}
              />
              <button type="button" onClick={addMessage} className="btn-secondary text-xs px-3 py-2">
                <Plus className="w-3.5 h-3.5" /> Add
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(campaign.key_messages || []).map((msg, i) => (
              <span key={i} className="badge-cyan text-xs py-1 px-3">
                {msg}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
