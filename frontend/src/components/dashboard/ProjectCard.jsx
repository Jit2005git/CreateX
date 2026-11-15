import { Link } from 'react-router-dom'
import { Trash2, ExternalLink, Clock, Tag } from 'lucide-react'

function timeAgo(dateString) {
  const diff = Date.now() - new Date(dateString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function ProjectCard({ project, onDelete }) {
  return (
    <div className="card-hover group relative overflow-hidden p-5 animate-fade-in">
      {/* Accent stripe */}
      <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-brand-purple to-brand-cyan rounded-l-2xl" />

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white text-sm truncate group-hover:gradient-text transition-all duration-300">
            {project.title}
          </h3>
          <p className="text-xs text-gray-500 mt-1 line-clamp-2 leading-relaxed">
            {project.original_idea}
          </p>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 shrink-0">
          <Link
            to={`/workspace/${project.id}`}
            className="p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-surface-elevated transition-all duration-200"
            title="Open workspace"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
          {onDelete && (
            <button
              onClick={() => onDelete(project.id)}
              className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-900/20 transition-all duration-200"
              title="Delete project"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="flex items-center gap-3 mt-4 flex-wrap">
        {project.industry && (
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <Tag className="w-3 h-3" />
            {project.industry}
          </span>
        )}
        <span className="flex items-center gap-1 text-xs text-gray-600">
          <Clock className="w-3 h-3" />
          {timeAgo(project.created_at)}
        </span>
        {project.tone && (
          <span className="badge-purple text-xs">{project.tone}</span>
        )}
      </div>
    </div>
  )
}
