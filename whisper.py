import openai
import os
import logging
import glob
import sys

from langchain import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

os.environ["OPENAP_API_KEY"] = "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"
root_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(root_dir, "audio")
llm = ChatOpenAI(temperature=0, openai_api_key=os.environ["OPENAP_API_KEY"], model_name="gpt-4")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)

# Get --summary flag from command line
summary = False
for argv in sys.argv:
    if argv == "--summary":
        summary = True
        break
    elif argv == "--help":
        print("Usage: python3 whisper.py [--summary]")
        exit(0)

# If transscript.txt does not exist, transcribe the audio file
text = ""
if summary == False:
    # scan the audio directory for audio files named chunk*.mp3
    audio_files = glob.glob(audio_dir + "/chunk*.mp3")

    # iterate over the audio files and transcribe them
    for f in audio_files:
        output_file = f + ".transcript.txt"
        if not os.path.exists(output_file):
            audio_file = open(f, "rb")
            logging.info("Transcribing audio file: " + f)
            try:
                transcript = openai.Audio.transcribe("whisper-1", audio_file)
                text = transcript.text + "\n"
                # write transcript to file
                with open(output_file, "wb") as f:
                    f.write(transcript.text.encode("utf-8"))
            except Exception as e:
                print(e)
                exit(1)


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
Write a concise summary of the following. When summarizing combat, only include the key points of
the combat. Do not include the dice rolls or the results of the dice rolls. Do not include the
narrative of the combat. Only include the key points of the combat, or funny/odd/unique moments.
"{text}"
CONCISE SUMMARY:
"""
map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])

combine_prompt = """
Write a concise summary of the following text delimited by triple backquotes.
Return your response in bullet points which covers the key points of the text.
```{text}```
BULLET POINT SUMMARY:
"""
combine_prompt_template = PromptTemplate(template=combine_prompt, input_variables=["text"])

logging.info("Loading summarization chain...")
summary_chain = load_summarize_chain(llm=llm, chain_type="map_reduce",
                                     map_prompt=map_prompt_template,
                                     combine_prompt=combine_prompt_template, verbose=True)
output = summary_chain.run(docs)
logging.info(f"Summary: {output}")

# Write summary to file
with open("summary.txt", "w") as f:
    f.write(output)