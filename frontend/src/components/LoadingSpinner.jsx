import { motion } from 'framer-motion'

const STEPS = [
  { label: 'Extrayendo texto del PDF', icon: '📄' },
  { label: 'Analizando habilidades con IA', icon: '🧠' },
  { label: 'Buscando cursos relevantes', icon: '🔍' },
  { label: 'Generando tu Learning Path', icon: '🗺️' },
]

export default function LoadingSpinner({ currentStatus = 'processing' }) {
  const stepIndex =
    currentStatus === 'processing' ? Math.floor(Date.now() / 4000) % STEPS.length : 3

  return (
    <div className="flex flex-col items-center justify-center py-20 gap-10">
      {/* Animated ring */}
      <div className="relative w-24 h-24">
        <motion.div
          className="absolute inset-0 rounded-full border-4 border-brand-600 border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        <div className="absolute inset-2 rounded-full bg-brand-900/30 flex items-center justify-center text-3xl">
          {STEPS[stepIndex % STEPS.length].icon}
        </div>
      </div>

      {/* Steps */}
      <div className="flex flex-col gap-3 w-full max-w-sm">
        {STEPS.map((step, idx) => (
          <motion.div
            key={idx}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
              idx === stepIndex % STEPS.length
                ? 'bg-brand-600/20 border border-brand-500/50 text-brand-300'
                : idx < stepIndex % STEPS.length
                ? 'text-slate-400 line-through'
                : 'text-slate-600'
            }`}
            animate={idx === stepIndex % STEPS.length ? { scale: [1, 1.02, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <span className="text-lg">{step.icon}</span>
            <span className="text-sm font-medium">{step.label}</span>
            {idx < stepIndex % STEPS.length && (
              <span className="ml-auto text-green-400 text-xs">✓</span>
            )}
          </motion.div>
        ))}
      </div>

      <p className="text-slate-400 text-sm text-center max-w-xs">
        La IA está analizando tu CV. Esto puede tomar entre 30 y 60 segundos…
      </p>
    </div>
  )
}
