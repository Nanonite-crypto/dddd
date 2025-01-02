import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf

device = "cuda:0" if torch.cuda.is_available() else "cpu"

model = ParlerTTSForConditionalGeneration.from_pretrained("parler-tts/parler-tts-mini-v1").to(device)
tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-mini-v1")

prompt = "Doesn't that feel kind-off weird?"
description = "Mira is a sophisticated British male voice, calm yet witty, with clear, measured enunciation, perfect for a high-tech AI assistant. Her tone is very low, yet cheerful."

description_tokens = tokenizer(
    description,
    return_tensors="pt",
    padding=True,
    return_attention_mask=True
)
prompt_tokens = tokenizer(
    prompt,
    return_tensors="pt",
    padding=True,
    return_attention_mask=True
)

generation = model.generate(
    attention_mask=description_tokens.attention_mask.to(device),
    input_ids=description_tokens.input_ids.to(device),
    prompt_input_ids=prompt_tokens.input_ids.to(device),
    prompt_attention_mask=prompt_tokens.attention_mask.to(device)
)
audio_arr = generation.cpu().numpy().squeeze()
sf.write("parler_tts_out.wav", audio_arr, model.config.sampling_rate)