import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, PlusCircle, User, LogIn, LogOut, ChevronUp, Sparkles, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export default function MobileNav({ onOpenAuth }) {
  const location = useLocation()
  const { user, signOut } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const drawerRef = useRef(null)

  // Close drawer when route changes
  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

  // Close drawer on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (drawerRef.current && !drawerRef.current.contains(event.target)) {
        setDrawerOpen(false)
      }
    }
    if (drawerOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [drawerOpen])

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U'
  const userDisplayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'

  const isDashboard = location.pathname === '/'
  const isCreate = location.pathname === '/create'

  return (
    <>
      {/* Mobile Account Drawer Backdrop */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm sm:hidden animate-fade-in"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Mobile Account Bottom Drawer */}
      {drawerOpen && (
        <div
          ref={drawerRef}
          className="fixed bottom-16 left-0 right-0 z-40 sm:hidden bg-surface-card border-t border-surface-border rounded-t-2xl p-5 shadow-card-hover animate-slide-up"
        >
          <div className="flex items-center justify-between pb-3 border-b border-surface-border mb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-purple to-brand-cyan flex items-center justify-center text-white font-bold text-sm shadow-brand-sm">
                {userInitial}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-white truncate">{userDisplayName}</p>
                <p className="text-xs text-gray-400 truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={() => setDrawerOpen(false)}
              className="p-1 rounded-lg text-gray-400 hover:text-white"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="mb-4">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-purple/20 text-brand-purple-light text-xs font-medium">
              <Sparkles className="w-3 h-3" />
              Cloud Account Active
            </span>
          </div>

          <button
            onClick={async () => {
              setDrawerOpen(false)
              await signOut()
            }}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-xs font-semibold text-red-400 border border-red-900/40 bg-red-900/10 hover:bg-red-900/20 active:scale-[0.98] transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      )}

      {/* Mobile Bottom Navigation Bar */}
      <nav
        aria-label="Mobile Navigation"
        className="fixed bottom-0 left-0 right-0 z-30 sm:hidden h-16 bg-surface-base/95 backdrop-blur-xl border-t border-surface-border px-6 flex items-center justify-between pb-[env(safe-area-inset-bottom,0px)]"
      >
        {/* Dashboard Link */}
        <Link
          to="/"
          aria-label="Dashboard"
          aria-current={isDashboard ? 'page' : undefined}
          className={`flex flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${
            isDashboard ? 'text-brand-purple-light' : 'text-gray-400 hover:text-white'
          }`}
        >
          <div className={`p-1 rounded-lg ${isDashboard ? 'bg-brand-purple/20' : ''}`}>
            <LayoutDashboard className="w-5 h-5" />
          </div>
          <span>Dashboard</span>
        </Link>

        {/* Create Campaign (Elevated Center CTA) */}
        <Link
          to="/create"
          aria-label="Create Campaign"
          aria-current={isCreate ? 'page' : undefined}
          className="flex flex-col items-center justify-center -mt-4 group"
        >
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-purple to-brand-cyan flex items-center justify-center shadow-brand text-white transition-transform group-active:scale-95">
            <PlusCircle className="w-6 h-6" />
          </div>
          <span className={`text-[10px] font-medium mt-1 ${isCreate ? 'text-brand-cyan' : 'text-gray-400'}`}>
            Create
          </span>
        </Link>

        {/* Account / Auth Action */}
        {user ? (
          <button
            onClick={() => setDrawerOpen((prev) => !prev)}
            aria-label="User Account Menu"
            className={`flex flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${
              drawerOpen ? 'text-brand-purple-light' : 'text-gray-400 hover:text-white'
            }`}
          >
            <div className={`p-1 rounded-lg ${drawerOpen ? 'bg-brand-purple/20' : ''}`}>
              <div className="w-5 h-5 rounded-md bg-gradient-to-br from-brand-purple to-brand-cyan flex items-center justify-center text-white text-[10px] font-bold">
                {userInitial}
              </div>
            </div>
            <span>Account</span>
          </button>
        ) : (
          <button
            onClick={() => onOpenAuth('signin')}
            aria-label="Sign In"
            className="flex flex-col items-center justify-center gap-1 text-[11px] font-medium text-gray-400 hover:text-white transition-colors"
          >
            <div className="p-1 rounded-lg">
              <LogIn className="w-5 h-5 text-brand-purple-light" />
            </div>
            <span>Sign In</span>
          </button>
        )}
      </nav>
    </>
  )
}
