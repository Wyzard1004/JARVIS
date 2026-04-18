import React, { useState, useRef } from 'react'

/**
 * PushToTalkButton Component (4.2.3)
 * 
 * Captures microphone audio and sends to backend for:
 * 1. Whisper transcription
 * 2. Ollama LLM intent parsing
 * 3. Gossip protocol execution
 */

function PushToTalkButton({ onCommand }) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder.current = new MediaRecorder(stream)
      audioChunks.current = []

      mediaRecorder.current.onstabledatachange = (event) => {
        audioChunks.current.push(event.data)
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

    mediaRecorder.current.addEventListener('stop', async () => {
      const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' })
      
      // TODO: Send audioBlob to backend for Whisper transcription
      // const formData = new FormData()
      // formData.append('audio', audioBlob)
      // const transcribed = await fetch('/api/transcribe', { method: 'POST', body: formData })
      
      // For now, use a mock transcript
      const mockTranscript = 'JARVIS, re-route swarm to Grid Alpha'
      setTranscript(mockTranscript)
      
      // Send command to backend
      onCommand(mockTranscript)
    })

    mediaRecorder.current.stop()
    mediaRecorder.current.stream.getTracks().forEach(track => track.stop())
  }

  return (
    <div className="flex flex-col gap-3">
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
