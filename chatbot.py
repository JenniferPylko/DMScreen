import os
from typing import List
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Pinecone
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import (
    HumanMessage,
    SystemMessage,
    FunctionMessage
)
import pinecone
import json

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
        
        self.functions = [
            {
                "name": "help",
                "description": "Get help with DM Screen, and its capabilities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool": {
                            "type": "string",
                            "enum": ["help"],
                            "description": "The tool to get help with"
                        }
                    },
                    "required": ["tool"]
                },
            },
            {
                "name":"query_vectorstore",
                "description": "Get context from the vectorstore to answer the question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A well formatted query to search the vectorstore with"
                        }
                    },
                    "required": ["query"]
                },
            },
            {
                "name":"final_answer",
                "description": "Show the final answer to the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "The final answer to the user's question"
                        },
                        "source": {
                            "type": "string",
                            "description": "The source of the answer"
                        },
                        "people": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "The name of a person in the answer"
                            }
                        }
                    },
                    "required": ["answer", "source", "people"]
                },
            }
        ]


    def show_help_message(self):
        return """
        Here are the tools I can use:
        - help: Get help with the bot, and its capabilities
        - doc search: Chat with Chat about D&D based on all of the published D&D books, as well as lots of 3rd party content
        """

    def send_message(self, query, temperature=0.0, model=None, titles=[]):
        if model is None:
            model_name = self.__default_model

        messages = [SystemMessage(content="""You are an expert on Dungeons and Dragons 5e. Your goal
            is to provide an answer to the user's question, as it pertains to D&D. You should give
            factual answers only based on the provided documentation, and not your own opinion. You
            should not provide any information that is not directly related to the user's question.
            If you do not know the answer to the question, you should say so. If your response is not
            related to D&D, you should query the vectorstore for more context.""")]

        llm = ChatOpenAI(model_name=model_name, temperature=temperature, openai_api_key=self.__openai_key)
        messages.append(HumanMessage(content=query))
        response = llm.predict_messages(messages, functions=self.functions, function_call={"name": "query_vectorstore"})
        messages.append(response)
        print(f"LLM Answer: {response}")

        if response.additional_kwargs.get("function_call"):
            function_name = response.additional_kwargs["function_call"]["name"]
            print(f"Calling function: {function_name}")
            available_functions = {
                "help": self.show_help_message,
                "query_vectorstore": self.search_vectorstore
            }

            function_to_call = available_functions.get(function_name)
            function_args = json.loads(response.additional_kwargs["function_call"]["arguments"])
            function_response = function_to_call(**function_args)
            messages.append(FunctionMessage(content=function_response, name=function_name))
            response2 = llm.predict_messages(messages, functions=self.functions, function_call={"name": "final_answer"})

            arguments2 = json.loads(response2.additional_kwargs["function_call"]["arguments"])
            print(f"LLM Answer 2: {arguments2['answer']}")
            return {
                "answer": arguments2["answer"],
                "source": arguments2["source"],
                "people": arguments2["people"]
            }
        else:
            answer = response.content
            print(f"LLM Answer: {answer}")
            return {
                "answer": answer,
                "source": "unknown",
                "people": []
            }

    def add_documents(self, loader):
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.__split_chunk_size, chunk_overlap=self.__split_chunk_overlap, separators=["\n\n", "\n", ". ", ",", " ", ""])
        texts = text_splitter.split_documents(documents)
        self.__reference_instance.add_documents(texts)

    def search_vectorstore(self, query, model_name=None, temperature=None) -> str:
        if model_name is None:
            model_name = self.__default_model
        if temperature is None:
            temperature = 0.0
        docs = self.__reference_instance.similarity_search(query, k=4)
        r = ""
        for doc in docs:
            print(doc)
            r += f"{doc.metadata['title']}\n{doc.page_content}\n\n"
        return r
    
    def run_chain(self, query, docs, model_name=None, temperature=None):
        # Note: This is a temporary function name, because I'm too high to come up with a better one right now
        llm = ChatOpenAI(model_name=model_name, temperature=temperature, openai_api_key=os.environ["OPENAI_API_KEY"])
        chain = load_qa_chain(llm, chain_type="stuff", verbose=True)
        answer = chain.run(input_documents=docs, question=query, verbose=True)
        return answer
