export default function StatsCard({ icon: Icon, label, value, color = 'purple' }) {
  const colorMap = {
    purple: 'from-brand-purple/20 to-brand-purple/5 border-brand-purple/30 text-brand-purple-light',
    cyan: 'from-brand-cyan/20 to-brand-cyan/5 border-brand-cyan/30 text-brand-cyan-light',
    amber: 'from-brand-amber/20 to-brand-amber/5 border-brand-amber/30 text-brand-amber',
  }

  return (
    <div className={`card p-5 bg-gradient-to-br ${colorMap[color]} animate-fade-in`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center ${
          color === 'purple' ? 'from-brand-purple/30 to-brand-purple/10' :
          color === 'cyan'   ? 'from-brand-cyan/30 to-brand-cyan/10' :
                               'from-brand-amber/30 to-brand-amber/10'
        }`}>
          <Icon className={`w-6 h-6 ${
            color === 'purple' ? 'text-brand-purple-light' :
            color === 'cyan'   ? 'text-brand-cyan-light' :
                                 'text-brand-amber'
          }`} />
        </div>
      </div>
    </div>
  )
}
