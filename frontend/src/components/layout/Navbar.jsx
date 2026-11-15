import { Link, useLocation } from 'react-router-dom'
import { Sparkles, LayoutDashboard, PlusCircle, Zap } from 'lucide-react'

export default function Navbar() {
  const location = useLocation()

  const navLinks = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/create', label: 'Create', icon: PlusCircle },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-surface-border bg-surface-base/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-full flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-brand-purple to-brand-cyan flex items-center justify-center shadow-brand-sm group-hover:shadow-brand transition-shadow duration-300">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold text-white">
            Create<span className="gradient-text">X</span>
          </span>
          <span className="hidden sm:block text-xs font-medium text-gray-500 mt-0.5">AI</span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {navLinks.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to))
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  active
                    ? 'bg-brand-purple/20 text-brand-purple-light'
                    : 'text-gray-400 hover:text-white hover:bg-surface-card'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            )
          })}
        </div>

        {/* CTA */}
        <Link to="/create" className="btn-primary text-xs px-4 py-2">
          <Zap className="w-3.5 h-3.5" />
          New Campaign
        </Link>
      </div>
    </nav>
  )
}
