import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Sparkles,
  Image,
  Film,
  Share2,
  AlertCircle,
  Download,
  FileText,
  FileCode,
  Copy,
  Check,
  ChevronDown,
  CheckCircle2,
  Clock,
  Layers,
} from 'lucide-react'
import { getProject, saveAsset } from '../services/api'
import CampaignOverview from '../components/workspace/CampaignOverview'
import PosterStudio from '../components/workspace/PosterStudio'
import StoryboardStudio from '../components/workspace/StoryboardStudio'
import SocialStudio from '../components/workspace/SocialStudio'
import {
  generateMarkdownDossier,
  generateCampaignJson,
  downloadBlob,
} from '../utils/exportUtils'

const TABS = [
  { id: 'overview',   label: 'Campaign Strategy', icon: Sparkles, key: null },
  { id: 'poster',     label: 'Poster Studio',    icon: Image,    key: 'poster' },
  { id: 'storyboard', label: 'Storyboard Studio',icon: Film,     key: 'storyboard' },
  { id: 'social',     label: 'Social Media',     icon: Share2,   key: 'social' },
]

export default function Workspace() {
  const { projectId } = useParams()
  const [campaign, setCampaign] = useState(null)
  const [assets, setAssets] = useState({ poster: null, storyboard: null, social: null })
  const [metadata, setMetadata] = useState({
    project_id: projectId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [copiedDossier, setCopiedDossier] = useState(false)
  const exportRef = useRef(null)

  // Close export dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (exportRef.current && !exportRef.current.contains(event.target)) {
        setExportOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    loadWorkspace()
  }, [projectId])

  async function loadWorkspace() {
    try {
      setLoading(true)
      setError(null)

      // 1. Try sessionStorage for campaign context
      let loadedCampaign = null
      const cachedCampaign = sessionStorage.getItem(`campaign_${projectId}`)
      if (cachedCampaign) {
        try {
          loadedCampaign = JSON.parse(cachedCampaign)
        } catch {
          loadedCampaign = null
        }
      }

      // Fallback for local session project
      if (!loadedCampaign && projectId === 'local') {
        const local = sessionStorage.getItem('createx_campaign_local')
        if (local) {
          try {
            loadedCampaign = JSON.parse(local)
          } catch {
            loadedCampaign = null
          }
        }
      }

      // 2. Try sessionStorage for existing assets
      let loadedAssets = { poster: null, storyboard: null, social: null }
      const cachedAssets = sessionStorage.getItem(`assets_${projectId}`)
      if (cachedAssets) {
        try {
          const parsed = JSON.parse(cachedAssets)
          loadedAssets = { ...loadedAssets, ...parsed }
        } catch {
          // ignore parsing error
        }
      }

      // 3. Fall back to backend project fetch if campaign not in sessionStorage
      if (!loadedCampaign) {
        const data = await getProject(projectId)
        if (data?.campaign_data) {
          loadedCampaign = data.campaign_data
          const assetMap = {}
          ;(data.assets || []).forEach(a => {
            assetMap[a.asset_type] = a.content || a
          })
          loadedAssets = { ...loadedAssets, ...assetMap }

          // Cache in session
          sessionStorage.setItem(`campaign_${projectId}`, JSON.stringify(loadedCampaign))
          sessionStorage.setItem(`assets_${projectId}`, JSON.stringify(loadedAssets))
        } else {
          throw new Error('Campaign data not found for this project. Please create a new campaign.')
        }
      }

      setCampaign(loadedCampaign)
      setAssets(loadedAssets)
      setMetadata({
        project_id: projectId,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    } catch (err) {
      setError(err.message || 'Failed to load campaign workspace.')
    } finally {
      setLoading(false)
    }
  }

  // Synchronized state handlers preserving all other assets
  async function persistAsset(assetType, content, assetUrl = null, storagePath = null) {
    if (!projectId || projectId === 'local') return
    try {
      await saveAsset(projectId, {
        asset_type: assetType,
        content: content,
        asset_url: assetUrl,
        storage_path: storagePath,
      })
    } catch (err) {
      // Graceful fallback: Supabase not yet configured or offline
      // Local sessionStorage already stores the generated asset safely
      console.warn(`Could not persist ${assetType} to remote database:`, err.message)
    }
  }

  function handleUpdateCampaign(updatedCampaign) {
    setCampaign(updatedCampaign)
    sessionStorage.setItem(`campaign_${projectId}`, JSON.stringify(updatedCampaign))
    setMetadata(prev => ({ ...prev, updated_at: new Date().toISOString() }))
  }

  function handlePosterGenerated(posterData) {
    setAssets(prev => {
      const next = { ...prev, poster: posterData }
      sessionStorage.setItem(`assets_${projectId}`, JSON.stringify(next))
      return next
    })
    setMetadata(prev => ({ ...prev, updated_at: new Date().toISOString() }))
    persistAsset('poster', posterData, posterData?.image_url, posterData?.storage_path)
  }

  function handleStoryboardGenerated(storyboardData) {
    setAssets(prev => {
      const next = { ...prev, storyboard: storyboardData }
      sessionStorage.setItem(`assets_${projectId}`, JSON.stringify(next))
      return next
    })
    setMetadata(prev => ({ ...prev, updated_at: new Date().toISOString() }))
    persistAsset('storyboard', storyboardData)
  }

  function handleSocialGenerated(socialData) {
    setAssets(prev => {
      const next = { ...prev, social: socialData }
      sessionStorage.setItem(`assets_${projectId}`, JSON.stringify(next))
      return next
    })
    setMetadata(prev => ({ ...prev, updated_at: new Date().toISOString() }))
    persistAsset('social', socialData)
  }

  // Export actions
  const safeFilename = (campaign?.campaign_name || 'campaign')
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '_')
    .replace(/_+/g, '_')

  function handleExportMarkdown() {
    const md = generateMarkdownDossier(campaign, assets, metadata)
    downloadBlob(md, `${safeFilename}_dossier.md`, 'text/markdown')
    setExportOpen(false)
  }

  function handleExportJson() {
    const json = generateCampaignJson(campaign, assets, metadata)
    downloadBlob(json, `${safeFilename}_campaign.json`, 'application/json')
    setExportOpen(false)
  }

  async function handleCopyDossier() {
    const md = generateMarkdownDossier(campaign, assets, metadata)
    await navigator.clipboard.writeText(md)
    setCopiedDossier(true)
    setTimeout(() => {
      setCopiedDossier(false)
      setExportOpen(false)
    }, 1800)
  }

  // Asset status metrics
  const assetStatus = {
    poster: !!assets.poster?.image_url,
    storyboard: !!(assets.storyboard?.scenes && assets.storyboard.scenes.length > 0),
    social: !!assets.social,
  }
  const generatedCount = Object.values(assetStatus).filter(Boolean).length

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-6 animate-pulse">
        <div className="skeleton h-10 w-48 rounded-xl" />
        <div className="skeleton h-16 w-full rounded-2xl" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton h-12 rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-20 text-center animate-fade-in">
        <div className="card p-10 border-red-500/20 bg-red-500/5">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Campaign Workspace Not Found</h2>
          <p className="text-gray-400 text-sm mb-6">
            {error || 'Could not retrieve campaign data for this workspace.'}
          </p>
          <Link to="/create" className="btn-primary inline-flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Create New Campaign
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6 animate-fade-in">
      {/* Top Header & Navigation Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-surface-border">
        {/* Back button & Campaign Identity */}
        <div className="flex items-start gap-3.5 min-w-0">
          <Link
            to="/"
            className="p-2 rounded-xl bg-surface-card border border-surface-border text-gray-400 hover:text-white hover:border-surface-border-light transition-all duration-200 shrink-0 mt-0.5"
            title="Return to Home"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight truncate">
                {campaign.campaign_name || 'Untitled Campaign'}
              </h1>
              <span className="badge-purple text-xs shrink-0">
                {campaign.industry || 'Campaign'}
              </span>
            </div>
            <p className="text-gray-400 text-xs sm:text-sm mt-0.5 italic truncate">
              "{campaign.tagline || 'One Idea. Multiple Creative Possibilities.'}"
            </p>
          </div>
        </div>

        {/* Right Header Utilities: Swatches, Asset Readiness, and Export Menu */}
        <div className="flex items-center gap-3 self-start md:self-auto shrink-0 flex-wrap">
          {/* Brand Colors Mini-Palette */}
          {campaign.brand_colors && (
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-card border border-surface-border"
              title="Campaign Brand Palette"
            >
              {Object.entries(campaign.brand_colors).map(([key, color]) =>
                color ? (
                  <div
                    key={key}
                    className="w-5 h-5 rounded-full border border-white/20 shadow-sm transition-transform hover:scale-110"
                    style={{ backgroundColor: color }}
                    title={`${key}: ${color}`}
                  />
                ) : null
              )}
            </div>
          )}

          {/* Asset Readiness Counter */}
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-card border border-surface-border text-xs text-gray-300"
            title="Generated Creative Studios"
          >
            <Layers className="w-3.5 h-3.5 text-brand-purple-light" />
            <span className="font-semibold text-white">{generatedCount}/3</span>
            <span className="text-gray-500">Studios</span>
          </div>

          {/* Campaign Export Dropdown */}
          <div className="relative" ref={exportRef}>
            <button
              id="export-campaign-btn"
              onClick={() => setExportOpen(prev => !prev)}
              className="btn-primary text-xs px-4 py-2 flex items-center gap-2 shadow-brand-sm"
              aria-expanded={exportOpen}
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Campaign</span>
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform duration-200 ${
                  exportOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {exportOpen && (
              <div
                id="export-dropdown-menu"
                className="absolute right-0 mt-2 w-72 rounded-2xl bg-[#121222] border border-surface-border-light shadow-2xl p-2 z-50 animate-scale-in"
              >
                <div className="px-3 py-2 border-b border-surface-border">
                  <p className="text-xs font-semibold text-white">Campaign Export Package</p>
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    Includes strategic overview and all current studio outputs.
                  </p>
                </div>

                <div className="py-1 space-y-1">
                  <button
                    id="export-dossier-md-btn"
                    onClick={handleExportMarkdown}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs hover:bg-surface-elevated text-gray-200 hover:text-white flex items-center gap-3 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-brand-cyan-light shrink-0" />
                    <div className="min-w-0">
                      <div className="font-medium text-white">Campaign Dossier (.md)</div>
                      <div className="text-[11px] text-gray-400 truncate">
                        Formatted Markdown document with tables
                      </div>
                    </div>
                  </button>

                  <button
                    id="export-data-json-btn"
                    onClick={handleExportJson}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs hover:bg-surface-elevated text-gray-200 hover:text-white flex items-center gap-3 transition-colors"
                  >
                    <FileCode className="w-4 h-4 text-brand-purple-light shrink-0" />
                    <div className="min-w-0">
                      <div className="font-medium text-white">Campaign Data (.json)</div>
                      <div className="text-[11px] text-gray-400 truncate">
                        Structured machine-readable JSON export
                      </div>
                    </div>
                  </button>

                  <button
                    id="copy-dossier-clipboard-btn"
                    onClick={handleCopyDossier}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs hover:bg-surface-elevated text-gray-200 hover:text-white flex items-center gap-3 transition-colors"
                  >
                    {copiedDossier ? (
                      <Check className="w-4 h-4 text-green-400 shrink-0" />
                    ) : (
                      <Copy className="w-4 h-4 text-brand-amber shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="font-medium text-white">
                        {copiedDossier ? 'Copied to Clipboard!' : 'Copy Dossier to Clipboard'}
                      </div>
                      <div className="text-[11px] text-gray-400 truncate">
                        Instant clipboard copy for reports
                      </div>
                    </div>
                  </button>
                </div>

                <div className="pt-2 pb-1 px-3 border-t border-surface-border text-[10px] text-gray-500 flex items-center justify-between">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Edited state preserved
                  </span>
                  <span>v1.0 Ready</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Workspace Tabs with Status Indicators */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        {TABS.map(({ id, label, icon: Icon, key }) => {
          const isActive = activeTab === id
          let isComplete = false
          let statusText = ''

          if (id === 'overview') {
            isComplete = true
            statusText = 'Ready'
          } else if (id === 'poster') {
            isComplete = assetStatus.poster
            statusText = isComplete ? 'Ready' : 'Draft'
          } else if (id === 'storyboard') {
            isComplete = assetStatus.storyboard
            const count = assets.storyboard?.scenes?.length || 0
            statusText = isComplete ? `${count} Scenes` : 'Draft'
          } else if (id === 'social') {
            isComplete = assetStatus.social
            statusText = isComplete ? 'Ready' : 'Draft'
          }

          return (
            <button
              key={id}
              id={`tab-${id}`}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium whitespace-nowrap transition-all duration-200 border ${
                isActive
                  ? 'bg-gradient-to-r from-brand-purple to-brand-cyan text-white border-transparent shadow-brand-sm'
                  : 'bg-surface-card border-surface-border text-gray-400 hover:text-white hover:border-surface-border-light'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>

              {/* Status pill on tab */}
              <span
                className={`ml-1 text-[10px] font-semibold px-2 py-0.5 rounded-full transition-colors ${
                  isActive
                    ? 'bg-black/30 text-white'
                    : isComplete
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                    : 'bg-surface-elevated text-gray-500 border border-surface-border'
                }`}
              >
                {statusText}
              </span>
            </button>
          )
        })}
      </div>

      {/* Tab Panels (Shared Campaign State & Unified Context) */}
      <main className="min-h-[500px]">
        {activeTab === 'overview' && (
          <CampaignOverview
            campaign={campaign}
            onUpdateCampaign={handleUpdateCampaign}
          />
        )}

        {activeTab === 'poster' && (
          <PosterStudio
            campaign={campaign}
            initialPoster={assets.poster}
            onPosterGenerated={handlePosterGenerated}
          />
        )}

        {activeTab === 'storyboard' && (
          <StoryboardStudio
            campaign={campaign}
            initialStoryboard={assets.storyboard}
            onStoryboardGenerated={handleStoryboardGenerated}
          />
        )}

        {activeTab === 'social' && (
          <SocialStudio
            campaign={campaign}
            initialSocial={assets.social}
            onSocialGenerated={handleSocialGenerated}
          />
        )}
      </main>
    </div>
  )
}
