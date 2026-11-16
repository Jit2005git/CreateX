import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Sparkles, LayoutDashboard, PlusCircle, Zap, User, LogOut, LogIn, ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import AuthModal from '../auth/AuthModal'
import MobileNav from './MobileNav'

export default function Navbar() {
  const location = useLocation()
  const { user, signOut } = useAuth()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState('signin')
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef(null)

  const navLinks = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/create', label: 'Create', icon: PlusCircle },
  ]

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleOpenAuth = (mode = 'signin') => {
    setAuthModalMode(mode)
    setAuthModalOpen(true)
    setUserMenuOpen(false)
  }

  const handleSignOut = async () => {
    setUserMenuOpen(false)
    await signOut()
  }

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U'
  const userDisplayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-40 h-16 border-b border-surface-border bg-surface-base/80 backdrop-blur-xl">
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

          {/* Actions & User Menu */}
          <div className="flex items-center gap-3">
            {/* CTA */}
            <Link to="/create" className="btn-primary text-xs px-4 py-2">
              <Zap className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Campaign</span>
            </Link>

            {/* Auth Button or User Menu */}
            {user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen((prev) => !prev)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-surface-border bg-surface-card hover:bg-surface-elevated transition-colors text-xs text-white"
                  aria-label="User account menu"
                >
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-brand-purple to-brand-cyan flex items-center justify-center text-white font-bold text-xs">
                    {userInitial}
                  </div>
                  <span className="hidden sm:inline font-medium max-w-[120px] truncate">
                    {userDisplayName}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-surface-card border border-surface-border rounded-xl shadow-card-hover p-2 animate-slide-up z-50">
                    <div className="px-3 py-2 border-b border-surface-border mb-1">
                      <p className="text-xs font-semibold text-white truncate">{userDisplayName}</p>
                      <p className="text-[11px] text-gray-400 truncate">{user.email}</p>
                      <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-brand-purple/20 text-brand-purple-light text-[10px] font-medium">
                        Cloud Account
                      </span>
                    </div>

                    <button
                      onClick={handleSignOut}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-400 hover:text-red-300 hover:bg-red-900/20 transition-colors"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => handleOpenAuth('signin')}
                className="btn-secondary text-xs px-3.5 py-2"
              >
                <LogIn className="w-3.5 h-3.5 text-brand-purple-light" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile Bottom Navigation */}
      <MobileNav onOpenAuth={handleOpenAuth} />

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </>
  )
}
