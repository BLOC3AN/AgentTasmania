/**
 * Transcription Filter for removing noise, false positives, and low-quality transcriptions
 */

export interface TranscriptionFilterConfig {
  // Confidence thresholds
  minConfidence: number;
  
  // Length constraints
  minLength: number;
  maxLength: number;
  minWords: number;
  maxWords: number;
  
  // Content filtering
  enableNoiseWordFilter: boolean;
  enableRepetitionFilter: boolean;
  enableLanguageFilter: boolean;
  
  // Timing constraints
  minDuration: number;
  maxSilenceGap: number;
  
  // Quality metrics
  minWordConfidence: number;
  maxUncertaintyRatio: number;
}

export interface FilterResult {
  isValid: boolean;
  confidence: number;
  reason?: string;
  filteredText?: string;
  metadata: {
    originalLength: number;
    wordCount: number;
    avgConfidence: number;
    hasNoiseWords: boolean;
    hasRepetition: boolean;
    qualityScore: number;
  };
}

export class TranscriptionFilter {
  private config: TranscriptionFilterConfig;
  
  // Common noise words and phrases that often appear in false transcriptions
  private readonly NOISE_WORDS = new Set([
    // Background noise transcriptions
    'subscribe', 'channel', 'like', 'comment', 'notification',
    'music', 'background', 'sound', 'noise', 'static',
    
    // Common false positives
    'uh', 'um', 'ah', 'er', 'hmm', 'mhm', 'yeah yeah yeah',
    'you know', 'i mean', 'like like like', 'so so so',
    
    // Repetitive patterns
    'the the the', 'and and and', 'is is is', 'it it it',
    'that that that', 'this this this', 'we we we',
    
    // Technical artifacts
    'beep', 'click', 'pop', 'buzz', 'hum', 'crackle',
    'interference', 'feedback', 'echo', 'reverb',
    
    // Common misheard phrases
    'thank you for watching', 'don\'t forget to subscribe',
    'hit the bell icon', 'leave a comment below',
    'check out the description', 'see you next time'
  ]);
  
  // Suspicious repetitive patterns
  private readonly REPETITION_PATTERNS = [
    /(.{1,10})\1{3,}/gi, // Same short phrase repeated 4+ times
    /(\b\w+\b)\s+\1\s+\1/gi, // Same word repeated 3+ times
    /(.{20,})\1{2,}/gi, // Same longer phrase repeated 3+ times
  ];
  
  // Language quality patterns
  private readonly QUALITY_PATTERNS = {
    // Good indicators
    goodPatterns: [
      /\b(what|how|when|where|why|who)\b/gi, // Question words
      /\b(please|thank|sorry|excuse)\b/gi, // Polite words
      /\b(can|could|would|should|will|shall)\b/gi, // Modal verbs
      /[.!?]/, // Proper punctuation
    ],
    
    // Bad indicators
    badPatterns: [
      /^[a-z\s]{1,5}$/i, // Very short, low-content
      /^\W+$/, // Only punctuation/symbols
      /(.)\1{5,}/, // Character repeated 6+ times
      /^(yeah|yes|no|ok|okay|right|sure|well|so|and|but|or|the|a|an|is|are|was|were|have|has|had|do|does|did|will|would|could|should|can|may|might)\s*$/i, // Single common words
    ]
  };

  constructor(config?: Partial<TranscriptionFilterConfig>) {
    this.config = {
      // Default configuration
      minConfidence: 0.7,
      minLength: 10,
      maxLength: 1000,
      minWords: 2,
      maxWords: 100,
      enableNoiseWordFilter: true,
      enableRepetitionFilter: true,
      enableLanguageFilter: true,
      minDuration: 500, // ms
      maxSilenceGap: 2000, // ms
      minWordConfidence: 0.6,
      maxUncertaintyRatio: 0.4,
      ...config
    };
  }

  /**
   * Filter transcription and return validation result
   */
  public filterTranscription(
    text: string, 
    confidence: number = 1.0, 
    duration?: number,
    wordConfidences?: number[]
  ): FilterResult {
    const originalLength = text.length;
    const words = this.extractWords(text);
    const wordCount = words.length;
    
    // Initialize metadata
    const metadata = {
      originalLength,
      wordCount,
      avgConfidence: confidence,
      hasNoiseWords: false,
      hasRepetition: false,
      qualityScore: 0
    };

    // Basic validation checks
    const basicValidation = this.performBasicValidation(text, confidence, duration);
    if (!basicValidation.isValid) {
      return {
        ...basicValidation,
        metadata: { ...metadata, qualityScore: 0 }
      };
    }

    // Content filtering
    let filteredText = text;
    let currentConfidence = confidence;

    // 1. Noise word filtering
    if (this.config.enableNoiseWordFilter) {
      const noiseResult = this.filterNoiseWords(filteredText, words);
      filteredText = noiseResult.text;
      currentConfidence *= noiseResult.confidenceMultiplier;
      metadata.hasNoiseWords = noiseResult.hasNoiseWords;
    }

    // 2. Repetition filtering
    if (this.config.enableRepetitionFilter) {
      const repetitionResult = this.filterRepetitions(filteredText);
      filteredText = repetitionResult.text;
      currentConfidence *= repetitionResult.confidenceMultiplier;
      metadata.hasRepetition = repetitionResult.hasRepetition;
    }

    // 3. Language quality assessment
    if (this.config.enableLanguageFilter) {
      const qualityResult = this.assessLanguageQuality(filteredText);
      currentConfidence *= qualityResult.confidenceMultiplier;
      metadata.qualityScore = qualityResult.score;
    }

    // 4. Word-level confidence filtering
    if (wordConfidences && wordConfidences.length > 0) {
      const wordConfidenceResult = this.filterByWordConfidence(filteredText, wordConfidences);
      filteredText = wordConfidenceResult.text;
      currentConfidence *= wordConfidenceResult.confidenceMultiplier;
      metadata.avgConfidence = wordConfidenceResult.avgConfidence;
    }

    // Final validation
    const finalWords = this.extractWords(filteredText);
    const isValid = this.isFinalResultValid(filteredText, finalWords, currentConfidence);

    return {
      isValid,
      confidence: currentConfidence,
      filteredText: isValid ? filteredText : undefined,
      reason: isValid ? undefined : this.getFilterReason(filteredText, finalWords, currentConfidence),
      metadata
    };
  }

  /**
   * Perform basic validation checks
   */
  private performBasicValidation(text: string, confidence: number, duration?: number): { isValid: boolean; reason?: string } {
    // Confidence check
    if (confidence < this.config.minConfidence) {
      return { isValid: false, reason: `Low confidence: ${confidence.toFixed(2)} < ${this.config.minConfidence}` };
    }

    // Length checks
    if (text.length < this.config.minLength) {
      return { isValid: false, reason: `Too short: ${text.length} < ${this.config.minLength} characters` };
    }

    if (text.length > this.config.maxLength) {
      return { isValid: false, reason: `Too long: ${text.length} > ${this.config.maxLength} characters` };
    }

    // Duration check
    if (duration !== undefined && duration < this.config.minDuration) {
      return { isValid: false, reason: `Too short duration: ${duration}ms < ${this.config.minDuration}ms` };
    }

    return { isValid: true };
  }

  /**
   * Filter out noise words and phrases
   */
  private filterNoiseWords(text: string, words: string[]): { text: string; confidenceMultiplier: number; hasNoiseWords: boolean } {
    let hasNoiseWords = false;
    let noiseWordCount = 0;

    // Check for noise words
    const filteredWords = words.filter(word => {
      const isNoise = this.NOISE_WORDS.has(word.toLowerCase());
      if (isNoise) {
        hasNoiseWords = true;
        noiseWordCount++;
      }
      return !isNoise;
    });

    // Check for noise phrases
    let filteredText = filteredWords.join(' ');
    for (const noisePhrase of this.NOISE_WORDS) {
      if (noisePhrase.includes(' ') && text.toLowerCase().includes(noisePhrase)) {
        filteredText = filteredText.replace(new RegExp(noisePhrase, 'gi'), '');
        hasNoiseWords = true;
        noiseWordCount += noisePhrase.split(' ').length;
      }
    }

    // Calculate confidence multiplier based on noise ratio
    const noiseRatio = noiseWordCount / Math.max(words.length, 1);
    const confidenceMultiplier = Math.max(0.1, 1 - noiseRatio);

    return {
      text: filteredText.trim(),
      confidenceMultiplier,
      hasNoiseWords
    };
  }

  /**
   * Filter repetitive patterns
   */
  private filterRepetitions(text: string): { text: string; confidenceMultiplier: number; hasRepetition: boolean } {
    let filteredText = text;
    let hasRepetition = false;

    for (const pattern of this.REPETITION_PATTERNS) {
      const matches = text.match(pattern);
      if (matches && matches.length > 0) {
        hasRepetition = true;
        // Replace repetitions with single occurrence
        filteredText = filteredText.replace(pattern, '$1');
      }
    }

    const confidenceMultiplier = hasRepetition ? 0.5 : 1.0;

    return {
      text: filteredText,
      confidenceMultiplier,
      hasRepetition
    };
  }

  /**
   * Assess language quality
   */
  private assessLanguageQuality(text: string): { score: number; confidenceMultiplier: number } {
    let score = 0.5; // Base score

    // Check for good patterns
    for (const pattern of this.QUALITY_PATTERNS.goodPatterns) {
      if (pattern.test(text)) {
        score += 0.1;
      }
    }

    // Check for bad patterns
    for (const pattern of this.QUALITY_PATTERNS.badPatterns) {
      if (pattern.test(text)) {
        score -= 0.2;
      }
    }

    // Normalize score
    score = Math.max(0, Math.min(1, score));

    const confidenceMultiplier = Math.max(0.2, score);

    return { score, confidenceMultiplier };
  }

  /**
   * Filter based on word-level confidence scores
   */
  private filterByWordConfidence(text: string, wordConfidences: number[]): { 
    text: string; 
    confidenceMultiplier: number; 
    avgConfidence: number 
  } {
    const words = this.extractWords(text);
    const minLength = Math.min(words.length, wordConfidences.length);
    
    const filteredWords: string[] = [];
    let totalConfidence = 0;
    let validWords = 0;

    for (let i = 0; i < minLength; i++) {
      const wordConfidence = wordConfidences[i];
      if (wordConfidence >= this.config.minWordConfidence) {
        filteredWords.push(words[i]);
        totalConfidence += wordConfidence;
        validWords++;
      }
    }

    const avgConfidence = validWords > 0 ? totalConfidence / validWords : 0;
    const retentionRatio = validWords / Math.max(words.length, 1);
    const confidenceMultiplier = Math.max(0.1, retentionRatio);

    return {
      text: filteredWords.join(' '),
      confidenceMultiplier,
      avgConfidence
    };
  }

  /**
   * Final validation of filtered result
   */
  private isFinalResultValid(text: string, words: string[], confidence: number): boolean {
    // Re-check basic constraints after filtering
    if (text.length < this.config.minLength) return false;
    if (words.length < this.config.minWords) return false;
    if (words.length > this.config.maxWords) return false;
    if (confidence < this.config.minConfidence) return false;

    // Check if text is meaningful
    const meaningfulWords = words.filter(word => 
      word.length > 2 && 
      !/^\d+$/.test(word) && 
      !this.NOISE_WORDS.has(word.toLowerCase())
    );

    return meaningfulWords.length >= Math.max(1, this.config.minWords - 1);
  }

  /**
   * Get reason for filtering
   */
  private getFilterReason(text: string, words: string[], confidence: number): string {
    if (text.length < this.config.minLength) return 'Filtered text too short';
    if (words.length < this.config.minWords) return 'Too few meaningful words';
    if (words.length > this.config.maxWords) return 'Too many words';
    if (confidence < this.config.minConfidence) return 'Low confidence after filtering';
    return 'Failed quality assessment';
  }

  /**
   * Extract words from text
   */
  private extractWords(text: string): string[] {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 0);
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<TranscriptionFilterConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('🔧 Transcription filter configuration updated:', newConfig);
  }

  /**
   * Get current configuration
   */
  public getConfig(): TranscriptionFilterConfig {
    return { ...this.config };
  }

  /**
   * Add custom noise words
   */
  public addNoiseWords(words: string[]): void {
    words.forEach(word => this.NOISE_WORDS.add(word.toLowerCase()));
    console.log(`📝 Added ${words.length} custom noise words`);
  }

  /**
   * Remove noise words
   */
  public removeNoiseWords(words: string[]): void {
    words.forEach(word => this.NOISE_WORDS.delete(word.toLowerCase()));
    console.log(`🗑️ Removed ${words.length} noise words`);
  }

  /**
   * Get current noise words list
   */
  public getNoiseWords(): string[] {
    return Array.from(this.NOISE_WORDS);
  }
}
