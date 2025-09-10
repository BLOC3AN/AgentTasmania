from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
from transformers import WhisperProcessor

model_id = "openai/whisper-tiny.en"

# Export sang ONNX
onnx_model = ORTModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    export=True,
    provider="CPUExecutionProvider"  # hoặc "CUDAExecutionProvider"
)

# Save model và processor
onnx_model.save_pretrained("./onnx-whisper-tiny")
processor = WhisperProcessor.from_pretrained(model_id)
processor.save_pretrained("./onnx-whisper-tiny")
