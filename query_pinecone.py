import logging
import os
import glob
import sys
import dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
import pinecone

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

root_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(root_dir, "audio")

QUERY = "Why did they go to the graveyard?"

"""
# Get --summary flag from command line
game_id = None
game_date = None
for argv in sys.argv:
    if argv == "--gameid":
        game_id = sys.argv[sys.argv.index(argv) + 1]
        next
    elif argv == "--date":
        game_date = sys.argv[sys.argv.index(argv) + 1]
        next
    elif argv == "--help":
        print("Usage: python3 save_transcript.py [--gameid <gameid>]")
        exit(0)

if game_id is None or game_date is None:
    print("Usage: python3 save_transcript.py --gameid <gameid> --date <date>")
    exit(1)
"""

model = "text-embedding-ada-002"
embed = OpenAIEmbeddings(model=model, openai_api_key=os.environ["OPENAI_API_KEY"])

index_name = "5e"
pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])

#index = pinecone.Index(index_name).delete(delete_all=True, namespace='documents')

idx = Pinecone.from_existing_index(index_name, embedding=embed)
vectorstore = Pinecone.from_existing_index(index_name, embedding=embed, namespace='sessions')
r = vectorstore.similarity_search(QUERY, k=2, namespace='sessions', filter={"game_id":'7'})
print(r)
