import { useState } from 'react'
import { RefreshCw, Loader2, AlertCircle, Copy, Check, Hash, MessageSquare, Youtube, Instagram } from 'lucide-react'
import { generateSocial } from '../../services/api'

function CopyBtn({ text, id }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button id={id} onClick={copy} className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-surface-elevated transition-all duration-200" title="Copy">
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export default function SocialStudio({ campaign, initialSocial }) {
  const [social, setSocial] = useState(initialSocial || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activePlatform, setActivePlatform] = useState('instagram')
  const [selectedCaption, setSelectedCaption] = useState(0)

  async function handleGenerate() {
    if (!campaign) return
    setLoading(true)
    setError(null)
    try {
      const result = await generateSocial({ campaign })
      setSocial(result.social)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const platforms = [
    { id: 'instagram', label: 'Instagram', icon: Instagram },
    { id: 'youtube', label: 'YouTube', icon: Youtube },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="section-title">Social Media Studio</h2>
          <p className="section-subtitle">Platform-optimized captions, hashtags & headlines</p>
        </div>
        <button
          id="generate-social-btn"
          onClick={handleGenerate}
          disabled={loading || !campaign}
          className="btn-primary text-xs px-4 py-2"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          {social ? 'Regenerate' : 'Generate Content'}
        </button>
      </div>

      {loading ? (
        <div className="card h-64 flex flex-col items-center justify-center gap-4">
          <Loader2 className="w-8 h-8 text-brand-purple-light animate-spin" />
          <p className="text-white font-medium">Crafting your social content...</p>
        </div>
      ) : error ? (
        <div className="card h-48 flex flex-col items-center justify-center gap-4 p-6">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <p className="text-red-400 text-sm text-center">{error}</p>
          <button onClick={handleGenerate} className="btn-primary text-xs px-4 py-2"><RefreshCw className="w-3.5 h-3.5" /> Retry</button>
        </div>
      ) : social ? (
        <div className="space-y-5">
          {/* Headlines */}
          {social.headlines?.length > 0 && (
            <div className="card p-5">
              <h3 className="font-semibold text-white mb-3">Promotional Headlines</h3>
              <div className="space-y-2">
                {social.headlines.map((h, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-surface-elevated border border-surface-border">
                    <p className="text-sm text-gray-300 font-medium">{h}</p>
                    <CopyBtn id={`copy-headline-${i}`} text={h} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Platform tabs */}
          <div className="flex gap-2">
            {platforms.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                id={`platform-tab-${id}`}
                onClick={() => setActivePlatform(id)}
                className={activePlatform === id ? 'tab-active' : 'tab border border-surface-border'}
              >
                <Icon className="w-4 h-4 inline mr-1.5" />
                {label}
              </button>
            ))}
          </div>

          {/* Instagram content */}
          {activePlatform === 'instagram' && social.instagram && (
            <div className="space-y-4 animate-fade-in">
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-brand-purple-light" />
                    Caption Variations
                  </h3>
                </div>
                <div className="space-y-3">
                  {social.instagram.captions?.map((caption, i) => (
                    <div
                      key={i}
                      onClick={() => setSelectedCaption(i)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                        selectedCaption === i
                          ? 'border-brand-purple bg-brand-purple/10'
                          : 'border-surface-border bg-surface-elevated hover:border-surface-border-light'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm text-gray-300 leading-relaxed">{caption}</p>
                        <CopyBtn id={`copy-caption-${i}`} text={caption} />
                      </div>
                      <span className="text-xs text-gray-600 mt-2 block">Variation {i + 1}</span>
                    </div>
                  ))}
                </div>
              </div>

              {social.instagram.hashtags?.length > 0 && (
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-white flex items-center gap-2">
                      <Hash className="w-4 h-4 text-brand-cyan-light" /> Hashtags
                    </h3>
                    <CopyBtn id="copy-hashtags" text={social.instagram.hashtags.map(h => `#${h}`).join(' ')} />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {social.instagram.hashtags.map((tag, i) => (
                      <span key={i} className="badge-cyan text-xs cursor-pointer hover:scale-105 transition-transform">#{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {social.instagram.cta && (
                <div className="card p-5">
                  <h3 className="font-semibold text-white mb-2">Call to Action</h3>
                  <p className="text-brand-cyan-light font-medium">{social.instagram.cta}</p>
                </div>
              )}
            </div>
          )}

          {/* YouTube content */}
          {activePlatform === 'youtube' && social.youtube && (
            <div className="space-y-4 animate-fade-in">
              <div className="card p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-white">Video Title</h3>
                  <CopyBtn id="copy-yt-title" text={social.youtube.title} />
                </div>
                <p className="text-brand-purple-light font-semibold text-lg">{social.youtube.title}</p>
              </div>

              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">Description</h3>
                  <CopyBtn id="copy-yt-desc" text={social.youtube.description} />
                </div>
                <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{social.youtube.description}</p>
              </div>

              {social.youtube.tags?.length > 0 && (
                <div className="card p-5">
                  <h3 className="font-semibold text-white mb-3">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {social.youtube.tags.map((tag, i) => (
                      <span key={i} className="badge-purple text-xs">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {social.youtube.cta && (
                <div className="card p-5">
                  <h3 className="font-semibold text-white mb-2">Call to Action</h3>
                  <p className="text-brand-cyan-light font-medium">{social.youtube.cta}</p>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="card h-64 flex flex-col items-center justify-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
            <MessageSquare className="w-7 h-7 text-gray-600" />
          </div>
          <div className="text-center">
            <p className="text-white font-medium">No social content yet</p>
            <p className="text-gray-500 text-sm mt-1">Generate platform-optimized captions, hashtags and headlines</p>
          </div>
        </div>
      )}
    </div>
  )
}
