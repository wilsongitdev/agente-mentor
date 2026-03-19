import { motion } from 'framer-motion'
import { BookOpen, Clock, ExternalLink, ChevronRight, Award } from 'lucide-react'

const PHASE_CONFIG = {
  Foundations:    { color: 'from-blue-600 to-cyan-500',    icon: '🏗️', bg: 'bg-blue-500/10 border-blue-500/20' },
  'Core Skills':  { color: 'from-brand-600 to-purple-500', icon: '⚡', bg: 'bg-brand-500/10 border-brand-500/20' },
  Specialisation: { color: 'from-orange-500 to-yellow-500', icon: '🎯', bg: 'bg-orange-500/10 border-orange-500/20' },
  Advanced:       { color: 'from-red-500 to-pink-500',     icon: '🚀', bg: 'bg-red-500/10 border-red-500/20' },
}

const LEVEL_COLORS = {
  beginner:     'text-blue-300 bg-blue-500/10',
  intermediate: 'text-yellow-300 bg-yellow-500/10',
  advanced:     'text-orange-300 bg-orange-500/10',
}

function CourseCard({ step, isLast }) {
  const phase = PHASE_CONFIG[step.phase] || PHASE_CONFIG['Core Skills']
  const course = step.course || {}

  return (
    <motion.div
      className="relative flex gap-4 sm:gap-6"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: step.step * 0.07 }}
    >
      {/* Timeline */}
      <div className="flex flex-col items-center">
        <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${phase.color} flex items-center justify-center text-white font-bold text-sm shadow-lg shrink-0`}>
          {step.step}
        </div>
        {!isLast && (
          <div className="w-0.5 flex-1 mt-2 bg-gradient-to-b from-slate-600 to-transparent min-h-[40px]" />
        )}
      </div>

      {/* Card */}
      <div className={`flex-1 glass rounded-2xl p-5 mb-4 border ${phase.bg}`}>
        {/* Phase badge */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-base">{phase.icon}</span>
          <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
            {step.phase}
          </span>
        </div>

        <h4 className="text-base font-bold text-slate-100 leading-snug mb-1">
          {course.title}
        </h4>

        <div className="flex flex-wrap items-center gap-3 mb-3">
          <span className="text-xs text-slate-400 font-medium">{course.provider}</span>
          {course.level && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${LEVEL_COLORS[course.level] || LEVEL_COLORS.intermediate}`}>
              {course.level}
            </span>
          )}
          {course.duration_hours && (
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3" />
              {course.duration_hours}h
            </span>
          )}
          {step.estimated_weeks && (
            <span className="text-xs text-slate-500">
              ~{step.estimated_weeks} semanas
            </span>
          )}
          {course.rating && (
            <span className="flex items-center gap-1 text-xs text-yellow-400">
              ★ {course.rating}
            </span>
          )}
        </div>

        <p className="text-sm text-slate-400 leading-relaxed mb-3">
          {step.rationale}
        </p>

        {course.skills_covered?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {course.skills_covered.slice(0, 5).map((skill, i) => (
              <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-300">
                {skill}
              </span>
            ))}
          </div>
        )}

        {course.url && (
          <a
            href={course.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-medium transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Ver curso
          </a>
        )}
      </div>
    </motion.div>
  )
}

export default function LearningPath({ learningPath }) {
  if (!learningPath) return null

  const {
    steps = [],
    executive_summary,
    total_duration_hours,
    total_estimated_weeks,
    seniority_level,
  } = learningPath

  // Group steps by phase for stats
  const phases = [...new Set(steps.map((s) => s.phase))]

  return (
    <div className="flex flex-col gap-8">
      {/* Summary card */}
      <motion.div
        className="glass rounded-2xl p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-3 mb-4">
          <Award className="w-6 h-6 text-brand-400" />
          <h3 className="text-xl font-bold gradient-text">Tu Learning Path personalizado</h3>
        </div>

        {executive_summary && (
          <p className="text-slate-300 leading-relaxed mb-5">{executive_summary}</p>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Cursos', value: steps.length, icon: '📚' },
            { label: 'Horas', value: `${total_duration_hours}h`, icon: '⏱️' },
            { label: 'Semanas', value: `~${total_estimated_weeks}`, icon: '📅' },
            { label: 'Nivel objetivo', value: seniority_level, icon: '🎯' },
          ].map((stat) => (
            <div key={stat.label} className="bg-slate-800/60 rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">{stat.icon}</div>
              <div className="text-lg font-bold text-slate-100">{stat.value}</div>
              <div className="text-xs text-slate-400">{stat.label}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Phase pills */}
      <div className="flex flex-wrap gap-2">
        {phases.map((phase) => {
          const cfg = PHASE_CONFIG[phase] || PHASE_CONFIG['Core Skills']
          return (
            <span
              key={phase}
              className={`flex items-center gap-1.5 text-sm px-3 py-1 rounded-full border ${cfg.bg} text-slate-200 font-medium`}
            >
              {cfg.icon} {phase}
            </span>
          )
        })}
      </div>

      {/* Steps timeline */}
      <div>
        <div className="flex items-center gap-2 mb-6">
          <BookOpen className="w-5 h-5 text-brand-400" />
          <h3 className="text-lg font-bold text-slate-100">Roadmap paso a paso</h3>
        </div>
        <div>
          {steps.map((step, i) => (
            <CourseCard key={step.step} step={step} isLast={i === steps.length - 1} />
          ))}
        </div>
      </div>
    </div>
  )
}
