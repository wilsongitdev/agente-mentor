import { useState, useRef } from 'react'
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

/**
 * HomePage Component
 * 
 * Punto de entrada principal de la aplicación. Gestiona el estado de carga,
 * la subida del archivo PDF y el proceso de 'polling' (consulta recurrente)
 * hasta que el análisis multi-agente en el backend finaliza.
 */
export default function HomePage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [currentStatus, setCurrentStatus] = useState('idle')
  const [resetKey, setResetKey] = useState(0)
  
  const abortControllerRef = useRef(null)

  /**
   * Resetea el flujo de trabajo a su estado inicial.
   * Cancela cualquier petición de red activa (polling) usando AbortController.
   */
  const resetFlow = () => {
    // Abort active polling if any (Stop the recursion in the service)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    setIsLoading(false)
    setCurrentStatus('idle')
    setResetKey(prev => prev + 1) // Forzar re-montaje del componente de subida
  }

  /**
   * Orquestador de la subida y análisis del CV.
   * 
   * @param {File} selectedFile - El archivo PDF seleccionado.
   * @param {string} selectedObjective - El objetivo profesional (ej: 'Data Analyst').
   */
  const handleUpload = async (selectedFile, selectedObjective) => {
    setIsLoading(true)
    setCurrentStatus('procesando')

    // Initialize abort controller to handle user cancellations
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      // 1. Upload to start the LangGraph process
      const { session_id } = await uploadCV(selectedFile, selectedObjective)
      toast.success('CV recibido. Iniciando análisis…')

      // 2. Poll the status until completion (handled by the service)
      const learningPath = await pollUntilDone(session_id, {
        onProgress: setCurrentStatus,
        intervalMs: 3000,
        signal: controller.signal,
      })

      toast.success('¡Análisis completado!')
      const lp = learningPath
      resetFlow()
      // Redirigir a la página de resultados con la data obtenida
      navigate(`/results/${session_id}`, { state: { learningPath: lp } })
    } catch (err) {
      // Manejo de errores y cancelación manual
      if (err.message !== 'Operación cancelada por el usuario.') {
        toast.error(err.message || 'Error al procesar el CV')
      }
      resetFlow()
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
              Powered by LangGraph + AWS Bedrock
            </div>

            <h1 className="text-4xl sm:text-6xl font-black leading-tight mb-4">
              <span className="gradient-text">CV Analyzer</span>
              <br />
              <span className="text-slate-800 text-3xl sm:text-5xl font-bold">
                Tu Learning Path con IA
              </span>
            </h1>

            <p className="text-slate-600 text-lg max-w-2xl mx-auto mb-10">
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
              <LoadingSpinner 
                currentStatus={currentStatus} 
                onCancel={resetFlow}
              />
            ) : (
              <CVUpload 
                key={resetKey}
                onUpload={handleUpload} 
                isLoading={isLoading} 
              />
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
                  <f.icon className="w-5 h-5 text-brand-600" />
                </div>
                <h3 className="font-semibold text-slate-900">{f.title}</h3>
                <p className="text-sm text-slate-600">{f.desc}</p>
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
