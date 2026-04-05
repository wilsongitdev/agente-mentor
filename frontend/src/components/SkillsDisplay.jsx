import { motion } from 'framer-motion'
import { Zap, TrendingUp, Star } from 'lucide-react'

const LEVEL_CONFIG = {
  beginner:     { color: 'bg-blue-500/10 dark:bg-blue-500/20 text-blue-600 dark:text-blue-300 border-blue-200 dark:border-blue-500/30',     dots: 1 },
  intermediate: { color: 'bg-amber-500/10 dark:bg-yellow-500/20 text-amber-600 dark:text-yellow-300 border-amber-200 dark:border-yellow-500/30', dots: 2 },
  advanced:     { color: 'bg-orange-500/10 dark:bg-orange-500/20 text-orange-600 dark:text-orange-300 border-orange-200 dark:border-orange-500/30', dots: 3 },
  expert:       { color: 'bg-green-500/10 dark:bg-green-500/20 text-green-600 dark:text-green-300 border-green-200 dark:border-green-500/30',   dots: 4 },
}

const PRIORITY_CONFIG = {
  high:   { color: 'bg-red-500/10 dark:bg-red-500/20 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/30',    label: 'Alta prioridad' },
  medium: { color: 'bg-amber-500/10 dark:bg-yellow-500/20 text-amber-600 dark:text-yellow-300 border-amber-200 dark:border-yellow-500/30', label: 'Media prioridad' },
  low:    { color: 'bg-slate-500/10 dark:bg-slate-500/20 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-500/30',  label: 'Baja prioridad' },
}

function SkillBadge({ skill }) {
  const cfg = LEVEL_CONFIG[skill.level] || LEVEL_CONFIG.intermediate
  return (
    <motion.div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${cfg.color}`}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <span className="flex gap-0.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <span
            key={i}
            className={`w-1.5 h-1.5 rounded-full ${i < cfg.dots ? 'bg-current' : 'bg-current opacity-20'}`}
          />
        ))}
      </span>
      {skill.name}
    </motion.div>
  )
}

function SuggestedSkillCard({ skill }) {
  const cfg = PRIORITY_CONFIG[skill.priority] || PRIORITY_CONFIG.medium
  return (
    <motion.div
      className="glass rounded-xl p-4 flex flex-col gap-2"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold text-slate-900">{skill.name}</span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${cfg.color}`}>
          {cfg.label}
        </span>
      </div>
      <p className="text-sm text-slate-600">{skill.reason}</p>
    </motion.div>
  )
}

export default function SkillsDisplay({ currentSkills = [], suggestedSkills = [], seniority, candidateName }) {
  const categories = [...new Set(currentSkills.map((s) => s.category))].sort()

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="glass rounded-2xl p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-brand-600/20 flex items-center justify-center text-2xl shrink-0">
          👤
        </div>
        <div>
          {candidateName && (
            <h2 className="text-2xl font-bold gradient-text">{candidateName}</h2>
          )}
          <div className="flex items-center gap-2 mt-1">
            <Star className="w-4 h-4 text-amber-500 dark:text-yellow-400" />
            <span className="text-slate-600 dark:text-slate-300 font-medium capitalize text-sm">
              Nivel: <span className="text-amber-600 dark:text-yellow-300">{seniority}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Current skills by category */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-5 h-5 text-brand-600" />
          <h3 className="text-lg font-bold text-slate-950">
            Habilidades actuales ({currentSkills.length})
          </h3>
        </div>
        <div className="glass rounded-2xl p-6 flex flex-col gap-5">
          {categories.map((cat) => (
            <div key={cat}>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {cat}
              </p>
              <div className="flex flex-wrap gap-2">
                {currentSkills
                  .filter((s) => s.category === cat)
                  .map((skill, i) => (
                    <SkillBadge key={i} skill={skill} />
                  ))}
              </div>
            </div>
          ))}
          {currentSkills.length === 0 && (
            <p className="text-slate-400 text-sm">No se detectaron habilidades.</p>
          )}
        </div>
        {/* Legend */}
        <div className="flex flex-wrap gap-4 mt-3 px-1">
          {Object.entries(LEVEL_CONFIG).map(([level, cfg]) => (
            <div key={level} className="flex items-center gap-1.5">
              <span className={`text-xs px-2 py-0.5 rounded-full border ${cfg.color}`}>
                {level}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Suggested skills */}
      {suggestedSkills.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-bold text-slate-950">
              Habilidades recomendadas ({suggestedSkills.length})
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {suggestedSkills.map((skill, i) => (
              <SuggestedSkillCard key={i} skill={skill} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
