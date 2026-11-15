import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Sparkles, Image, Film, Share2, AlertCircle } from 'lucide-react'
import { getProject } from '../services/api'
import CampaignOverview from '../components/workspace/CampaignOverview'
import PosterStudio from '../components/workspace/PosterStudio'
import StoryboardStudio from '../components/workspace/StoryboardStudio'
import SocialStudio from '../components/workspace/SocialStudio'

const TABS = [
  { id: 'overview',   label: 'Campaign',  icon: Sparkles },
  { id: 'poster',     label: 'Poster',    icon: Image },
  { id: 'storyboard', label: 'Storyboard', icon: Film },
  { id: 'social',     label: 'Social',    icon: Share2 },
]

export default function Workspace() {
  const { projectId } = useParams()
  const [campaign, setCampaign] = useState(null)
  const [assets, setAssets] = useState({})
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadWorkspace()
  }, [projectId])

  async function loadWorkspace() {
    try {
      setLoading(true)

      // 1. Try sessionStorage first (just created)
      const cached = sessionStorage.getItem(`campaign_${projectId}`)
      if (cached) {
        setCampaign(JSON.parse(cached))
        setLoading(false)
        return
      }

      // 2. Fall back to local-only key (Supabase not configured)
      const local = sessionStorage.getItem('createx_campaign_local')
      if (local && projectId === 'local') {
        setCampaign(JSON.parse(local))
        setLoading(false)
        return
      }

      // 3. Try fetching from backend/Supabase
      const data = await getProject(projectId)
      if (data.campaign_data) {
        setCampaign(data.campaign_data)
      } else {
        throw new Error('Campaign data not found in project.')
      }

      // Extract previously generated assets
      const assetMap = {}
      ;(data.assets || []).forEach(a => { assetMap[a.asset_type] = a.content || a })
      setAssets(assetMap)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-6">
        <div className="skeleton h-10 w-48 rounded-xl" />
        <div className="skeleton h-16 w-full rounded-2xl" />
        <div className="grid grid-cols-4 gap-3">
          {[1,2,3,4].map(i => <div key={i} className="skeleton h-10 rounded-xl" />)}
        </div>
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-20 text-center">
        <div className="card p-10">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Workspace not found</h2>
          <p className="text-gray-400 text-sm mb-6">{error || 'Could not load campaign data.'}</p>
          <Link to="/create" className="btn-primary">
            <Sparkles className="w-4 h-4" />
            Create New Campaign
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Back + header */}
      <div className="flex items-start gap-4 mb-8">
        <Link to="/" className="btn-ghost mt-1">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-white truncate">{campaign.campaign_name}</h1>
          <p className="text-gray-500 text-sm mt-0.5 italic">"{campaign.tagline}"</p>
        </div>
        {/* Brand color mini-palette */}
        <div className="hidden sm:flex items-center gap-1.5 mt-1">
          {Object.values(campaign.brand_colors || {}).filter(Boolean).map((color, i) => (
            <div key={i} className="w-6 h-6 rounded-full border-2 border-white/10" style={{ backgroundColor: color }} title={color} />
          ))}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 mb-8 overflow-x-auto pb-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`tab-${id}`}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200 ${
              activeTab === id
                ? 'bg-gradient-to-r from-brand-purple to-brand-cyan text-white shadow-brand-sm'
                : 'bg-surface-card border border-surface-border text-gray-400 hover:text-white hover:border-surface-border-light'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'overview'   && <CampaignOverview campaign={campaign} />}
        {activeTab === 'poster'     && <PosterStudio     campaign={campaign} initialPoster={assets.poster} />}
        {activeTab === 'storyboard' && <StoryboardStudio campaign={campaign} initialStoryboard={assets.storyboard} />}
        {activeTab === 'social'     && <SocialStudio     campaign={campaign} initialSocial={assets.social} />}
      </div>
    </div>
  )
}
