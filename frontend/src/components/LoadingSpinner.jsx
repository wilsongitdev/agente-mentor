import { motion } from 'framer-motion'

const STEPS = [
  { label: 'Extrayendo texto del PDF', icon: '📄' },
  { label: 'Analizando habilidades con IA', icon: '🧠' },
  { label: 'Buscando cursos relevantes', icon: '🔍' },
  { label: 'Generando tu Learning Path', icon: '🗺️' },
]

const STATUS_TO_STEP = {
  'procesando': 0,
  'procesando_pdf_parser': 1,
  'procesando_skill_extractor': 2,
  'procesando_course_matcher': 3,
  'procesando_learning_path_generator': 3,
  'completado': 3,
}

export default function LoadingSpinner({ currentStatus = 'procesando', onCancel }) {
  const currentStep = STATUS_TO_STEP[currentStatus] ?? 0

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
          {STEPS[currentStep].icon}
        </div>
      </div>

      {/* Steps */}
      <div className="flex flex-col gap-3 w-full max-w-sm">
        {STEPS.map((step, idx) => (
          <motion.div
            key={idx}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
              idx === currentStep
                ? 'bg-brand-600/10 dark:bg-brand-600/20 border border-brand-200 dark:border-brand-500/50 text-brand-600 dark:text-brand-200'
                : idx < currentStep
                ? 'text-slate-400 opacity-60'
                : 'text-slate-300 dark:text-slate-600'
            }`}
            animate={idx === currentStep ? { scale: [1, 1.02, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <span className="text-lg">{step.icon}</span>
            <span className="text-sm font-medium">{step.label}</span>
            {idx < currentStep && (
              <span className="ml-auto text-green-400 text-xs font-bold">✓ Hecho</span>
            )}
          </motion.div>
        ))}
      </div>

      <div className="flex flex-col gap-4 items-center">
        <p className="text-slate-600 text-sm text-center max-w-xs">
          La IA está analizando tu CV. Esto puede tomar entre 30 y 60 segundos…
        </p>
        
        {onCancel && (
          <button
            onClick={onCancel}
            className="text-xs text-slate-500 hover:text-red-400 transition-colors uppercase tracking-widest font-bold underline underline-offset-4"
          >
            Cancelar Análisis
          </button>
        )}
      </div>
    </div>
  )
}
