import torch
from TTS.api import TTS
import gradio as gr

device = "cuda" if torch.cuda.is_available() else "cpu"

def generate_audio(text="Hello"):
    tts = TTS(model_name="voice_conversion_models/multilingual/vctk/freevc24", progress_bar=False, gpu=True if device == "cuda" else False).to(device)
    
    if not hasattr(tts, 'speakers') or not tts.speakers:
        print("No speakers found, proceeding without speaker selection.")
        tts.tts_to_file(text=text, file_path="outputs/output.wav")
    else:
        speaker_name = tts.speakers[0].name
        speaker_id = tts.speakers[0].id
        tts.tts_to_file(text=text, file_path="outputs/output.wav", speaker=speaker_name, speaker_id=speaker_id)
    
    return "outputs/output.wav"

print(generate_audio())