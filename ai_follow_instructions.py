import openai
import os
import logging
import glob
import sys

from langchain import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

root_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(root_dir, "audio")
llm = ChatOpenAI(temperature=0, openai_api_key=os.environ["OPENAP_API_KEY"], model_name="gpt-3.5-turbo")

instrunctions_path = os.path.join(root_dir, "ai_instructions.txt")
instructions = ""
if os.path.exists(instrunctions_path):
    with open(instrunctions_path, "r") as f:
        instructions += f.read()

print("Instructions: " + instructions)

map_prompt = """
You are an Artificial Intelligence named Craig. You are reading part of a transcript of a a Dungeons
and Dragons sessions. Find all instructions for you, the AI, to follow, and infer the opinions of the
speakers of you. If the speaker does not have instructions for you, simply state "No instructions for
Craig." If the speaker does not have an opinion of you, simply state "No opinion of Craig."

"{text}"
CONCISE SUMMARY:
"""
map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])

combine_prompt = """
The following text delimited by triple backquotes is a summary of the instructions and opinions
a group of people have about an AI named Craig. Give me a concise list of the instructions and
opinions found in the text. Return your response in a bullet point list.
```{text}```
BULLET POINT LIST:
"""
combine_prompt_template = PromptTemplate(template=combine_prompt, input_variables=["text"])

logging.info("Loading summarization chain...")
summary_chain = load_summarize_chain(llm=llm, chain_type="map_reduce",
                                     map_prompt=map_prompt_template,
                                     combine_prompt=combine_prompt_template, verbose=True)
output = summary_chain.run(docs)
logging.info(f"Summary: {output}")

# Write summary to file
with open("ai_instructions.txt", "w") as f:
    f.write(output)