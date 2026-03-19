import { useState } from 'react'
import { useLocation, useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Cpu, Map } from 'lucide-react'
import SkillsDisplay from '../components/SkillsDisplay'
import LearningPath from '../components/LearningPath'

const TABS = [
  { id: 'skills', label: 'Habilidades', icon: Cpu },
  { id: 'path', label: 'Learning Path', icon: Map },
]

export default function ResultsPage() {
  const { state } = useLocation()
  const { sessionId } = useParams()
  const [activeTab, setActiveTab] = useState('skills')

  const learningPath = state?.learningPath

  if (!learningPath) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-6 px-6">
        <p className="text-slate-400 text-center">
          No se encontraron resultados para la sesión{' '}
          <code className="text-brand-300">{sessionId}</code>.
        </p>
        <Link
          to="/"
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al inicio
        </Link>
      </div>
    )
  }

  const { current_skills, suggested_skills, seniority_level, candidate_name } = learningPath

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-slate-950/80 backdrop-blur border-b border-white/5">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Nuevo análisis
          </Link>
          <span className="text-xs text-slate-600 font-mono hidden sm:block">{sessionId}</span>
        </div>

        {/* Tabs */}
        <div className="max-w-4xl mx-auto px-6 flex gap-1 pb-0">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-brand-500 text-brand-300'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-10">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === 'skills' ? (
            <SkillsDisplay
              currentSkills={current_skills}
              suggestedSkills={suggested_skills}
              seniority={seniority_level}
              candidateName={candidate_name}
            />
          ) : (
            <LearningPath learningPath={learningPath} />
          )}
        </motion.div>
      </div>
    </div>
  )
}
