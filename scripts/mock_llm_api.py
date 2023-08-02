from gpt4all import GPT4All, Embed4All

class LLMAPI:
    def __init__(self):
        self.model = model = GPT4All("ggml-model-gpt4all-falcon-q4_0.bin")
        self.embedder = Embed4All()

    def completion_request(self, prompt, max_tokens):
        output = self.model.generate(prompt, max_tokens=max_tokens)
        return output

    def embedding_request(self, input):
        embedding = self.embedder.embed(input)
        return embedding

llm_api = LLMAPI()