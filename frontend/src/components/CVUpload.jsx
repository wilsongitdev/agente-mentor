import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { Upload, FileText, X, Zap } from 'lucide-react'
import toast from 'react-hot-toast'

/**
 * CVUpload Component
 * 
 * Interfaz de arrastrar y soltar (Drag & Drop) para la carga de archivos PDF.
 * Permite seleccionar el objetivo profesional antes de iniciar el proceso.
 * 
 * @param {Object} props
 * @param {Function} props.onUpload - Callback ejecutado al confirmar el análisis.
 * @param {boolean} props.isLoading - Estado de carga global de la app.
 */
export default function CVUpload({ onUpload, isLoading }) {
  const [selectedFile, setSelectedFile] = useState(null)
  const [selectedObjective, setSelectedObjective] = useState("Data Analyst")
  
  const OBJECTIVE_OPTIONS = [
    "Data Analyst",
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "Business Intelligence Analyst",
    "Otro"
  ]

  /**
   * Manejador para el evento 'Drop' de archivos.
   * Valida que sea un único archivo PDF.
   */
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      toast.error('Solo se aceptan archivos PDF (máx. 10 MB)')
      return
    }
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0])
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    disabled: isLoading,
  })

  /**
   * Valida y envía el archivo y el objetivo seleccionado al componente padre.
   */
  const handleSubmit = () => {
    if (!selectedFile) {
      toast.error('Por favor selecciona un archivo PDF primero')
      return
    }
    onUpload(selectedFile, selectedObjective)
  }

  const removeFile = (e) => {
    e.stopPropagation()
    setSelectedFile(null)
  }

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col gap-6">
      {/* Drop zone */}
      <motion.div
        {...getRootProps()}
        className={`
          relative cursor-pointer rounded-2xl border-2 border-dashed p-10
          flex flex-col items-center justify-center gap-4 transition-all
          ${isDragActive
            ? 'border-brand-400 bg-brand-600/10 scale-[1.02]'
            : selectedFile
            ? 'border-green-500/60 bg-green-500/5'
            : 'border-slate-300 hover:border-brand-500 hover:bg-brand-600/5'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        whileHover={!isLoading ? { scale: 1.01 } : {}}
        whileTap={!isLoading ? { scale: 0.99 } : {}}
      >
        <input {...getInputProps()} />

        {selectedFile ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center">
              <FileText className="w-8 h-8 text-green-400" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-slate-900 dark:text-slate-100">{selectedFile.name}</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <button
              onClick={removeFile}
              className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors"
            >
              <X className="w-3 h-3" /> Cambiar archivo
            </button>
          </div>
        ) : isLoading ? (
          <p className="text-slate-600 dark:text-slate-300 text-sm text-center max-w-xs">
            La IA está analizando tu CV. Esto puede tomar entre 30 y 60 segundos…
          </p>
        ) : (
          <>
            <motion.div
              className="w-16 h-16 rounded-full bg-brand-600/20 flex items-center justify-center"
              animate={isDragActive ? { scale: [1, 1.2, 1] } : {}}
              transition={{ repeat: Infinity, duration: 0.8 }}
            >
              <Upload className="w-8 h-8 text-brand-400" />
            </motion.div>
            <div className="text-center">
              <p className="font-semibold text-slate-900 dark:text-slate-500">
                {isDragActive ? 'Suelta el archivo aquí' : 'Arrastra tu CV aquí'}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                o <span className="text-brand-600 underline">haz click para seleccionar</span>
              </p>
              <p className="text-xs text-slate-500 mt-2">PDF · máx. 10 MB</p>
            </div>
          </>
        )}
      </motion.div>

      {/* Professional Objective Selector */}
      <div className="flex flex-col gap-2">
        <label htmlFor="objective" className="text-sm font-medium text-slate-900 dark:text-slate-600 ml-1">
          Objetivo Profesional / Posición Aspirada
        </label>
        <select
          id="objective"
          value={selectedObjective}
          onChange={(e) => setSelectedObjective(e.target.value)}
          disabled={isLoading}
          className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors disabled:opacity-50"
        >
          {OBJECTIVE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>

      {/* Analyse button */}
      <motion.button
        onClick={handleSubmit}
        disabled={!selectedFile || isLoading}
        className={`
          flex items-center justify-center gap-3 w-full py-4 px-6
          rounded-xl font-semibold text-lg transition-all
          ${selectedFile && !isLoading
            ? 'bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 text-white shadow-lg shadow-brand-900/10 dark:shadow-brand-900/40 cursor-pointer'
            : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
          }
        `}
        whileHover={selectedFile && !isLoading ? { scale: 1.02 } : {}}
        whileTap={selectedFile && !isLoading ? { scale: 0.98 } : {}}
      >
        <Zap className="w-5 h-5" />
        {isLoading ? 'Analizando…' : 'Analizar mi CV con IA'}
      </motion.button>
    </div>
  )
}
