import tiktoken

class OpenAIHandler():
    MODEL_GPT4 = "gpt-4-0613"
    MODEL_GPT4_16 = "gpt-4-0613-16k"
    MODEL_GPT3 = "gpt-3.5-turbo-0613"
    MODEL_GPT3_16 = "gpt-3.5-turbo-16k"
    MODEL_WHISPER = "whisper-1"
    GPT_COST_INPUT = {
        MODEL_GPT4: 0.00003,
        MODEL_GPT4_16: 0.00006,
        MODEL_GPT3: 0.0000015,
        MODEL_GPT3_16: 0.000003
    }
    GPT_COST_OUTPUT = {
        MODEL_GPT4: 0.00006,
        MODEL_GPT4_16: 0.00012,
        MODEL_GPT3: 0.00002,
        MODEL_GPT3_16: 0.00004
    }
    GPT_COST_WHISPER = 0.006

    def num_tokens_from_string(string: str, encoding_name: str) -> int:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        return input_tokens * self.GPT_COST_INPUT[model] + output_tokens * self.GPT_COST_OUTPUT[model]

