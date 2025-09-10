/**
 * Advanced Audio Processor for Voice Activity Detection and Noise Filtering
 * Implements multiple VAD algorithms and noise reduction techniques
 */

export interface AudioMetrics {
  rms: number;
  zcr: number;
  spectralCentroid: number;
  spectralRolloff: number;
  energy: number;
  confidence: number;
}

export interface VADConfig {
  // Energy thresholds
  energyThreshold: number;
  rmsThreshold: number;
  
  // Spectral analysis thresholds
  zcrThreshold: number;
  spectralCentroidMin: number;
  spectralCentroidMax: number;
  
  // Noise gate settings
  noiseGateThreshold: number;
  attackTime: number;
  releaseTime: number;
  
  // Confidence scoring
  minConfidence: number;
  
  // Timing constraints
  minSpeechDuration: number;
  maxSilenceDuration: number;
}

export class AdvancedAudioProcessor {
  private config: VADConfig;
  private noiseFloor: number = 0;
  private noiseFloorSamples: number[] = [];
  private isCalibrating: boolean = false;
  private calibrationSamples: number = 0;
  private readonly CALIBRATION_DURATION = 3000; // 3 seconds
  
  // Noise gate state
  private gateState: 'closed' | 'opening' | 'open' | 'closing' = 'closed';
  private gateEnvelope: number = 0;
  private lastGateTime: number = 0;
  
  // Speech detection state
  private speechStartTime: number = 0;
  private lastSpeechTime: number = 0;
  private consecutiveSpeechFrames: number = 0;
  private consecutiveSilenceFrames: number = 0;
  
  constructor(config?: Partial<VADConfig>) {
    this.config = {
      // Default configuration optimized for speech detection
      energyThreshold: 0.01,
      rmsThreshold: 0.02,
      zcrThreshold: 0.3,
      spectralCentroidMin: 300,
      spectralCentroidMax: 3000,
      noiseGateThreshold: 0.005,
      attackTime: 10, // ms
      releaseTime: 100, // ms
      minConfidence: 0.6,
      minSpeechDuration: 300, // ms
      maxSilenceDuration: 1500, // ms
      ...config
    };
    
    this.startNoiseFloorCalibration();
  }

  /**
   * Start automatic noise floor calibration
   */
  public startNoiseFloorCalibration(): void {
    console.log('🎚️ Starting noise floor calibration...');
    this.isCalibrating = true;
    this.calibrationSamples = 0;
    this.noiseFloorSamples = [];
    
    setTimeout(() => {
      this.finishCalibration();
    }, this.CALIBRATION_DURATION);
  }

  private finishCalibration(): void {
    if (this.noiseFloorSamples.length > 0) {
      // Calculate noise floor as 95th percentile to avoid outliers
      const sorted = this.noiseFloorSamples.sort((a, b) => a - b);
      const index = Math.floor(sorted.length * 0.95);
      this.noiseFloor = sorted[index];
      
      // Adjust thresholds based on noise floor
      this.config.energyThreshold = Math.max(this.noiseFloor * 2, 0.005);
      this.config.rmsThreshold = Math.max(this.noiseFloor * 3, 0.01);
      this.config.noiseGateThreshold = Math.max(this.noiseFloor * 1.5, 0.003);
      
      console.log(`✅ Calibration complete. Noise floor: ${this.noiseFloor.toFixed(4)}`);
      console.log(`📊 Adjusted thresholds - Energy: ${this.config.energyThreshold.toFixed(4)}, RMS: ${this.config.rmsThreshold.toFixed(4)}`);
    }
    
    this.isCalibrating = false;
  }

  /**
   * Process audio frame and return comprehensive metrics
   */
  public processAudioFrame(audioData: Float32Array, sampleRate: number = 16000): AudioMetrics {
    const rms = this.calculateRMS(audioData);
    const zcr = this.calculateZCR(audioData);
    const energy = this.calculateEnergy(audioData);
    const spectralCentroid = this.calculateSpectralCentroid(audioData, sampleRate);
    const spectralRolloff = this.calculateSpectralRolloff(audioData, sampleRate);
    
    // Update noise floor during calibration
    if (this.isCalibrating) {
      this.noiseFloorSamples.push(rms);
      this.calibrationSamples++;
    }
    
    // Calculate confidence score
    const confidence = this.calculateConfidence(rms, zcr, spectralCentroid, energy);
    
    return {
      rms,
      zcr,
      spectralCentroid,
      spectralRolloff,
      energy,
      confidence
    };
  }

  /**
   * Determine if audio frame contains speech
   */
  public isSpeech(metrics: AudioMetrics): boolean {
    const now = Date.now();
    
    // Apply noise gate
    const gatedMetrics = this.applyNoiseGate(metrics, now);
    if (!gatedMetrics) {
      this.consecutiveSilenceFrames++;
      this.consecutiveSpeechFrames = 0;
      return false;
    }
    
    // Multi-criteria speech detection
    const energyCheck = gatedMetrics.energy > this.config.energyThreshold;
    const rmsCheck = gatedMetrics.rms > this.config.rmsThreshold;
    const zcrCheck = gatedMetrics.zcr < this.config.zcrThreshold;
    const spectralCheck = gatedMetrics.spectralCentroid >= this.config.spectralCentroidMin && 
                         gatedMetrics.spectralCentroid <= this.config.spectralCentroidMax;
    const confidenceCheck = gatedMetrics.confidence >= this.config.minConfidence;
    
    // Require multiple criteria to be met
    const criteriaCount = [energyCheck, rmsCheck, zcrCheck, spectralCheck, confidenceCheck].filter(Boolean).length;
    const isSpeechFrame = criteriaCount >= 3; // At least 3 out of 5 criteria
    
    if (isSpeechFrame) {
      this.consecutiveSpeechFrames++;
      this.consecutiveSilenceFrames = 0;
      
      if (this.speechStartTime === 0) {
        this.speechStartTime = now;
      }
      this.lastSpeechTime = now;
      
      // Require minimum consecutive frames for speech detection
      return this.consecutiveSpeechFrames >= 3;
    } else {
      this.consecutiveSilenceFrames++;
      this.consecutiveSpeechFrames = 0;
      
      // Check if silence duration exceeds threshold
      if (this.lastSpeechTime > 0 && (now - this.lastSpeechTime) > this.config.maxSilenceDuration) {
        this.speechStartTime = 0;
      }
      
      return false;
    }
  }

  /**
   * Apply noise gate with attack/release envelope
   */
  private applyNoiseGate(metrics: AudioMetrics, currentTime: number): AudioMetrics | null {
    const inputLevel = metrics.rms;
    const threshold = this.config.noiseGateThreshold;
    const deltaTime = currentTime - this.lastGateTime;
    this.lastGateTime = currentTime;
    
    // Determine target gate state
    const shouldOpen = inputLevel > threshold;
    
    // State machine for noise gate
    switch (this.gateState) {
      case 'closed':
        if (shouldOpen) {
          this.gateState = 'opening';
        }
        break;
        
      case 'opening':
        this.gateEnvelope += deltaTime / this.config.attackTime;
        if (this.gateEnvelope >= 1) {
          this.gateEnvelope = 1;
          this.gateState = 'open';
        }
        if (!shouldOpen) {
          this.gateState = 'closing';
        }
        break;
        
      case 'open':
        if (!shouldOpen) {
          this.gateState = 'closing';
        }
        break;
        
      case 'closing':
        this.gateEnvelope -= deltaTime / this.config.releaseTime;
        if (this.gateEnvelope <= 0) {
          this.gateEnvelope = 0;
          this.gateState = 'closed';
        }
        if (shouldOpen) {
          this.gateState = 'opening';
        }
        break;
    }
    
    // Apply gate envelope
    if (this.gateEnvelope <= 0.1) {
      return null; // Gate is closed
    }
    
    // Apply envelope to metrics
    const gateMultiplier = this.gateEnvelope;
    return {
      ...metrics,
      rms: metrics.rms * gateMultiplier,
      energy: metrics.energy * gateMultiplier,
      confidence: metrics.confidence * gateMultiplier
    };
  }

  /**
   * Calculate Root Mean Square (RMS) energy
   */
  private calculateRMS(audioData: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < audioData.length; i++) {
      sum += audioData[i] * audioData[i];
    }
    return Math.sqrt(sum / audioData.length);
  }

  /**
   * Calculate Zero Crossing Rate (ZCR)
   */
  private calculateZCR(audioData: Float32Array): number {
    let crossings = 0;
    for (let i = 1; i < audioData.length; i++) {
      if ((audioData[i] >= 0) !== (audioData[i - 1] >= 0)) {
        crossings++;
      }
    }
    return crossings / (audioData.length - 1);
  }

  /**
   * Calculate total energy
   */
  private calculateEnergy(audioData: Float32Array): number {
    let energy = 0;
    for (let i = 0; i < audioData.length; i++) {
      energy += Math.abs(audioData[i]);
    }
    return energy / audioData.length;
  }

  /**
   * Calculate spectral centroid (simplified)
   */
  private calculateSpectralCentroid(audioData: Float32Array, sampleRate: number): number {
    // Simplified spectral centroid calculation
    // In a full implementation, you'd use FFT
    let weightedSum = 0;
    let magnitudeSum = 0;
    
    for (let i = 0; i < audioData.length; i++) {
      const magnitude = Math.abs(audioData[i]);
      const frequency = (i / audioData.length) * (sampleRate / 2);
      weightedSum += frequency * magnitude;
      magnitudeSum += magnitude;
    }
    
    return magnitudeSum > 0 ? weightedSum / magnitudeSum : 0;
  }

  /**
   * Calculate spectral rolloff (simplified)
   */
  private calculateSpectralRolloff(audioData: Float32Array, sampleRate: number): number {
    // Simplified spectral rolloff calculation
    let totalEnergy = 0;
    const magnitudes: number[] = [];
    
    for (let i = 0; i < audioData.length; i++) {
      const magnitude = Math.abs(audioData[i]);
      magnitudes.push(magnitude);
      totalEnergy += magnitude;
    }
    
    const threshold = totalEnergy * 0.85; // 85% rolloff
    let cumulativeEnergy = 0;
    
    for (let i = 0; i < magnitudes.length; i++) {
      cumulativeEnergy += magnitudes[i];
      if (cumulativeEnergy >= threshold) {
        return (i / magnitudes.length) * (sampleRate / 2);
      }
    }
    
    return sampleRate / 2;
  }

  /**
   * Calculate overall confidence score
   */
  private calculateConfidence(rms: number, zcr: number, spectralCentroid: number, energy: number): number {
    // Normalize metrics and calculate weighted confidence
    const rmsScore = Math.min(rms / this.config.rmsThreshold, 1);
    const energyScore = Math.min(energy / this.config.energyThreshold, 1);
    const zcrScore = 1 - Math.min(zcr / this.config.zcrThreshold, 1); // Lower ZCR is better for speech
    
    const spectralScore = (spectralCentroid >= this.config.spectralCentroidMin && 
                          spectralCentroid <= this.config.spectralCentroidMax) ? 1 : 0;
    
    // Weighted average
    return (rmsScore * 0.3 + energyScore * 0.3 + zcrScore * 0.2 + spectralScore * 0.2);
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<VADConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('🔧 Audio processor configuration updated:', newConfig);
  }

  /**
   * Get current configuration
   */
  public getConfig(): VADConfig {
    return { ...this.config };
  }

  /**
   * Get current noise floor
   */
  public getNoiseFloor(): number {
    return this.noiseFloor;
  }

  /**
   * Check if currently calibrating
   */
  public isCalibrating(): boolean {
    return this.isCalibrating;
  }

  /**
   * Reset speech detection state
   */
  public reset(): void {
    this.speechStartTime = 0;
    this.lastSpeechTime = 0;
    this.consecutiveSpeechFrames = 0;
    this.consecutiveSilenceFrames = 0;
    this.gateState = 'closed';
    this.gateEnvelope = 0;
  }
}
