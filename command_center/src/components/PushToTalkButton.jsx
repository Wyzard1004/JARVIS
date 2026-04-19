import React, { useState, useRef } from 'react'

/**
 * PushToTalkButton Component (4.2.3)
 * 
 * Captures microphone audio and sends to backend for:
 * 1. Whisper transcription
 * 2. Ollama LLM intent parsing
 * 3. Gossip protocol execution
 */

function PushToTalkButton({ onCommand, activeSoldierLabel = 'Soldier 1' }) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder.current = new MediaRecorder(stream)
      audioChunks.current = []

      mediaRecorder.current.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.current.push(event.data)
        }
      }

      mediaRecorder.current.start()
      setIsListening(true)
      setTranscript('Listening...')
    } catch (error) {
      console.error('Microphone access denied:', error)
      setTranscript('Mic access denied')
    }
  }

  const stopListening = async () => {
    setIsListening(false)
    
    if (!mediaRecorder.current) return

    const recorder = mediaRecorder.current
    recorder.onstop = async () => {
      const mimeType = recorder.mimeType || 'audio/webm'
      const audioBlob = new Blob(audioChunks.current, { type: mimeType })

      setTranscript('Processing audio...')
      const result = await onCommand({ audioBlob, mimeType })

      if (result?.transcribed_text) {
        setTranscript(result.transcribed_text)
      } else if (result?.error) {
        setTranscript(`Error: ${result.error}`)
      } else {
        setTranscript('No transcript received')
      }
    }

    recorder.stop()
    recorder.stream.getTracks().forEach(track => track.stop())
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100">
        Transmitting as <span className="font-semibold">{activeSoldierLabel}</span>
      </div>
      <button
        onClick={isListening ? stopListening : startListening}
        className={`py-3 px-4 rounded font-bold text-white transition ${
          isListening
            ? 'bg-red-600 hover:bg-red-700 animate-pulse'
            : 'bg-green-600 hover:bg-green-700'
        }`}
      >
        {isListening ? '🔴 STOP' : '🎤 PUSH TO TALK'}
      </button>
      
      {transcript && (
        <div className="bg-gray-900 p-3 rounded border border-gray-600">
          <p className="text-sm text-gray-300">
            <span className="font-mono text-yellow-400">{transcript}</span>
          </p>
        </div>
      )}
    </div>
  )
}

export default PushToTalkButton
