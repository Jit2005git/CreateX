import { useState, useEffect } from 'react'
import {
  RefreshCw,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Hash,
  MessageSquare,
  Youtube,
  Instagram,
  Edit3,
  Plus,
  X,
  Share2,
  Sparkles,
} from 'lucide-react'
import { generateSocial } from '../../services/api'

function CopyBtn({ text, id, label = 'Copy' }) {
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
      className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-surface-elevated transition-all duration-200 flex items-center gap-1 text-xs"
      title={label}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export default function SocialStudio({ campaign, initialSocial, onSocialGenerated }) {
  const [social, setSocial] = useState(initialSocial || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activePlatform, setActivePlatform] = useState('instagram')
  const [selectedCaption, setSelectedCaption] = useState(0)
  const [isEditing, setIsEditing] = useState(false)
  const [newHashtag, setNewHashtag] = useState('')
  const [newTag, setNewTag] = useState('')

  useEffect(() => {
    if (initialSocial) {
      setSocial(initialSocial)
    }
  }, [initialSocial])

  async function handleGenerate() {
    if (!campaign) return
    setLoading(true)
    setError(null)
    try {
      const result = await generateSocial({ campaign })
      const s = result.social
      setSocial(s)
      if (onSocialGenerated) {
        onSocialGenerated(s)
      }
    } catch (err) {
      setError(err.message || 'Social content generation failed.')
    } finally {
      setLoading(false)
    }
  }

  function updateSocial(updater) {
    setSocial(prev => {
      const next = updater(prev)
      if (onSocialGenerated) {
        onSocialGenerated(next)
      }
      return next
    })
  }

  function handleCaptionChange(index, val) {
    updateSocial(prev => {
      const captions = [...(prev.instagram?.captions || [])]
      captions[index] = val
      return {
        ...prev,
        instagram: {
          ...prev.instagram,
          captions,
        },
      }
    })
  }

  function addHashtag() {
    if (!newHashtag.trim()) return
    const clean = newHashtag.trim().replace(/^#/, '')
    updateSocial(prev => ({
      ...prev,
      instagram: {
        ...prev.instagram,
        hashtags: [...(prev.instagram?.hashtags || []), clean],
      },
    }))
    setNewHashtag('')
  }

  function removeHashtag(idx) {
    updateSocial(prev => ({
      ...prev,
      instagram: {
        ...prev.instagram,
        hashtags: prev.instagram.hashtags.filter((_, i) => i !== idx),
      },
    }))
  }

  function addYouTubeTag() {
    if (!newTag.trim()) return
    updateSocial(prev => ({
      ...prev,
      youtube: {
        ...prev.youtube,
        tags: [...(prev.youtube?.tags || []), newTag.trim()],
      },
    }))
    setNewTag('')
  }

  function removeYouTubeTag(idx) {
    updateSocial(prev => ({
      ...prev,
      youtube: {
        ...prev.youtube,
        tags: prev.youtube.tags.filter((_, i) => i !== idx),
      },
    }))
  }

  const platforms = [
    { id: 'instagram', label: 'Instagram', icon: Instagram },
    { id: 'youtube', label: 'YouTube', icon: Youtube },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="section-title">Social Media Studio</h2>
            <span className="badge-cyan text-xs">Copy & Distribution</span>
          </div>
          <p className="section-subtitle mt-0.5">
            Platform-optimized captions, hashtags, headlines, and ad copy.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {social && (
            <button
              type="button"
              onClick={() => setIsEditing(!isEditing)}
              className="btn-secondary text-xs px-3.5 py-2 flex items-center gap-1.5"
            >
              <Edit3 className="w-3.5 h-3.5 text-brand-cyan" />
              {isEditing ? 'Done Editing' : 'Edit Copy'}
            </button>
          )}

          <button
            id="generate-social-btn"
            onClick={handleGenerate}
            disabled={loading || !campaign}
            className="btn-primary text-xs px-4 py-2 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            {social ? 'Regenerate Content' : 'Generate Content'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="card h-80 flex flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="w-16 h-16 rounded-full border-2 border-brand-cyan/20 border-t-brand-cyan animate-spin" />
          <div className="space-y-1">
            <p className="text-white font-medium">Crafting tailored social copy...</p>
            <p className="text-gray-400 text-sm">
              Writing compelling Instagram hooks, viral hashtags, and YouTube launch packaging.
            </p>
          </div>
        </div>
      ) : error ? (
        <div className="card h-64 flex flex-col items-center justify-center gap-4 p-6 text-center">
          <div className="w-12 h-12 rounded-xl bg-red-900/20 border border-red-700/30 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-red-400" />
          </div>
          <div className="max-w-md">
            <p className="text-white font-medium">Generation Notice</p>
            <p className="text-red-400 text-sm mt-1">{error}</p>
          </div>
          <button
            onClick={handleGenerate}
            className="btn-primary text-xs px-4 py-2 flex items-center gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Try Again
          </button>
        </div>
      ) : social ? (
        <div className="space-y-6">
          {/* Promotional Headlines */}
          {social.headlines?.length > 0 && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-amber" />
                  Promotional Headlines
                </h3>
                <CopyBtn
                  id="copy-all-headlines"
                  text={social.headlines.join('\n')}
                  label="Copy all headlines"
                />
              </div>

              <div className="space-y-2.5">
                {social.headlines.map((h, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-3 p-3 rounded-xl bg-surface-elevated/70 border border-surface-border"
                  >
                    {isEditing ? (
                      <input
                        type="text"
                        className="input text-xs flex-1"
                        value={h}
                        onChange={e => {
                          const updated = [...social.headlines]
                          updated[i] = e.target.value
                          updateSocial(prev => ({ ...prev, headlines: updated }))
                        }}
                      />
                    ) : (
                      <p className="text-sm text-gray-200 font-medium">{h}</p>
                    )}
                    <CopyBtn id={`copy-headline-${i}`} text={h} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Core Advertising Copy */}
          {social.ad_copy && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-white text-sm">Core Advertising Copy</h3>
                <CopyBtn id="copy-ad-copy" text={social.ad_copy} />
              </div>
              {isEditing ? (
                <textarea
                  className="textarea text-xs h-20"
                  value={social.ad_copy}
                  onChange={e =>
                    updateSocial(prev => ({ ...prev, ad_copy: e.target.value }))
                  }
                />
              ) : (
                <p className="text-sm text-gray-300 leading-relaxed bg-surface-elevated/60 p-3.5 rounded-xl border border-surface-border">
                  {social.ad_copy}
                </p>
              )}
            </div>
          )}

          {/* Platform Switcher Tabs */}
          <div className="flex gap-2 border-b border-surface-border pb-3">
            {platforms.map(({ id, label, icon: Icon }) => {
              const active = activePlatform === id
              return (
                <button
                  key={id}
                  id={`platform-tab-${id}`}
                  onClick={() => setActivePlatform(id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                    active
                      ? 'bg-gradient-to-r from-brand-purple to-brand-cyan text-white shadow-brand-sm'
                      : 'bg-surface-card border border-surface-border text-gray-400 hover:text-white'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              )
            })}
          </div>

          {/* Instagram Section */}
          {activePlatform === 'instagram' && social.instagram && (
            <div className="space-y-5 animate-fade-in">
              {/* Caption Variations */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
                    <MessageSquare className="w-4 h-4 text-brand-purple-light" />
                    Instagram Captions (3 Angles)
                  </h3>
                  <span className="text-xs text-gray-500">
                    {isEditing ? 'Editing mode active' : 'Click to preview angle'}
                  </span>
                </div>

                <div className="space-y-3">
                  {(social.instagram.captions || []).map((caption, i) => (
                    <div
                      key={i}
                      onClick={() => !isEditing && setSelectedCaption(i)}
                      className={`p-4 rounded-xl border transition-all duration-200 ${
                        selectedCaption === i && !isEditing
                          ? 'border-brand-purple bg-brand-purple/10 shadow-sm'
                          : 'border-surface-border bg-surface-elevated/60 hover:border-surface-border-light'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        {isEditing ? (
                          <textarea
                            className="textarea text-xs h-24 flex-1"
                            value={caption}
                            onChange={e => handleCaptionChange(i, e.target.value)}
                          />
                        ) : (
                          <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                            {caption}
                          </p>
                        )}
                        <CopyBtn id={`copy-caption-${i}`} text={caption} />
                      </div>
                      <span className="text-[11px] font-mono text-gray-500 mt-2 block">
                        Variation {i + 1}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Hashtag Cloud */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
                    <Hash className="w-4 h-4 text-brand-cyan-light" />
                    Hashtags
                  </h3>
                  <CopyBtn
                    id="copy-hashtags"
                    text={(social.instagram.hashtags || []).map(h => `#${h}`).join(' ')}
                    label="Copy hashtag block"
                  />
                </div>

                <div className="flex flex-wrap gap-2 mb-3">
                  {(social.instagram.hashtags || []).map((tag, i) => (
                    <span
                      key={i}
                      className="badge-cyan text-xs flex items-center gap-1.5 py-1 px-2.5"
                    >
                      #{tag}
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => removeHashtag(i)}
                          className="hover:text-red-400"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </span>
                  ))}
                </div>

                {isEditing && (
                  <div className="flex items-center gap-2 pt-2 border-t border-surface-border">
                    <input
                      type="text"
                      className="input text-xs flex-1"
                      placeholder="Add hashtag without '#'..."
                      value={newHashtag}
                      onChange={e => setNewHashtag(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addHashtag())}
                    />
                    <button type="button" onClick={addHashtag} className="btn-secondary text-xs px-3 py-2">
                      <Plus className="w-3.5 h-3.5" /> Add
                    </button>
                  </div>
                )}
              </div>

              {/* Instagram Call to Action */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">Instagram Call to Action</h3>
                  <CopyBtn id="copy-ig-cta" text={social.instagram.cta} />
                </div>
                {isEditing ? (
                  <input
                    type="text"
                    className="input text-xs"
                    value={social.instagram.cta || ''}
                    onChange={e =>
                      updateSocial(prev => ({
                        ...prev,
                        instagram: { ...prev.instagram, cta: e.target.value },
                      }))
                    }
                  />
                ) : (
                  <p className="text-sm text-brand-cyan-light font-medium bg-brand-cyan/10 p-3 rounded-xl border border-brand-cyan/20">
                    {social.instagram.cta || 'Tap the link in bio to learn more.'}
                  </p>
                )}
              </div>

              {/* Instagram Stories Prompt */}
              {social.instagram.story_text && (
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-white text-sm">Stories Text Prompt</h3>
                    <CopyBtn id="copy-ig-story" text={social.instagram.story_text} />
                  </div>
                  {isEditing ? (
                    <input
                      type="text"
                      className="input text-xs"
                      value={social.instagram.story_text}
                      onChange={e =>
                        updateSocial(prev => ({
                          ...prev,
                          instagram: { ...prev.instagram, story_text: e.target.value },
                        }))
                      }
                    />
                  ) : (
                    <p className="text-sm text-gray-300 italic bg-surface-elevated/60 p-3 rounded-xl border border-surface-border">
                      "{social.instagram.story_text}"
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* YouTube Section */}
          {activePlatform === 'youtube' && social.youtube && (
            <div className="space-y-5 animate-fade-in">
              {/* YouTube Title */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">Video Title</h3>
                  <CopyBtn id="copy-yt-title" text={social.youtube.title} />
                </div>
                {isEditing ? (
                  <input
                    type="text"
                    className="input text-sm font-semibold"
                    value={social.youtube.title}
                    onChange={e =>
                      updateSocial(prev => ({
                        ...prev,
                        youtube: { ...prev.youtube, title: e.target.value },
                      }))
                    }
                  />
                ) : (
                  <p className="text-brand-purple-light font-bold text-lg">
                    {social.youtube.title}
                  </p>
                )}
              </div>

              {/* YouTube Description */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white text-sm">Video Description</h3>
                  <CopyBtn id="copy-yt-desc" text={social.youtube.description} />
                </div>
                {isEditing ? (
                  <textarea
                    className="textarea text-xs h-36 font-mono"
                    value={social.youtube.description}
                    onChange={e =>
                      updateSocial(prev => ({
                        ...prev,
                        youtube: { ...prev.youtube, description: e.target.value },
                      }))
                    }
                  />
                ) : (
                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap bg-surface-elevated/60 p-4 rounded-xl border border-surface-border font-sans">
                    {social.youtube.description}
                  </p>
                )}
              </div>

              {/* Search Tags */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white text-sm">Search Tags</h3>
                  <CopyBtn
                    id="copy-yt-tags"
                    text={(social.youtube.tags || []).join(', ')}
                    label="Copy comma-separated tags"
                  />
                </div>
                <div className="flex flex-wrap gap-2 mb-3">
                  {(social.youtube.tags || []).map((tag, i) => (
                    <span
                      key={i}
                      className="badge-purple text-xs flex items-center gap-1.5 py-1 px-2.5"
                    >
                      {tag}
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => removeYouTubeTag(i)}
                          className="hover:text-red-400"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </span>
                  ))}
                </div>

                {isEditing && (
                  <div className="flex items-center gap-2 pt-2 border-t border-surface-border">
                    <input
                      type="text"
                      className="input text-xs flex-1"
                      placeholder="Add tag..."
                      value={newTag}
                      onChange={e => setNewTag(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addYouTubeTag())}
                    />
                    <button type="button" onClick={addYouTubeTag} className="btn-secondary text-xs px-3 py-2">
                      <Plus className="w-3.5 h-3.5" /> Add
                    </button>
                  </div>
                )}
              </div>

              {/* Thumbnail Overlay Text */}
              {social.youtube.thumbnail_text && (
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-white text-sm">Thumbnail Graphic Text</h3>
                    <CopyBtn id="copy-yt-thumb" text={social.youtube.thumbnail_text} />
                  </div>
                  {isEditing ? (
                    <input
                      type="text"
                      className="input text-xs font-mono"
                      value={social.youtube.thumbnail_text}
                      onChange={e =>
                        updateSocial(prev => ({
                          ...prev,
                          youtube: { ...prev.youtube, thumbnail_text: e.target.value },
                        }))
                      }
                    />
                  ) : (
                    <span className="font-mono text-xs font-bold text-brand-amber bg-brand-amber/10 py-1.5 px-3 rounded-lg border border-brand-amber/20 inline-block">
                      {social.youtube.thumbnail_text}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="card h-72 flex flex-col items-center justify-center gap-4 p-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
            <Share2 className="w-8 h-8 text-gray-500" />
          </div>
          <div className="max-w-sm">
            <p className="text-white font-medium">No social content generated yet</p>
            <p className="text-gray-400 text-sm mt-1">
              Click{' '}
              <span className="text-brand-cyan font-medium">Generate Content</span> to create tailored copy for Instagram and YouTube.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
