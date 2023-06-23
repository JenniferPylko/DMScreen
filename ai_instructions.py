import os
import logging
import glob

from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

root_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(root_dir, "audio")

if "OPENAI_API_KEY" not in os.environ:
    print("Please set the OPENAI_API_KEY environment variable to your OpenAI API key.")
    exit(1)


llm = ChatOpenAI(temperature=0, openai_api_key=os.environ["OPENAI_API_KEY"], model_name="gpt-4")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)

# read transcript from file
transcripts = glob.glob(audio_dir + "/chunk*.mp3.transcript.txt")
text = ""
for f in transcripts:
    print("Reading text from file: " + f)
    with open(f, "r") as f:
        text += f.read() + "\n"

docs = text_splitter.create_documents([text])

num_docs = len(docs)
logging.info(f"Number of documents: {num_docs}")

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