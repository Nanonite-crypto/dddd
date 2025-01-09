import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained("THUDM/glm-4-9b-chat-1m", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    "THUDM/glm-4-9b-chat-1m",
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True
).to(device).eval()

query = "你好"

inputs = tokenizer.apply_chat_template(
    [{"role": "user", "content": query}],
    add_generation_prompt=True,
    tokenize=True,
    return_tensors="pt",
    return_dict=True
)
inputs = inputs.to(device)

gen_kwargs = {"max_length": 2500, "do_sample": True, "top_k": 1}
with torch.no_grad():
    outputs = model.generate(**inputs, **gen_kwargs)
    outputs = outputs[:, inputs['input_ids'].shape[1]:]
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(response)