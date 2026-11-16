import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, PlusCircle, FolderOpen, TrendingUp, Image, FileText, Zap, AlertCircle } from 'lucide-react'
import { getProjects, deleteProject } from '../services/api'
import { getSessionId } from '../services/session'
import { useAuth } from '../context/AuthContext'
import ProjectCard from '../components/dashboard/ProjectCard'
import StatsCard from '../components/dashboard/StatsCard'

export default function Dashboard() {
  const { user } = useAuth()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const sessionId = getSessionId()

  useEffect(() => {
    fetchProjects()
  }, [user])

  async function fetchProjects() {
    try {
      setLoading(true)
      setError(null)
      const data = await getProjects(sessionId)
      if (data?.projects && Array.isArray(data.projects) && data.projects.length > 0) {
        setProjects(data.projects)
        return
      }

      // Check session fallback for demo/offline workspace (guest mode only)
      if (!user) {
        const local = sessionStorage.getItem('createx_campaign_local') || sessionStorage.getItem('campaign_local')
        if (local) {
          try {
            const c = JSON.parse(local)
            setProjects([
              {
                id: 'local',
                title: c.campaign_name || 'Active Campaign',
                original_idea: c.original_idea || c.description || 'Active session campaign project',
                industry: c.industry || 'General',
                created_at: new Date().toISOString(),
                tone: c.tone || c.writing_tone,
                campaign_data: c,
              },
            ])
            return
          } catch {
            setProjects([])
          }
        } else {
          setProjects([])
        }
      } else {
        setProjects([])
      }
    } catch (err) {
      // Supabase query failed — check session fallback in guest mode
      if (!user) {
        const local = sessionStorage.getItem('createx_campaign_local') || sessionStorage.getItem('campaign_local')
        if (local) {
          try {
            const c = JSON.parse(local)
            setProjects([
              {
                id: 'local',
                title: c.campaign_name || 'Active Campaign',
                original_idea: c.original_idea || c.description || 'Active session campaign project',
                industry: c.industry || 'General',
                created_at: new Date().toISOString(),
                tone: c.tone || c.writing_tone,
                campaign_data: c,
              },
            ])
            return
          } catch {
            setProjects([])
          }
        }
      }
      setProjects([])
      // Only set visible error if neither remote nor local projects exist
      setError(err.message || 'Could not connect to project database.')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(projectId) {
    if (!confirm('Delete this project? This cannot be undone.')) return
    try {
      if (projectId === 'local') {
        sessionStorage.removeItem('createx_campaign_local')
        sessionStorage.removeItem('campaign_local')
        sessionStorage.removeItem('assets_local')
        setProjects([])
        return
      }
      await deleteProject(projectId)
      setProjects(prev => prev.filter(p => p.id !== projectId))
    } catch (err) {
      alert(`Failed to delete: ${err.message}`)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-purple/20 via-surface-elevated to-brand-cyan/10 border border-surface-border p-10 mb-10">
        {/* Background glow */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-purple/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-brand-cyan/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-4">
            <span className="badge-purple">
              <Sparkles className="w-3 h-3 mr-1" />
              AI Creative Studio
            </span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white leading-tight mb-3">
            One Idea.<br />
            <span className="gradient-text">Multiple Creative</span> Possibilities.
          </h1>
          <p className="text-gray-400 text-lg max-w-xl leading-relaxed">
            Transform your ideas into complete campaign packages — posters, storyboards, and social content, all sharing the same brand identity.
          </p>
          <div className="flex flex-wrap gap-3 mt-8">
            <Link to="/create" className="btn-primary">
              <PlusCircle className="w-4 h-4" />
              Create New Campaign
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="btn-secondary"
            >
              <Zap className="w-4 h-4" />
              API Docs
            </a>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <StatsCard icon={FolderOpen}   label="Campaigns Created" value={projects.length} color="purple" />
        <StatsCard icon={Image}        label="Posters Generated"  value={projects.filter(p => p.campaign_data).length} color="cyan" />
        <StatsCard icon={TrendingUp}   label="Assets Created"     value={projects.length * 4} color="amber" />
      </div>

      {/* Recent Projects */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Recent Projects</h2>
          <p className="section-subtitle">Your latest creative campaigns</p>
        </div>
        {projects.length > 0 && (
          <Link to="/create" className="btn-secondary text-xs px-4 py-2">
            <PlusCircle className="w-3.5 h-3.5" />
            New
          </Link>
        )}
      </div>

      {/* Error notification if failed to fetch */}
      {error && !loading && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchProjects}
            className="text-xs font-medium text-red-200 underline hover:text-white transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton h-36 rounded-2xl" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        /* Empty state */
        <div data-testid="dashboard-empty-state" className="card p-12 sm:p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand-purple/20 border border-brand-purple/30 flex items-center justify-center mx-auto mb-5 shadow-brand-sm">
            <Sparkles className="w-8 h-8 text-brand-purple-light" />
          </div>

          {user ? (
            /* Authenticated Cloud Empty State */
            <div data-testid="cloud-empty-state">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-purple/10 border border-brand-purple/30 text-brand-purple-light text-xs font-medium mb-3">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Cloud Workspace Active ({user.email})
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">No cloud campaigns yet</h3>
              <p className="text-gray-400 mb-6 max-w-md mx-auto text-sm leading-relaxed">
                Your cloud workspace is ready. Launch your first project to save posters, storyboards, and social content securely across devices.
              </p>
              <Link to="/create" className="btn-primary mx-auto">
                <PlusCircle className="w-4 h-4" />
                Create Your First Cloud Campaign
              </Link>
            </div>
          ) : (
            /* Guest Empty State */
            <div data-testid="guest-empty-state">
              <h3 className="text-xl font-semibold text-white mb-2">No campaigns yet</h3>
              <p className="text-gray-500 mb-6 max-w-sm mx-auto text-sm">
                Create your first AI campaign and watch your idea transform into a complete creative package.
              </p>
              <Link to="/create" className="btn-primary mx-auto">
                <PlusCircle className="w-4 h-4" />
                Create Your First Campaign
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(project => (
            <ProjectCard key={project.id} project={project} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {/* Quick Actions */}
      <div className="mt-12">
        <h2 className="section-title mb-6">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { icon: Sparkles, label: 'Campaign Generator', desc: 'Generate full campaign concepts', to: '/create', color: 'purple' },
            { icon: Image,     label: 'Poster Studio',     desc: 'Create AI promotional posters', to: '/create', color: 'cyan' },
            { icon: FileText,  label: 'Social Assistant',  desc: 'Platform-optimized content', to: '/create', color: 'amber' },
          ].map(({ icon: Icon, label, desc, to, color }) => (
            <Link
              key={label}
              to={to}
              className="card-hover p-6 flex items-start gap-4 group"
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                color === 'purple' ? 'bg-brand-purple/20 text-brand-purple-light' :
                color === 'cyan'   ? 'bg-brand-cyan/20 text-brand-cyan-light' :
                                     'bg-brand-amber/20 text-brand-amber'
              }`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="font-semibold text-white text-sm">{label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
