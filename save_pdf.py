import logging
import os
import glob
import sys
import dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.document_loaders import PyPDFLoader
import pinecone
import re

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

root_dir = os.path.dirname(os.path.abspath(__file__))
docs_dir = os.path.join(root_dir, "docs")

file = None
for argv in sys.argv:
    if argv == "--file":
        file = sys.argv[sys.argv.index(argv) + 1]
        next

if file is None:
    print("Usage: python3 save_pdf.py --file <file>")
    exit(1)

if not os.path.isfile(file):
    print("File not found: " + file)
    print("Usage: python3 save_pdf.py --file <file>")
    exit(1)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)

loader = PyPDFLoader(file)
pages = loader.load_and_split(text_splitter=text_splitter) 
for page in pages:
    page.page_content = re.sub(r'[^\x00-\x7F]+', '', page.page_content)
    page.page_content = re.sub(r'\t+', '', page.page_content)
    page.page_content = re.sub(r'\r+', '', page.page_content)
print(str(len(pages)) + " pages loaded")
print(pages[0])
texts = [page.page_content for page in pages]
record_metadatas = [{"page": page.metadata['page']} for page in pages]

model = "text-embedding-ada-002"
embed = OpenAIEmbeddings(model=model, openai_api_key=os.environ["OPENAI_API_KEY"])

index_name = "5e"
pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])

#index = pinecone.Index(index_name).delete(delete_all=True, namespace='documents')

idx = Pinecone.from_existing_index(index_name, embedding=embed)
r = idx.add_texts(texts=texts, metadatas=record_metadatas, embedding=embed.embed_documents(texts), namespace='srd')
#print(r)

#vectorstore = Pinecone.from_existing_index(index_name, embedding=embed, namespace='documents')
#query = "Is it a good week?"
#r = vectorstore.similarity_search(query, k=1, namespace='documents')
#print(r)
