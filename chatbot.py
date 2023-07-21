import os
from typing import List
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Pinecone
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.callbacks import get_openai_callback
from langchain.schema import (
    HumanMessage,
    SystemMessage,
    FunctionMessage,
    AIMessage
)
import pinecone
import json
from npc import AINPC
from models import NPCs, Reminders, TokenLog
import logging
from openaihandler import OpenAIHandler

logging.basicConfig(level=logging.DEBUG, filename='webserver.log')

class ChatBot():
    __default_model = OpenAIHandler.MODEL_GPT3
    __reference_instance: Pinecone = None
    __split_chunk_size = 1000
    __split_chunk_overlap = 100

    def __init__(self, game_id, openai_key:str, pinecone_api_key:str, pinecone_environment:str, model_name=None, pinecone_index: str='5e'):
        self.__default_model = model_name if model_name is not None else self.__default_model
        self.__pinecone_index = pinecone_index
        self.__openai_key = openai_key
        self.__game_id = game_id

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
                "name":"query_documentation",
                "description": "Call this function to query the documentation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question asked by the user"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name":"query_sessions",
                "description": "Call this function to query the previous session notes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question asked by the user"
                        }
                    },
                    "required": ["query"]
                }
            },
            AINPC.create_npc_openai_functions,
            {
                "name": "create_reminder",
                "description": "Create a reminder for the DM",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title or description of the reminder"
                        },
                        "details": {
                            "type": "string",
                            "description": "Detailed description of the reminder"
                        },
                        "trigger": {
                            "type": "string",
                            "description": "The trigger for the reminder"
                        },
                    },
                    "required": ["title", "details", "trigger"]
                }
            },
        ]
    
        self.function_final_answer = [
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
                }
            }
        ]

    def show_help_message(self, tool:str = None):
        return """
        Here are the tools I can use:
        - help: Get help with the bot, and its capabilities
        - doc search: Chat with Chat about D&D based on all of the published D&D books, as well as lots of 3rd party content
        """

    def create_npc(self, **kwargs):
        npc = NPCs().add_npc(kwargs["name"], attributes=kwargs)
        return f"Created NPC: {npc.data['name']}" if npc is not None else "Failed to create NPC"

    def send_message(self, query, temperature=0.0, model=None, titles=[]):
        model = model if model is not None else self.__default_model

        messages = [SystemMessage(content="""You are an expert on Dungeons and Dragons 5e, and as
            assistant to the Dungeon Master. Your goal is to provide an answer to the user's question,
            as it pertains to D&D or the session notes. You should give
            factual answers only based on the provided documentation, and not your own opinion. You
            should not provide any information that is not directly related to the user's question.
            If you do not know the answer to the question, you should say so. You must always
            call a function as a response.""")]

        llm = ChatOpenAI(model_name=model, temperature=temperature, openai_api_key=self.__openai_key)
        messages.append(HumanMessage(content=query))
        with get_openai_callback() as cb:
            response = llm.predict_messages(messages, functions=self.functions)
            TokenLog().add("Chat Bot", cb.prompt_tokens, cb.completion_tokens, cb.total_cost)

        messages.append(response)

        if response.additional_kwargs.get("function_call"):
            function_name = response.additional_kwargs["function_call"]["name"]
            logging.debug(f"Calling function: {function_name}")
            available_functions = {
                "help": self.show_help_message,
                "query_documentation": self.search_vectorstore,
                "generate_npc": self.create_npc,
                "query_sessions": self.search_sessions,
                "create_reminder": self.create_reminder
            }

            function_to_call = available_functions.get(function_name)
            function_args = json.loads(response.additional_kwargs["function_call"]["arguments"])
            function_response = function_to_call(**function_args)
            messages.append(FunctionMessage(content=function_response, name=function_name))
            response2 = ""
            if (function_name == "query_documentation") or (function_name == "query_sessions"):
                with get_openai_callback() as cb:
                    response2 = llm.predict_messages(messages, functions=self.function_final_answer, function_call={"name": "final_answer"})
                    TokenLog().add("Query Vectorstore", cb.prompt_tokens, cb.completion_tokens, cb.total_cost)

                arguments2 = json.loads(response2.additional_kwargs["function_call"]["arguments"])
                logging.debug(f"LLM Answer 2: {arguments2['answer']}")
                return {
                    "answer": arguments2["answer"] if arguments2["answer"] is not None else "I don't know the answer to that question",
                    "source": arguments2["source"] if arguments2["source"] is not None else "unknown",
                    "people": arguments2["people"] if arguments2["people"] is not None else [],
                }
            else:
                # We don't need gpt4 for this part, so we can just use the default model
                with get_openai_callback() as cb:
                    response2 = llm.predict_messages(messages, model=self.__default_model)
                    TokenLog().add("Chat Function: " + function_name, cb.prompt_tokens, cb.completion_tokens, cb.total_cost)
                r = {
                    "answer": response2.content,
                    "source": "Chad",
                    "people": []
                }
                if function_name == "generate_npc":
                    r["frontend"] = ["refresh_npc_list"]
                elif function_name == "create_reminder":
                    r["frontend"] = ["refresh_reminders"]
                return r
        else:
            answer = response.content
            logging.debug(f"LLM Answer: {answer}")
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
        docs = self.__reference_instance.similarity_search(query, k=4, namespace='srd')
        r = ""
        for doc in docs:
            #print(doc)
            #r += f"{doc.metadata['title']}\n{doc.page_content}\n\n"
            r += f"Dungeons and Dragons SRD - Page: {doc.metadata['page']}\n{doc.page_content}\n\n"

        return r

    def search_sessions(self, query, model_name=None, temperature=None) -> str:
        if model_name is None:
            model_name = self.__default_model
        if temperature is None:
            temperature = 0.0
        session_notes = self.__reference_instance.similarity_search(query, k=4, namespace='sessions', filter={"game_id": str(self.__game_id)})
        r = ""
        for note in session_notes:
            r += f"Session Notes - Date: {note.metadata['game_date']}\n{note.page_content}\n\n"        
        return r
    
    def create_reminder(self, title, details, trigger):
        reminder = Reminders(self.__game_id).add(title, details, trigger)
        if (reminder is None):
            return "Failed to create reminder"
        
        return f"Reminder created: {title}"

    def run_chain(self, query, docs, model_name=None, temperature=None):
        # Note: This is a temporary function name, because I'm too high to come up with a better one right now
        llm = ChatOpenAI(model_name=model_name, temperature=temperature, openai_api_key=os.environ["OPENAI_API_KEY"])
        chain = load_qa_chain(llm, chain_type="stuff", verbose=True)
        answer = chain.run(input_documents=docs, question=query, verbose=True)
        return answer
