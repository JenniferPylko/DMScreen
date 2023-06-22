import os
from typing import List
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Pinecone
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
import pinecone

class ReferenceQuery(BaseModel):
    answer: str = Field(description="answer to the users's question")
    source: str = Field(description="The source of the answer")
    nouns: List[str] = Field(description="A list of people's proper names in the answer. Do not include locations, spells nor groups of people")

class ChatBot():
    __root_dir = os.path.dirname(os.path.abspath(__file__))
    __default_model = "gpt-3.5-turbo-0613"
    __reference_instance = None
    __reference_parser = None
    __split_chunk_size = 1000
    __split_chunk_overlap = 100

    def __init__(self, openai_key:str, pinecone_api_key:str, pinecone_environment:str, model_name=None, pinecone_index='5e'):
        self.__default_model = model_name if model_name is not None else self.__default_model
        self.__pinecone_index = pinecone_index
        self.__openai_key = openai_key

        embeddings = OpenAIEmbeddings(openai_api_key=self.__openai_key)
        pinecone.init(api_key=pinecone_api_key, environment=pinecone_environment)

        self.__reference_instance = Pinecone.from_existing_index(self.__pinecone_index, embedding=embeddings)
        self.__reference_parser = PydanticOutputParser(pydantic_object=ReferenceQuery)
        
        self.__reference_prompt = PromptTemplate(
            template="""You are an expert on Dungeons and Dragons 5e. Your goal is to provide an
            answer to the user's question, as it pertains to D&D. You should give factual answers only based
            on the provided documentation, and not your own opinion. You should not provide any information
            that is not directly related to the user's question. If you do not know the answer to the question,
            you should say so.

            {format_instructions}
            {query}""",
            input_variables=["query"],
            partial_variables={"format_instructions": self.__reference_parser.get_format_instructions()}
        )



    def send_message(self, query, temperature=0.0, model=None, titles=[]) -> ReferenceQuery:
        if model is None:
            model_name = self.__default_model

        _input = self.__reference_prompt.format_prompt(query=query)
        title_ors = [{"$eq": title} for title in titles]
 
        docs = self.__reference_instance.similarity_search(_input.to_messages()[0].content, k=4, filter={
            "collection": "core",
            "title": {"$or": title_ors}
        })

        llm = ChatOpenAI(model_name=model_name, temperature=temperature, openai_api_key=self.__openai_key)
        chain = load_qa_chain(llm, chain_type="stuff", verbose=True)
        answer = chain.run(input_documents=docs, question=_input.to_messages()[0].content, verbose=False)
        print(answer)

        try:
            parsed_answer = self.__reference_parser.parse(answer)
        except:
            parsed_answer = ReferenceQuery(answer=answer, source="Unknown", nouns=[])

        return parsed_answer

    def add_documents(self, loader):
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.__split_chunk_size, chunk_overlap=self.__split_chunk_overlap, separators=["\n\n", "\n", ". ", ",", " ", ""])
        texts = text_splitter.split_documents(documents)
        self.__reference_instance.add_documents(texts)

