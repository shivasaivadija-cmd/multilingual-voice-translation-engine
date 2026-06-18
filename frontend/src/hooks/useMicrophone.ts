import { useState, useRef, useCallback, useEffect } from 'react';
import { wsService } from '@/services/websocket';

export const useMicrophone = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number>();
  const isRecordingRef = useRef(false);

  const startRecording = useCallback(async () => {
    try {
      setError(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      mediaStreamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      await audioContext.audioWorklet.addModule('/audio-processor.js');

      const source = audioContext.createMediaStreamSource(stream);

      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
      workletNode.port.onmessage = (e: MessageEvent) => {
        if (!isRecordingRef.current) return;
        wsService.sendAudioChunk(e.data);
      };

      source.connect(workletNode);
      workletNode.connect(audioContext.destination);
      workletNodeRef.current = workletNode;

      isRecordingRef.current = true;
      setIsRecording(true);
      updateAudioLevel();
    } catch (err) {
      console.error('Microphone access error:', err);
      setError('Could not access microphone. Please check permissions.');
    }
  }, []);

  const stopRecording = useCallback(() => {
    isRecordingRef.current = false;
    setIsRecording(false);

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;

    setAudioLevel(0);
  }, []);

  const updateAudioLevel = useCallback(() => {
    if (!isRecordingRef.current || !analyserRef.current) return;
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    setAudioLevel(avg / 255);
    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  }, []);

  useEffect(() => {
    return () => {
      if (isRecordingRef.current) stopRecording();
    };
  }, [stopRecording]);

  return { isRecording, audioLevel, error, startRecording, stopRecording };
};
