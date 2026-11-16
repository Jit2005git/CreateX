import { createContext, useContext, useState, useEffect } from 'react'
import { supabase, isSupabaseConfigured, setAccessToken } from '../services/supabase'

const AuthContext = createContext({
  user: null,
  session: null,
  loading: true,
  isConfigured: false,
  error: null,
  signUp: async () => {},
  signIn: async () => {},
  signOut: async () => {},
  clearError: () => {},
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const configured = isSupabaseConfigured()

  useEffect(() => {
    if (!configured || !supabase) {
      setLoading(false)
      return
    }

    // 1. Restore existing session on mount
    supabase.auth.getSession().then(({ data: { session }, error }) => {
      if (error) {
        console.warn('Session restoration notice:', error.message)
      }
      setSession(session)
      setUser(session?.user ?? null)
      setAccessToken(session?.access_token ?? null)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })

    // 2. Listen to live auth state changes (sign in, sign out, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, currentSession) => {
        setSession(currentSession)
        setUser(currentSession?.user ?? null)
        setAccessToken(currentSession?.access_token ?? null)
        setLoading(false)
      }
    )

    return () => {
      subscription?.unsubscribe()
    }
  }, [configured])

  const signUp = async ({ email, password, fullName }) => {
    setError(null)
    if (!configured || !supabase) {
      throw new Error('Supabase Auth is not configured.')
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName || '',
        },
      },
    })

    if (error) {
      setError(error.message)
      throw error
    }

    return data
  }

  const signIn = async ({ email, password }) => {
    setError(null)
    if (!configured || !supabase) {
      throw new Error('Supabase Auth is not configured.')
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setError(error.message)
      throw error
    }

    // Immediate token sync
    if (data?.session) {
      setSession(data.session)
      setUser(data.session.user)
      setAccessToken(data.session.access_token)
    }

    return data
  }

  const signOut = async () => {
    setError(null)
    if (configured && supabase) {
      const { error } = await supabase.auth.signOut()
      if (error) {
        console.warn('Sign out notice:', error.message)
      }
    }
    setSession(null)
    setUser(null)
    setAccessToken(null)
  }

  const clearError = () => setError(null)

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isConfigured: configured,
        error,
        signUp,
        signIn,
        signOut,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
