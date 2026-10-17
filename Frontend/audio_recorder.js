/**
 * audio_recorder.js
 * 
 * UnClone Gate / GramPay - Robust In-Browser 16-bit Mono PCM WAV Audio Recorder
 * 
 * Architecture (Fix 3):
 * 1. Requests microphone access via navigator.mediaDevices.getUserMedia({ audio: true }).
 * 2. Captures audio via MediaStreamAudioSourceNode + ScriptProcessorNode and MediaRecorder chunks in parallel,
 *    eliminating external AudioWorklet file MIME-type issues on iOS Safari and Android Chrome.
 * 3. On stop, decodes recorded audio data into an AudioBuffer via AudioContext.decodeAudioData()
 *    (with seamless fallback to captured PCM Float32Array buffers).
 * 4. Resamples down to 16,000 Hz single-channel (mono) using OfflineAudioContext(1, duration * 16000, 16000).
 * 5. Encodes resampled Float32Array into standard 44-byte WAV header (16-bit PCM integer samples, 16kHz, 1 channel).
 * 6. Returns a Blob with MIME type 'audio/wav' and precise durationSeconds.
 * 
 * Exports:
 * - window.PcmAudioRecorder:
 *     .start(): Promise<void>
 *     .stop(): Promise<{ blob: Blob, durationSeconds: number }>
 *     .isRecording(): boolean
 *     .startPcmRecording(): Promise<void>
 *     .stopPcmRecording(): Promise<{ blob: Blob, durationSeconds: number }>
 */

(function (global) {
  'use strict';

  // Cross-browser AudioContext & OfflineAudioContext references
  const AudioContextClass = global.AudioContext || global.webkitAudioContext;
  const OfflineAudioContextClass = global.OfflineAudioContext || global.webkitOfflineAudioContext;

  /**
   * Safely decodes audio data via AudioContext.decodeAudioData across older Safari
   * (callback-based) and modern browsers (Promise-based).
   * 
   * @param {AudioContext} audioCtx 
   * @param {ArrayBuffer} arrayBuffer 
   * @returns {Promise<AudioBuffer>}
   */
  function decodeAudioDataSafe(audioCtx, arrayBuffer) {
    return new Promise((resolve, reject) => {
      let settled = false;

      const onSuccess = (buffer) => {
        if (!settled) {
          settled = true;
          resolve(buffer);
        }
      };

      const onError = (err) => {
        if (!settled) {
          settled = true;
          reject(err || new Error('decodeAudioData failed'));
        }
      };

      try {
        // Pass slice(0) to avoid detach issues on some WebKit versions
        const bufferCopy = arrayBuffer.slice ? arrayBuffer.slice(0) : arrayBuffer;
        const res = audioCtx.decodeAudioData(bufferCopy, onSuccess, onError);
        if (res && typeof res.then === 'function') {
          res.then(onSuccess).catch(onError);
        }
      } catch (err) {
        onError(err);
      }
    });
  }

  /**
   * Renders an OfflineAudioContext supporting both Promise and legacy oncomplete events.
   * 
   * @param {OfflineAudioContext} offlineCtx 
   * @returns {Promise<AudioBuffer>}
   */
  function renderOfflineContext(offlineCtx) {
    return new Promise((resolve, reject) => {
      let settled = false;

      const onSuccess = (rendered) => {
        if (!settled) {
          settled = true;
          resolve(rendered);
        }
      };

      const onError = (err) => {
        if (!settled) {
          settled = true;
          reject(err || new Error('OfflineAudioContext rendering failed'));
        }
      };

      try {
        if (typeof offlineCtx.startRendering === 'function') {
          const promise = offlineCtx.startRendering();
          if (promise && typeof promise.then === 'function') {
            promise.then(onSuccess).catch(onError);
            return;
          }
        }
        offlineCtx.oncomplete = (e) => onSuccess(e.renderedBuffer);
        offlineCtx.onerror = onError;
        offlineCtx.startRendering();
      } catch (err) {
        onError(err);
      }
    });
  }

  /**
   * Linear interpolation downsampler fallback when OfflineAudioContext is unavailable.
   * 
   * @param {Float32Array} sourceData 
   * @param {number} srcRate 
   * @param {number} dstRate 
   * @returns {Float32Array}
   */
  function resampleLinear(sourceData, srcRate, dstRate) {
    if (srcRate === dstRate || !sourceData || sourceData.length === 0) {
      return sourceData;
    }
    const ratio = srcRate / dstRate;
    const dstLength = Math.max(1, Math.round(sourceData.length / ratio));
    const result = new Float32Array(dstLength);

    for (let i = 0; i < dstLength; i++) {
      const srcPos = i * ratio;
      const index = Math.floor(srcPos);
      const frac = srcPos - index;
      const s0 = sourceData[index] || 0;
      const s1 = index + 1 < sourceData.length ? sourceData[index + 1] : s0;
      result[i] = s0 + frac * (s1 - s0);
    }

    return result;
  }

  /**
   * Encodes a mono Float32Array into a standard 44-byte 16-bit PCM WAV Blob.
   * 
   * Specification:
   * - Format: 16-bit Linear PCM (AudioFormat = 1)
   * - Channels: 1 (Mono)
   * - Sample Rate: sampleRate (default 16,000 Hz)
   * - Bits per sample: 16 (2 bytes per sample)
   * - Byte Rate: sampleRate * 1 * 2 = 32,000 bytes/sec
   * - Block Align: 2 bytes
   * 
   * @param {Float32Array} samples 
   * @param {number} sampleRate 
   * @returns {Blob} Blob with MIME type 'audio/wav'
   */
  function encodeWav(samples, sampleRate = 16000) {
    const numChannels = 1;
    const bitsPerSample = 16;
    const bytesPerSample = bitsPerSample / 8; // 2
    const blockAlign = numChannels * bytesPerSample; // 2
    const byteRate = sampleRate * blockAlign; // 32000
    const dataSize = samples.length * bytesPerSample; // 2 * N
    const headerSize = 44;
    const totalSize = headerSize + dataSize;

    const buffer = new ArrayBuffer(totalSize);
    const view = new DataView(buffer);

    // Helper: Write ASCII string to DataView
    function writeString(offset, str) {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    }

    // --- RIFF Chunk Descriptor ---
    // [00-03] "RIFF"
    writeString(0, 'RIFF');
    // [04-07] ChunkSize = 36 + SubChunk2Size
    view.setUint32(4, 36 + dataSize, true);
    // [08-11] "WAVE"
    writeString(8, 'WAVE');

    // --- "fmt " Sub-chunk ---
    // [12-15] "fmt "
    writeString(12, 'fmt ');
    // [16-19] Subchunk1Size = 16 for PCM
    view.setUint32(16, 16, true);
    // [20-21] AudioFormat = 1 (Linear PCM)
    view.setUint16(20, 1, true);
    // [22-23] NumChannels = 1 (Mono)
    view.setUint16(22, numChannels, true);
    // [24-27] SampleRate = 16000
    view.setUint32(24, sampleRate, true);
    // [28-31] ByteRate = SampleRate * NumChannels * BitsPerSample / 8 = 32000
    view.setUint32(28, byteRate, true);
    // [32-33] BlockAlign = NumChannels * BitsPerSample / 8 = 2
    view.setUint16(32, blockAlign, true);
    // [34-35] BitsPerSample = 16
    view.setUint16(34, bitsPerSample, true);

    // --- "data" Sub-chunk ---
    // [36-39] "data"
    writeString(36, 'data');
    // [40-43] Subchunk2Size = NumSamples * NumChannels * BitsPerSample / 8
    view.setUint32(40, dataSize, true);

    // [44-end] Write 16-bit linear PCM audio samples
    let writeOffset = 44;
    for (let i = 0; i < samples.length; i++, writeOffset += 2) {
      // Clamp between -1.0 and 1.0
      const sample = Math.max(-1, Math.min(1, samples[i]));
      // Map [-1.0, 1.0] to signed 16-bit integer [-32768, 32767]
      const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(writeOffset, int16, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  /**
   * PcmAudioRecorder class
   */
  class PcmAudioRecorder {
    constructor() {
      this._mediaStream = null;
      this._audioContext = null;
      this._sourceNode = null;
      this._scriptNode = null;
      this._zeroGain = null;
      this._mediaRecorder = null;
      this._recordedChunks = [];
      this._pcmBuffers = [];
      this._isRecording = false;
      this._targetSampleRate = 16000;
      this._recordStartTime = 0;
    }

    /**
     * Checks if recording is currently active.
     * @returns {boolean}
     */
    isRecording() {
      return this._isRecording;
    }

    /**
     * Alias for start() to fulfill architecture requirement startPcmRecording().
     * @returns {Promise<void>}
     */
    startPcmRecording() {
      return this.start();
    }

    /**
     * Alias for stop() to fulfill architecture requirement stopPcmRecording().
     * @returns {Promise<{ blob: Blob, durationSeconds: number }>}
     */
    stopPcmRecording() {
      return this.stop();
    }

    /**
     * Starts microphone recording in 16-bit mono PCM format.
     * Compatible with iOS Safari and Android Chrome.
     * 
     * @returns {Promise<void>}
     */
    async start() {
      if (this._isRecording) {
        throw new Error('PcmAudioRecorder: Already recording.');
      }

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('PcmAudioRecorder: getUserMedia is not supported in this environment.');
      }

      if (!AudioContextClass) {
        throw new Error('PcmAudioRecorder: Web Audio API (AudioContext) is not supported.');
      }

      // 1. Initialize & resume AudioContext (required on iOS Safari after user interaction)
      if (!this._audioContext || this._audioContext.state === 'closed') {
        this._audioContext = new AudioContextClass();
      }
      if (this._audioContext.state === 'suspended') {
        await this._audioContext.resume();
      }

      // 2. Request microphone stream with voice-optimized audio constraints
      try {
        this._mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
      } catch (constraintErr) {
        // Fallback for older browsers / webviews that reject complex constraints
        this._mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }

      this._pcmBuffers = [];
      this._recordedChunks = [];

      // 3. Connect MediaStreamAudioSourceNode + ScriptProcessorNode
      // ScriptProcessorNode ensures robust sample capture even if MediaRecorder / container decode fails
      try {
        this._sourceNode = this._audioContext.createMediaStreamSource(this._mediaStream);
        // 4096 buffer size: balanced low-latency and smooth performance on mobile
        this._scriptNode = this._audioContext.createScriptProcessor(4096, 1, 1);
        this._scriptNode.onaudioprocess = (e) => {
          if (!this._isRecording) return;
          const inputChannel = e.inputBuffer.getChannelData(0);
          this._pcmBuffers.push(new Float32Array(inputChannel));
        };

        // Route through a 0-gain node to the destination to keep ScriptProcessor running without speaker echo
        this._zeroGain = this._audioContext.createGain();
        this._zeroGain.gain.setValueAtTime(0, this._audioContext.currentTime);

        this._sourceNode.connect(this._scriptNode);
        this._scriptNode.connect(this._zeroGain);
        this._zeroGain.connect(this._audioContext.destination);
      } catch (nodeErr) {
        console.warn('[PcmAudioRecorder] ScriptProcessorNode setup warning:', nodeErr);
      }

      // 4. Concurrently initialize MediaRecorder chunks (if supported)
      if (typeof MediaRecorder !== 'undefined') {
        let selectedMime = '';
        const candidateMimes = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/mp4',
          'audio/aac',
          'audio/ogg;codecs=opus'
        ];

        for (const mime of candidateMimes) {
          if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(mime)) {
            selectedMime = mime;
            break;
          }
        }

        try {
          const mrOptions = selectedMime ? { mimeType: selectedMime } : undefined;
          this._mediaRecorder = new MediaRecorder(this._mediaStream, mrOptions);
          this._mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
              this._recordedChunks.push(e.data);
            }
          };
          // Timeslice of 100ms for continuous streaming chunks
          this._mediaRecorder.start(100);
        } catch (mrErr) {
          console.warn('[PcmAudioRecorder] MediaRecorder init warning, relying on ScriptProcessorNode:', mrErr);
          this._mediaRecorder = null;
        }
      }

      this._isRecording = true;
      this._recordStartTime = Date.now();
    }

    /**
     * Stops recording, processes, resamples down to 16,000 Hz single-channel (mono),
     * and encodes into a standard 44-byte 16-bit PCM WAV Blob.
     * 
     * @returns {Promise<{ blob: Blob, durationSeconds: number }>}
     */
    async stop() {
      if (!this._isRecording) {
        throw new Error('PcmAudioRecorder: No active recording to stop.');
      }

      this._isRecording = false;

      // 1. Stop MediaRecorder if running
      if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
        await new Promise((resolve) => {
          this._mediaRecorder.onstop = resolve;
          try {
            this._mediaRecorder.stop();
          } catch (_) {
            resolve();
          }
        });
      }

      // 2. Disconnect and cleanup Web Audio nodes
      if (this._scriptNode) {
        this._scriptNode.onaudioprocess = null;
        try { this._scriptNode.disconnect(); } catch (_) {}
        this._scriptNode = null;
      }
      if (this._sourceNode) {
        try { this._sourceNode.disconnect(); } catch (_) {}
        this._sourceNode = null;
      }
      if (this._zeroGain) {
        try { this._zeroGain.disconnect(); } catch (_) {}
        this._zeroGain = null;
      }

      // 3. Stop all microphone hardware tracks immediately
      if (this._mediaStream) {
        this._mediaStream.getTracks().forEach((track) => {
          try { track.stop(); } catch (_) {}
        });
        this._mediaStream = null;
      }

      // 4. Resolve AudioBuffer: decode via AudioContext.decodeAudioData() or fallback to ScriptProcessor buffers
      let audioBuffer = null;

      // Method A: Attempt decodeAudioData from MediaRecorder chunks
      if (this._recordedChunks.length > 0 && this._audioContext) {
        try {
          const mime = (this._mediaRecorder && this._mediaRecorder.mimeType) || 'audio/webm';
          const containerBlob = new Blob(this._recordedChunks, { type: mime });
          if (containerBlob.size > 0) {
            const arrayBuffer = await containerBlob.arrayBuffer();
            audioBuffer = await decodeAudioDataSafe(this._audioContext, arrayBuffer);
          }
        } catch (decodeErr) {
          console.warn('[PcmAudioRecorder] decodeAudioData on container chunks failed, using ScriptProcessor samples:', decodeErr);
        }
      }

      // Method B: Assemble AudioBuffer directly from ScriptProcessor Float32Array PCM buffers
      if (!audioBuffer && this._pcmBuffers.length > 0 && this._audioContext) {
        const totalSamples = this._pcmBuffers.reduce((sum, b) => sum + b.length, 0);
        if (totalSamples > 0) {
          const merged = new Float32Array(totalSamples);
          let offset = 0;
          for (const buf of this._pcmBuffers) {
            merged.set(buf, offset);
            offset += buf.length;
          }
          audioBuffer = this._audioContext.createBuffer(1, totalSamples, this._audioContext.sampleRate);
          audioBuffer.copyToChannel(merged, 0);
        }
      }

      if (!audioBuffer) {
        throw new Error('PcmAudioRecorder: No audio data was captured during recording.');
      }

      // 5. Resample down to 16,000 Hz single-channel (mono) using OfflineAudioContext(1, duration * 16000, 16000)
      const targetRate = this._targetSampleRate; // 16000
      const durationSec = audioBuffer.duration || ((Date.now() - this._recordStartTime) / 1000);
      const targetFrames = Math.max(1, Math.round(durationSec * targetRate));

      let resampledData = null;

      if (OfflineAudioContextClass) {
        try {
          const offlineCtx = new OfflineAudioContextClass(1, targetFrames, targetRate);
          const source = offlineCtx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(offlineCtx.destination);
          source.start(0);

          const rendered = await renderOfflineContext(offlineCtx);
          resampledData = rendered.getChannelData(0);
        } catch (resampleErr) {
          console.warn('[PcmAudioRecorder] OfflineAudioContext resample failed, using linear interpolation:', resampleErr);
        }
      }

      // Fallback interpolation if OfflineAudioContext was unavailable or threw
      if (!resampledData) {
        const sourceData = audioBuffer.getChannelData(0);
        resampledData = resampleLinear(sourceData, audioBuffer.sampleRate, targetRate);
      }

      // 6. Encode resampled Float32Array into standard 44-byte WAV header (16-bit PCM integer samples, 16,000 Hz, 1 channel)
      const wavBlob = encodeWav(resampledData, targetRate);
      const finalDuration = resampledData.length / targetRate;

      // Clean buffer references
      this._recordedChunks = [];
      this._pcmBuffers = [];

      return {
        blob: wavBlob,
        durationSeconds: finalDuration
      };
    }

    /**
     * Cancels any in-flight recording and discards buffers without processing.
     */
    cancel() {
      this._isRecording = false;
      if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
        try { this._mediaRecorder.stop(); } catch (_) {}
      }
      if (this._mediaStream) {
        this._mediaStream.getTracks().forEach((t) => {
          try { t.stop(); } catch (_) {}
        });
        this._mediaStream = null;
      }
      if (this._scriptNode) {
        try { this._scriptNode.disconnect(); } catch (_) {}
        this._scriptNode = null;
      }
      if (this._sourceNode) {
        try { this._sourceNode.disconnect(); } catch (_) {}
        this._sourceNode = null;
      }
      if (this._zeroGain) {
        try { this._zeroGain.disconnect(); } catch (_) {}
        this._zeroGain = null;
      }
      this._recordedChunks = [];
      this._pcmBuffers = [];
    }
  }

  // Create default singleton instance for static calls
  const defaultRecorder = new PcmAudioRecorder();

  // Attach static methods to the class for direct window.PcmAudioRecorder.start() usage
  PcmAudioRecorder.start = function () {
    return defaultRecorder.start();
  };

  PcmAudioRecorder.stop = function () {
    return defaultRecorder.stop();
  };

  PcmAudioRecorder.isRecording = function () {
    return defaultRecorder.isRecording();
  };

  PcmAudioRecorder.startPcmRecording = function () {
    return defaultRecorder.startPcmRecording();
  };

  PcmAudioRecorder.stopPcmRecording = function () {
    return defaultRecorder.stopPcmRecording();
  };

  PcmAudioRecorder.cancel = function () {
    return defaultRecorder.cancel();
  };

  // Expose encodeWav & resampleLinear as utility methods on PcmAudioRecorder
  PcmAudioRecorder.encodeWav = encodeWav;
  PcmAudioRecorder.resampleLinear = resampleLinear;

  // Export to global window object
  if (typeof window !== 'undefined') {
    window.PcmAudioRecorder = PcmAudioRecorder;
    window.startPcmRecording = () => defaultRecorder.start();
    window.stopPcmRecording = () => defaultRecorder.stop();
  }

  // Export for CommonJS / Module test environments if available
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      PcmAudioRecorder,
      encodeWav,
      resampleLinear,
      decodeAudioDataSafe,
      renderOfflineContext
    };
  }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
