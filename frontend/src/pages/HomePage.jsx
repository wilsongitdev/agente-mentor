import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Brain, Layers, Zap, Map } from 'lucide-react'
import toast from 'react-hot-toast'
import CVUpload from '../components/CVUpload'
import LoadingSpinner from '../components/LoadingSpinner'
import { uploadCV, pollUntilDone } from '../services/api'

const FEATURES = [
  { icon: Brain, title: 'Análisis IA', desc: 'Extrae habilidades con LLMs avanzados (GPT-4 / Claude)' },
  { icon: Layers, title: 'Multi-Agente', desc: 'Orquestado con LangGraph: 4 agentes especializados' },
  { icon: Zap, title: 'Matching Semántico', desc: 'Búsqueda vectorial de cursos con FAISS' },
  { icon: Map, title: 'Learning Path', desc: 'Roadmap personalizado ordenado de Junior a Senior' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [currentStatus, setCurrentStatus] = useState('idle')

  const handleUpload = async (file) => {
    setIsLoading(true)
    setCurrentStatus('processing')

    try {
      const { session_id } = await uploadCV(file)
      toast.success('CV recibido. Iniciando análisis…')

      const learningPath = await pollUntilDone(session_id, {
        onProgress: setCurrentStatus,
        intervalMs: 3000,
      })

      toast.success('¡Análisis completado!')
      navigate(`/results/${session_id}`, { state: { learningPath } })
    } catch (err) {
      toast.error(err.message || 'Error al procesar el CV')
      setCurrentStatus('idle')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <div className="relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand-600/10 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-600/20 border border-brand-500/30 text-brand-300 text-sm font-medium mb-6">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Powered by LangGraph + GPT-4 / Claude
            </div>

            <h1 className="text-4xl sm:text-6xl font-black leading-tight mb-4">
              <span className="gradient-text">CV Analyzer</span>
              <br />
              <span className="text-slate-200 text-3xl sm:text-5xl font-bold">
                Tu Learning Path con IA
              </span>
            </h1>

            <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-10">
              Sube tu CV y nuestra plataforma multi-agente analiza tus habilidades,
              detecta brechas y genera un roadmap de aprendizaje personalizado.
            </p>
          </motion.div>

          {/* Upload / Spinner */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            {isLoading ? (
              <LoadingSpinner currentStatus={currentStatus} />
            ) : (
              <CVUpload onUpload={handleUpload} isLoading={isLoading} />
            )}
          </motion.div>
        </div>
      </div>

      {/* Features */}
      {!isLoading && (
        <div className="max-w-4xl mx-auto px-6 py-16 w-full">
          <p className="text-center text-slate-500 text-sm uppercase tracking-widest font-semibold mb-8">
            Cómo funciona
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {FEATURES.map((f, i) => (
              <motion.div
                key={i}
                className="glass rounded-2xl p-5 flex flex-col gap-3"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i }}
              >
                <div className="w-10 h-10 rounded-xl bg-brand-600/20 flex items-center justify-center">
                  <f.icon className="w-5 h-5 text-brand-400" />
                </div>
                <h3 className="font-semibold text-slate-100">{f.title}</h3>
                <p className="text-sm text-slate-400">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-auto border-t border-white/5 py-6 text-center text-slate-600 text-xs">
        CV Analyzer · Multi-Agent AI System · LangGraph + FastAPI + React
      </footer>
    </div>
  )
}
