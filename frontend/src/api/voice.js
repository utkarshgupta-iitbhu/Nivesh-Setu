// Centralized Voice Manager for NiveshSetu
// - TTS (App speaks): Sarvam Bulbul v3 primary, browser speechSynthesis offline fallback.
// - STT (User speaks): Sarvam Saarika v2.5 primary (via MediaRecorder), browser SpeechRecognition fallback.
// - Guarantees ONLY ONE audio plays at a time, supports instant Stop, and cancels in-flight fetches.

import { useEffect, useState } from 'react';
import { api } from './client';

let activeAudio = null;
let playToken = 0;
let currentSpeakingId = null;
const listeners = new Set();

function notify() {
  listeners.forEach((fn) => fn(currentSpeakingId));
}

export function stopSpeaking() {
  playToken += 1;
  if (activeAudio) {
    try {
      activeAudio.pause();
      activeAudio.currentTime = 0;
    } catch {
      // ignore
    }
    activeAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  currentSpeakingId = null;
  notify();
}

export async function toggleSpeak(id, text, lang = 'en') {
  // Clicking the currently playing button stops playback cleanly
  if (currentSpeakingId === id) {
    stopSpeaking();
    return;
  }

  // Stop any other active audio immediately before starting new one
  stopSpeaking();
  const myToken = playToken;
  currentSpeakingId = id;
  notify();

  try {
    const res = await api.tts(text, lang);
    // If user clicked Stop or switched screens while Sarvam was fetching, abort silently
    if (myToken !== playToken) return;

    if (res.audio_base64) {
      const audio = new Audio(`data:${res.mime_type || 'audio/wav'};base64,${res.audio_base64}`);
      activeAudio = audio;
      audio.onended = () => {
        if (myToken === playToken) {
          activeAudio = null;
          currentSpeakingId = null;
          notify();
        }
      };
      audio.onerror = () => {
        if (myToken === playToken) {
          activeAudio = null;
          currentSpeakingId = null;
          notify();
        }
      };
      await audio.play();
      return;
    }
  } catch {
    if (myToken !== playToken) return;
  }

  // Offline fallback: browser built-in speechSynthesis
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    utter.onend = () => {
      if (myToken === playToken) {
        currentSpeakingId = null;
        notify();
      }
    };
    utter.onerror = () => {
      if (myToken === playToken) {
        currentSpeakingId = null;
        notify();
      }
    };
    window.speechSynthesis.speak(utter);
  } else {
    currentSpeakingId = null;
    notify();
  }
}

// Speech-to-Text: tries Sarvam Saarika v2.5 via MediaRecorder (5s clip), falls back to browser SpeechRecognition
export function recordAndTranscribe(lang = 'hi', { onStart, onResult, onEnd, onError } = {}) {
  stopSpeaking();

  // Fallback helper using Web Speech API (Chrome/Edge)
  const useBrowserRecognition = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      onError?.(lang === 'hi' ? 'इस ब्राउज़र में माइक उपलब्ध नहीं है।' : 'Voice input is not supported in this browser.');
      onEnd?.();
      return;
    }
    const rec = new SR();
    rec.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => onStart?.();
    rec.onresult = (e) => {
      const txt = e.results?.[0]?.[0]?.transcript || '';
      if (txt) onResult?.(txt);
    };
    rec.onerror = () => onError?.(lang === 'hi' ? 'आवाज़ नहीं सुनी जा सकी।' : 'Could not hear audio.');
    rec.onend = () => onEnd?.();
    rec.start();
  };

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    useBrowserRecognition();
    return () => {};
  }

  let recorder = null;
  let stream = null;
  let stopped = false;

  navigator.mediaDevices
    .getUserMedia({ audio: true })
    .then((s) => {
      stream = s;
      const chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop());
        const blob = new Blob(chunks, { type: 'audio/webm' });
        try {
          const res = await api.stt(blob, lang);
          if (res.transcript) {
            onResult?.(res.transcript);
            onEnd?.();
            return;
          }
        } catch {
          // fall through
        }
        // If Sarvam STT is offline/no-key, tell user gently or fallback
        onError?.(
          lang === 'hi'
            ? 'Sarvam वॉइस ऑफ़लाइन है — कृपया टाइप करें या Chrome में फिर कोशिश करें।'
            : 'Sarvam STT is offline — please type your answer or try again.'
        );
        onEnd?.();
      };
      onStart?.();
      recorder.start();
      // Auto-stop after 6 seconds for snappy low-bandwidth uploads
      setTimeout(() => {
        if (!stopped && recorder?.state === 'recording') recorder.stop();
      }, 6000);
    })
    .catch(() => useBrowserRecognition());

  return () => {
    stopped = true;
    if (recorder?.state === 'recording') recorder.stop();
    if (stream) stream.getTracks().forEach((tr) => tr.stop());
  };
}

export function useVoice() {
  const [speakingId, setSpeakingId] = useState(currentSpeakingId);
  useEffect(() => {
    listeners.add(setSpeakingId);
    return () => listeners.delete(setSpeakingId);
  }, []);
  return { speakingId, toggleSpeak, stopSpeaking };
}
