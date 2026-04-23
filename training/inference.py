import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

class QwenInferencer:
    def __init__(self, model_path: str):
        self.model_path = model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"path does not exist: {model_path}")
        
        print(f"正在从 {model_path} 加载模型，这可能需要几分钟...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        
        # 加载模型核心逻辑
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            device_map="auto", # 自动分配显存，这是工程化的关键
            trust_remote_code=True
        )

    def chat(self, prompt: str, history: list = None):
        if history is None:
            history = []
        
        # 1. 构造符合 Qwen 模板的消息格式
        messages = history + [{"role": "user", "content": prompt}]
        
        # 2. 请补全使用 tokenizer 应用聊天模板的逻辑
        # 提示：使用 apply_chat_template 方法，设置 add_generation_prompt=True
        text = self.tokenizer.apply_chat_template(
            conversation=messages, 
            tokenize=False, 
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        # 3. 设置流式传输器 (TextIteratorStreamer)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        # 4. 在后台线程运行生成，以实现流式输出效果
        generation_kwargs = dict(model_inputs, streamer=streamer, max_new_tokens=2048)
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        # 5. 请补全从 streamer 中逐词打印输出的优雅逻辑
        print("Assistant: ", end="")
        full_response = ""
        for new_text in streamer:
            print(new_text, end="", flush=True)
            full_response += new_text
        print("\n")

        # 6. 工程优化：手动清理一下显存缓存（可选但推荐）
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return full_response

if __name__ == "__main__":
    MODEL_PATH = "/root/autodl-tmp/Qwen2.5-7B-paper2Xcode"
    bot = QwenInferencer(MODEL_PATH)
    
    chat_history = []
    print("已进入对话模式（输入 'exit' 退出）")
    while True:
        query = input("User: ")
        if query.strip().lower() == "exit":
            break
        response = bot.chat(query, chat_history)
        chat_history.append({"role": "user", "content": query})
        chat_history.append({"role": "assistant", "content": response})
