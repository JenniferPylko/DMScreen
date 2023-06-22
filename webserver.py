import os
import time
import pathlib
import json
import logging
import sqlite3
import pinecone
import openai
import requests

import dmscreenxml
from models import NPC, NPCs, GameNotes, Game

from typing import List

from flask import Flask, render_template, request, make_response

from dotenv import dotenv_values, load_dotenv

from watchdog.observers import Observer

from langchain.document_loaders import TextLoader
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma, Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
from langchain.document_loaders import UnstructuredPDFLoader
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.llms import OpenAI
from pydantic import BaseModel, Field, validator
from langchain.chains.question_answering import load_qa_chain

logging.basicConfig(level=logging.DEBUG)

"""Global Variables"""

""" FLAGS """
ENABLE_CHATBOT = True

""" CONSTANTS """
DIR_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR_DOCS = os.path.join(DIR_ROOT, 'docs')
DIR_PERSIST = os.path.join(DIR_ROOT, 'db')
DIR_NOTES = os.path.join(DIR_ROOT, 'notes')
DIR_XML = os.path.join(DIR_ROOT, 'xml')

#model_name = 'gpt-4'
model_name = 'gpt-3.5-turbo-16k'
reference_instance = None
notes_instance = None
game = None
game_dir = None
game_persist_dir = None

""" FLASK """
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

if "OPENAI_API_KEY" not in os.environ:
    print("Please set the OPEN_API_KEY environment variable to your OpenAI API key.")
    exit(1)


class ReferenceQuery(BaseModel):
    answer: str = Field(description="answer to the users's question")
    source: str = Field(description="The source of the answer")
    nouns: List[str] = Field(description="A list of people's proper names in the answer. Do not include locations, spells nor groups of people")

class NotesSummary(BaseModel):
    answer: str = Field(description="answer to the users's question")
    nouns: List[str] = Field(description="A list of people's proper names in the answer. Do not include locations, spells nor groups of people")

class NameList(BaseModel):
    names: List[str] = Field(description="A list of names")

class NPCSummary(BaseModel):
    summary: str = Field(description="A summary of the npc")

class NPCQuery(BaseModel):
    name: str = Field(description="The name of the NPC")
    race: str = Field(description="The race of the NPC")
    npc_class: str = Field(description="The class of the NPC")
    background: str = Field(description="The background of the NPC")
    alignment: str = Field(description="The alignment of the NPC")
    gender: str = Field(description="The NPC's gender")
    age: str = Field(description="The NPC's age")
    height: str = Field(description="The NPC's height")
    weight: str = Field(description="The NPC's weight")
    hair: str = Field(description="The NPC's hair color")
    eyes: str = Field(description="The NPC's eye color")
    eyes_description: str = Field(description="A description of the NPC's eyes other than color")
    hair_style: str = Field(description="The NPC's hair style")
    ears: str = Field(description="The NPC's ear shape")
    nose: str = Field(description="The NPC's nose shape")
    mouth: str = Field(description="The NPC's mouth shape")
    chin: str = Field(description="The NPC's chin shape")
    mouth: str = Field(description="The NPC's mouth shape")
    features: str = Field(description="The NPC's distinguishing features")
    flaws: str = Field(description="The NPC's flaws")
    ideals: str = Field(description="The NPC's ideals")
    bonds: str = Field(description="The NPC's bonds")
    personality: str = Field(description="The NPC's personality")
    mannerisms: str = Field(description="The NPC's mannerisms")
    talents: str = Field(description="The NPC's talents")
    abilities: str = Field(description="The NPC's abilities")
    skills: str = Field(description="The NPC's skills")
    languages: str = Field(description="The NPC's languages")
    inventory: str = Field(description="What they NPC has on their person")
    body: str = Field(description="The NPC's body type")
    clothing: str = Field(description="The NPC's clothing")
    hands: str = Field(description="The NPC's hand shape")
    jewelry: str = Field(description="The NPC's jewelry")
    voice: str = Field(description="The NPC's voice")
    attitude: str = Field(description="The NPC's current attitude")
    deity: str = Field(description="The NPC's deity")
    occupation: str = Field(description="The NPC's occupation")
    wealth: str = Field(description="The NPC's wealth")
    family: str = Field(description="The NPC's family connections")
    faith: str = Field(description="The NPC's strength of faith")
    summary: str = Field(description="A summary of the NPC")

class NPCKeyQuery(BaseModel):
    value: str = Field(description="The new value of the key")

reference_parser = PydanticOutputParser(pydantic_object=ReferenceQuery)
notes_summary_parser = PydanticOutputParser(pydantic_object=NotesSummary)
names_parser = PydanticOutputParser(pydantic_object=NameList)
npc_parser = PydanticOutputParser(pydantic_object=NPCQuery)
npc_summary_parser = PydanticOutputParser(pydantic_object=NPCSummary)
npc_key_parser = PydanticOutputParser(pydantic_object=NPCKeyQuery)

reference_prompt = PromptTemplate(
    template="""You are an expert on Dungeons and Dragons 5e. Your goal is to provide an
    answer to the user's question, as it pertains to D&D. You should give factual answers only based
    on the provided documentation, and not your own opinion. You should not provide any information
    that is not directly related to the user's question. If you do not know the answer to the question,
    you should say so.

    {format_instructions}
    {query}""",
    input_variables=["query"],
    partial_variables={"format_instructions": reference_parser.get_format_instructions()}
)

notes_prompt = PromptTemplate(
    template="""You are a High Fantasy Storyteller, like George R.R. Martin, Robert Jordan, or J.R.R. Tolkein. Give me a summary of the following game session notes as though they were a part of an epic story. Including any important NPCs, locations, and events. {format_instructions}\n\n{notes}""",
    input_variables=["notes"],
    partial_variables={"format_instructions": notes_summary_parser.get_format_instructions()}
)

names_prompt = PromptTemplate(
    template="""Give me a list of {names_need} names appropriate for a Dungeons and Dragon fantasy setting. {format_instructions}""",
    input_variables=["names_need"],
    partial_variables={"format_instructions": names_parser.get_format_instructions()}
)

npc_prompt = PromptTemplate(
    template="""Create a NPC for Dungeons and Dragons 5e whose name is {name}. {format_instructions}""",
    input_variables=["name"],
    partial_variables={"format_instructions": npc_parser.get_format_instructions()}
)

npc_summary_prompt = PromptTemplate(
    template="""Give me a summary of the following NPC. {format_instructions}\n
    Name: {name}
    Class: {npc_class}
    Background: {background}
    Alignment: {alignment}
    Gender: {gender}
    Age: {age}
    Height: {height}
    Weight: {weight}
    Hair: {hair}
    Eyes: {eyes}
    Eyes Description: {eyes_description}
    Hair Style: {hair_style}
    Ears: {ears}
    Nose: {nose}
    Mouth: {mouth}
    Chin: {chin}
    Mouth: {mouth}
    Features: {features}
    Flaws: {flaws}
    Ideals: {ideals}
    Bonds: {bonds}
    Personality: {personality}
    Mannerisms: {mannerisms}
    Talents: {talents}
    Abilities: {abilities}
    Skills: {skills}
    Languages: {languages}
    Inventory: {inventory}
    Body: {body}
    Clothing: {clothing}
    Hands: {hands}
    Jewelry: {jewelry}
    Voice: {voice}
    Attitude: {attitude}
    Deity: {deity}
    Occupation: {occupation}
    Wealth: {wealth}
    Family: {family}
    Faith: {faith}
    """,
    input_variables=["name", "npc_class", "background", "alignment", "gender", "age", "height", "weight", "hair", "eyes", "eyes_description", "hair_style", "ears", "nose", "mouth", "chin", "mouth", "features", "flaws", "ideals", "bonds", "personality", "mannerisms", "talents", "abilities", "skills", "languages", "inventory", "body", "clothing", "hands", "jewelry", "voice", "attitude", "deity", "occupation", "wealth", "family", "faith"],
    partial_variables={"format_instructions": npc_summary_parser.get_format_instructions()}
)

npc_key_prompt = PromptTemplate(
    template="""Create a new value for the following field. The value should make sense in the context
    of the NPC, and should not be the same as its original value.
    Name: {name}
    Class: {npc_class}
    Background: {background}
    Alignment: {alignment}
    Gender: {gender}
    Age: {age}
    Height: {height}
    Weight: {weight}
    Hair: {hair}
    Eyes: {eyes}
    Eyes Description: {eyes_description}
    Hair Style: {hair_style}
    Ears: {ears}
    Nose: {nose}
    Mouth: {mouth}
    Chin: {chin}
    Features: {features}
    Flaws: {flaws}
    Ideals: {ideals}
    Bonds: {bonds}
    Personality: {personality}
    Mannerisms: {mannerisms}
    Talents: {talents}
    Abilities: {abilities}
    Skills: {skills}
    Languages: {languages}
    Inventory: {inventory}
    Body: {body}
    Clothing: {clothing}
    Hands: {hands}
    Jewelry: {jewelry}
    Voice: {voice}
    Attitude: {attitude}
    Deity: {deity}
    Occupation: {occupation}
    Wealth: {wealth}
    Family: {family}
    Faith: {faith}

    Field to change: {field}
    Original Value: {original_value}
    {format_instructions}\n""",
    input_variables=["name", "npc_class", "background", "alignment", "gender", "age", "height", "weight", "hair", "eyes", "eyes_description", "hair_style", "ears", "nose", "mouth", "chin", "mouth", "features", "flaws", "ideals", "bonds", "personality", "mannerisms", "talents", "abilities", "skills", "languages", "inventory", "body", "clothing", "hands", "jewelry", "voice", "attitude", "deity", "occupation", "wealth", "family", "faith", "field", "original_value"],
    partial_variables={"format_instructions": npc_key_parser.get_format_instructions()}
)

npc_create_partial_prompt = PromptTemplate(
    template="""Create an NPC for Dungeons and Dragons 5e that has the following attributes.
    {attributes}

    {format_instructions}\n""",
    input_variables=["attributes"],
    partial_variables={"format_instructions": npc_parser.get_format_instructions()}
)

def get_notes_summary(notes="", temperature=0.5, model='gpt-3.5-turbo'):
    _input = notes_prompt.format_prompt(notes=notes)
    messages = _input.to_messages()

    chat = ChatOpenAI(model_name=model, temperature=temperature)
    logging.debug("Sending prompt to OpenAI using model: "+model+"\n\n"+_input.to_messages().pop().content)
    answer = chat(_input.to_messages())
    logging.debug("Received answer from OpenAI: "+answer.content+"\n\nType: "+str(type(answer)))

    parsed_answer = ""
    try:
        parsed_answer = notes_summary_parser.parse(answer)
    except:
        if (type(answer) == str):
            try:
                parsed_answer = NotesSummary(answer=json.loads(answer), nouns=[])
            except:
                parsed_answer = NotesSummary(answer=answer, nouns=[])
        else:
            content = json.loads(answer.content)
            parsed_answer = NotesSummary(answer=content["answer"], nouns=[])

    return parsed_answer

def get_npc(id: int, temperature: float = 0.9, model: str = 'gpt-3.5-turbo-16k', quick: bool = False):
    npc = NPCs().get_npc(int(id))

    # if npc has the key, race, then it is a NPCQuery object
    if (npc.data["race"] != None):
        return npc
    else:
        # If we get here, the NPC is not in the database, so we need to create it
        if (quick == True):
            # Quick mode, use DMScreenXML
            dmscreen_npc = dmscreenxml.DMScreenXML(os.path.join(DIR_XML, 'npc.xml'))
            npc_dict = dmscreen_npc.get_all_values()
            npc_dict["name"] = npc.data["name"]
            return NPCs().add_npc(npc.data["name"], npc_dict)
        else:
            # Slow mode, use GPT-3.5-0613 functions\
            response = openai.ChatCompletion.create(
                model = 'gpt-3.5-turbo-0613',
                messages = [{
                    "role": "user",
                    "content": "Create a NPC for Dungeons and Dragons 5e whose name is "+npc.data["name"]+"."
                }],
                functions = [
                    {
                        "name": "generate_npc",
                        "description": "Generate a NPC for Dungeons and Dragons 5e",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "race": {
                                    "type": "string",
                                    "description": "The race of the NPC"
                                },
                                "npc_class": {
                                    "type": "string",
                                    "description": "The class of the NPC (This can be classless or a multi-class)"
                                },
                                "background": {
                                    "type": "string",
                                    "description": "The background of the NPC"
                                },
                                "alignment": {
                                    "type": "string",
                                    "description": "The alignment of the NPC"
                                },
                                "gender": {
                                    "type": "string",
                                    "description": "The gender of the NPC. (This can include non-binary genders)"
                                },
                                "age": {
                                    "type": "string",
                                    "description": "The age of the NPC"
                                },
                                "height": {
                                    "type": "string",
                                    "description": "The height of the NPC (in feet and inches)"
                                },
                                "weight": {
                                    "type": "string",
                                    "description": "The weight of the NPC (in pounds)"
                                },
                                "hair": {
                                    "type": "string",
                                    "description": "The hair color of the NPC"
                                },
                                "eyes": {
                                    "type": "string",
                                    "description": "The eye color of the NPC"
                                },
                                "eyes_description": {
                                    "type": "string",
                                    "description": "A description of the NPC's eyes other than color"
                                },
                                "hair_style": {
                                    "type": "string",
                                    "description": "The hair style of the NPC"
                                },
                                "ears": {
                                    "type": "string",
                                    "description": "The ear shape of the NPC"
                                },
                                "nose": {
                                    "type": "string",
                                    "description": "The nose shape of the NPC"
                                },
                                "mouth": {
                                    "type": "string",
                                    "description": "The mouth shape of the NPC"
                                },
                                "chin": {
                                    "type": "string",
                                    "description": "The chin shape of the NPC"
                                },
                                "features": {
                                    "type": "string",
                                    "description": "The distinguishing features of the NPC"
                                },
                                "flaws": {
                                    "type": "string",
                                    "description": "The flaws of the NPC"
                                },
                                "ideals": {
                                    "type": "string",
                                    "description": "The ideals of the NPC"
                                },
                                "bonds": {
                                    "type": "string",
                                    "description": "The bonds of the NPC"
                                },
                                "personality": {
                                    "type": "string",
                                    "description": "The personality of the NPC"
                                },
                                "mannerisms": {
                                    "type": "string",
                                    "description": "The mannerisms of the NPC"
                                },
                                "talents": {
                                    "type": "string",
                                    "description": "The talents of the NPC"
                                },
                                "abilities": {
                                    "type": "string",
                                    "description": "The abilities of the NPC"   
                                },
                                "skills": {
                                    "type": "string",
                                    "description": "The skills of the NPC"
                                },
                                "languages": {
                                    "type": "string",
                                    "description": "The languages of the NPC"
                                },
                                "inventory": {
                                    "type": "string",
                                    "description": "The inventory of the NPC"
                                },
                                "body": {
                                    "type": "string",
                                    "description": "The body type of the NPC"
                                },
                                "clothing": {
                                    "type": "string",
                                    "description": "The clothing of the NPC"
                                },
                                "hands": {
                                    "type": "string",
                                    "description": "The hand shape of the NPC"
                                },
                                "jewelry": {
                                    "type": "string",
                                    "description": "The jewelry of the NPC"
                                },
                                "voice": {
                                    "type": "string",
                                    "description": "The voice of the NPC"
                                },
                                "attitude": {
                                    "type": "string",
                                    "description": "The attitude of the NPC"
                                },
                                "deity": {
                                    "type": "string",
                                    "description": "The deity of the NPC"
                                },
                                "occupation": {
                                    "type": "string",
                                    "description": "The occupation of the NPC"
                                },
                                "wealth": {
                                    "type": "string",
                                    "description": "The wealth of the NPC"
                                },
                                "family": {
                                    "type": "string",
                                    "description": "The family of the NPC"
                                },
                                "faith": {
                                    "type": "string",
                                    "description": "The faith of the NPC"
                                },
                                "summary": {
                                    "type": "string",
                                    "description": "A summary of the NPC"
                                }
                            },
                            "required": ["race", "npc_class", "background", "alignment",
                                         "gender", "age", "height", "weight", "hair", "eyes",
                                         "eyes_description", "hair_style", "ears", "nose", "mouth",
                                         "chin", "features", "flaws", "ideals", "bonds", "personality",
                                         "mannerisms", "talents", "abilities", "skills", "languages",
                                         "inventory", "body", "clothing", "hands", "jewelry", "voice",
                                         "attitude", "deity", "occupation", "wealth", "family", "faith",
                                         "summary"]
                        }
                    }
                ],
                function_call="auto"
            )

            print(response)
            message = response["choices"][0]["message"]

            if (message.get("function_call")):
                function_name = message["function_call"]["name"]
                args = message.get("function_call")["arguments"]
                print(args)
                args_json = json.loads(args)
                print(args_json)
                return npc.update(**args_json)
            else:
                return None

def get_npc_summary(id, model="gpt-3.5-turbo", temperature="0.5"):
    npc = NPCs().get_npc(id)
    _input = npc_summary_prompt.format_prompt(name=npc.data["name"], npc_class=npc.data["npc_class"],
                                              background=npc.data["background"], alignment=npc.data["alignment"],
                                              gender=npc.data["gender"], age=npc.data["age"], height=npc.data["height"],
                                              weight=npc.data["weight"], hair=npc.data["hair"], eyes=npc.data["eyes"],
                                              eyes_description=npc.data["eyes_description"], hair_style=npc.data["hair_style"],
                                              ears=npc.data["ears"], nose=npc.data["nose"], mouth=npc.data["mouth"],
                                              chin=npc.data["chin"], features=npc.data["features"],
                                              flaws=npc.data["flaws"], ideals=npc.data["ideals"], bonds=npc.data["bonds"],
                                              personality=npc.data["personality"], mannerisms=npc.data["mannerisms"],
                                              talents=npc.data["talents"], abilities=npc.data["abilities"],
                                              skills=npc.data["skills"], languages=npc.data["languages"],
                                              inventory=npc.data["inventory"], body=npc.data["body"],
                                              clothing=npc.data["clothing"], hands=npc.data["hands"],
                                              jewelry=npc.data["jewelry"], voice=npc.data["voice"],
                                              attitude=npc.data["attitude"], deity=npc.data["deity"],
                                              occupation=npc.data["occupation"], wealth=npc.data["wealth"],
                                              family=npc.data["family"], faith=npc.data["faith"])
    messages = _input.to_messages()
    chat = ChatOpenAI(model_name=model, temperature=temperature)
    logging.debug("Sending prompt to OpenAI using model: "+model+"\n\n"+_input.to_messages().pop().content)
    answer = chat(messages)
    logging.debug("Received answer from OpenAI: "+answer.json()+"\n\nType: "+str(type(answer)))
    parsed_answer = npc_summary_parser.parse(answer.content)
    npc.update(summary=parsed_answer.summary)
    return parsed_answer.summary

def regen_npc_key(id, key, model="gpt-3.5-turbo", temperature="0.5"):
    npc = NPCs().get_npc(id)
    _input = npc_key_prompt.format_prompt(name=npc.data["name"], npc_class=npc.data["npc_class"],
                                              background=npc.data["background"], alignment=npc.data["alignment"],
                                              gender=npc.data["gender"], age=npc.data["age"], height=npc.data["height"],
                                              weight=npc.data["weight"], hair=npc.data["hair"], eyes=npc.data["eyes"],
                                              eyes_description=npc.data["eyes_description"], hair_style=npc.data["hair_style"],
                                              ears=npc.data["ears"], nose=npc.data["nose"], mouth=npc.data["mouth"],
                                              chin=npc.data["chin"], features=npc.data["features"],
                                              flaws=npc.data["flaws"], ideals=npc.data["ideals"], bonds=npc.data["bonds"],
                                              personality=npc.data["personality"], mannerisms=npc.data["mannerisms"],
                                              talents=npc.data["talents"], abilities=npc.data["abilities"],
                                              skills=npc.data["skills"], languages=npc.data["languages"],
                                              inventory=npc.data["inventory"], body=npc.data["body"],
                                              clothing=npc.data["clothing"], hands=npc.data["hands"],
                                              jewelry=npc.data["jewelry"], voice=npc.data["voice"],
                                              attitude=npc.data["attitude"], deity=npc.data["deity"],
                                              occupation=npc.data["occupation"], wealth=npc.data["wealth"],
                                              family=npc.data["family"], faith=npc.data["faith"],
                                              field=key, original_value=npc.data[key])
    messages = _input.to_messages()
    chat = ChatOpenAI(model_name=model, temperature=temperature)
    logging.debug("Sending prompt to OpenAI using model: "+model+"\n\n"+_input.to_messages().pop().content)
    answer = chat(messages)
    logging.debug("Received answer from OpenAI: "+answer.json()+"\n\nType: "+str(type(answer)))
    parsed_answer = npc_key_parser.parse(answer.content)
    npc.update(**{key: parsed_answer.value})
    return parsed_answer.value

def gen_npc_from_dict(npc_dict):
    _input = npc_create_partial_prompt.format_prompt(attributes=npc_dict)
    messages = _input.to_messages()
    chat = ChatOpenAI(model_name=model_name, temperature=0.9)
    print("Sending prompt to OpenAI using model: "+model_name+"\n\n"+_input.to_messages().pop().content)
    answer = chat(messages)
    print("Received answer from OpenAI: "+answer.json()+"\n\nType: "+str(type(answer)))
    parsed_answer = npc_parser.parse(answer.content)
    NPCs().add_npc(parsed_answer.name, parsed_answer.dict())
    return parsed_answer

def get_names(temperature=0.9, model='text-davinci-003', game_id=None) -> list[str]:
    names = NPCs().get_all(game_id=game_id)
    if (game_id != None):
        return names
    
    # If we get here, we are getting unassigned names
    names_need = 5 - len(names)
    if (names_need > 0):
        logging.info("Getting "+str(names_need)+" names from OpenAI")
        _input = names_prompt.format_prompt(names_need=names_need)
        messages = _input.to_messages()
        chat = ChatOpenAI(model_name=model_name, temperature=0.9)
        logging.debug("Sending prompt to OpenAI using model: "+model_name+"\n\n"+_input.to_messages().pop().content)
        answer = chat(_input.to_messages())
        logging.debug("Received answer from OpenAI: "+answer.content+"\n\nType: "+str(type(answer.content)))

        parsed_answer = names_parser.parse(answer.content)

        for name in parsed_answer.names:
            NPCs().add_npc(name)
    return names

def send_message(message, temperature=0.0):
    book_query = message
    _input = reference_prompt.format_prompt(query=book_query)

    docs = reference_instance.similarity_search(_input.to_messages()[0].content, k=4, filter={
        "collection": "core",
        "title": {"$or": [{"$eq":"Tyranny of Dragons"}]}
    })
    llm = ChatOpenAI(model_name=model_name, temperature=temperature, openai_api_key=os.environ["OPENAI_API_KEY"])
    chain = load_qa_chain(llm, chain_type="stuff", verbose=True)
    answer = chain.run(input_documents=docs, question=_input.to_messages()[0].content, verbose=True)

    try:
        parsed_answer = reference_parser.parse(answer)
    except:
        parsed_answer = ReferenceQuery(answer=answer, source="Unknown")

    return parsed_answer

def add_documents(loader, instance):
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100, separators=["\n\n", "\n", ". ", ",", " ", ""])
    texts = text_splitter.split_documents(documents)
    instance.add_documents(texts)

def reload_documents():
    for file in [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(DIR_DOCS)) for f in fn]:
        file_extension = pathlib.Path(file).suffix
        loader = None
        match file_extension:
            case '.txt':
                loader = TextLoader(file, 'utf-8')
            case '.pdf':
                loader = UnstructuredPDFLoader(file, 'utf-8')
            case _:
                print("Unsupported file type: "+file_extension)
    
        loader = TextLoader(file, 'utf-8')
        print("Adding documents from "+file)
        add_documents(loader, reference_instance)

def generate_npc(npc: NPC, name:str, fields:dict={}, game_id:int=None):
    fields["game_id"] = game_id
    fields["name"] = name
    return npc.update(**fields)

"""Required for flask webserver"""
@app.route('/')
@app.route('/home')
def home():
    db = sqlite3.connect(os.path.join(DIR_ROOT, 'db.sqlite3'))
    # create table
    """
    cursor = db.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS names(id INTEGER PRIMARY KEY, name TEXT);")
    cursor.close()
    db.commit()
    db.close()
    """

    todays_date = time.strftime("%m/%d/%Y")
    return render_template('dmscreen.html', **locals())

@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    message = request.form.get('question')
    modules = request.form.get('modules')
    temperature = request.form.get('temperature')
    gpt_response = send_message(message, temperature)
    response = make_response([gpt_response.answer, gpt_response.source, gpt_response.nouns])
    
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/setgame', methods=['POST'])
def setgame():
    global game, game_dir, game_persist_dir, notes_instance

    # Update the currently tracked game, and set embeddings 
    game = Game(request.form.get('game'))
    game_dir = os.path.join(DIR_NOTES, game.data['abbr'])
    # If game_dir does not exist, create it
    if not os.path.exists(game_dir):
        os.makedirs(game_dir)
        game_persist_dir = os.path.join(game_dir, 'db')
        os.makedirs(game_persist_dir)
    else:
        game_persist_dir = os.path.join(game_dir, 'db')

    embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    notes_instance = Chroma(embedding_function=embeddings, persist_directory=game_persist_dir)
    notes_instance.persist()

    # Check the db for a notes summary
    game_notes = GameNotes(game.data['abbr']).get_newest()

    # Scan notes_dir for files, store the list of files and choose the most recent one
    notes_file = None
    notes_files = []
    for file in [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(game_dir)) for f in fn]:
        file_extension = pathlib.Path(file).suffix
        if file_extension == '.txt':
            filename = os.path.basename(file)
            filename = os.path.splitext(filename)[0]
            notes_files.append(filename)
            if notes_file == None:
                notes_file = file
            else:
                if os.path.getmtime(file) > os.path.getmtime(notes_file):
                    notes_file = file

    # If there is a notes summary in the db, use it, otherwise, generate one from ChatGPT
    notes_summary = ""
    if (game_notes != None):
        notes_summary = game_notes.data["summary"]
    else:
        # Scan notes_dir for files and choose the most recent one
        # Slurp the contents of the most recent file into string
        notes = ""
        if notes_file != None:
            with open(notes_file, 'r') as f:
                notes = f.read()

        if (notes == ""):
            notes_summary = "No notes found for "+game.data['name']
        else:
            gpt_response = get_notes_summary(notes)
            notes_summary = gpt_response.answer

            # Store the notes summary in the db
            GameNotes(game.data['abbr']).add(notes, filename, notes_summary)

    # Get a list of NPCs
    names = []
    for name in get_names():
        names.append(name.data)

    game_names = []
    for name in get_names(game_id=game.data['id']):
        game_names.append(name.data)

    # Return the notes summary, the list of files, and the list of NPCs
    response = make_response([notes_summary, notes_files, names, game_names])
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/savenotes', methods=['POST'])
def savenotes(model='text-davinci-003', temperature=0.2):
    notes = request.form.get('notes')
    demark = time.strftime("%Y-%m-%d")+" SESSION NOTES FOR "+game.data['name'].upper()
    notes_formatted = demark+"\n\n"+notes+"\n\nEND OF "+demark
    game_dir = os.path.join(DIR_NOTES, game.data['abbr'])
    notes_file = os.path.join(game_dir, time.strftime("%Y-%m-%d")+'.txt')
    with open(notes_file, 'w') as f:
        f.write(notes_formatted)
    loader = TextLoader(notes_file, 'utf-8')
    add_documents(loader, notes_instance)

    gpt_response = get_notes_summary(notes)
    response_text = gpt_response.answer
    
    db = sqlite3.connect(os.path.join(DIR_ROOT, 'db.sqlite3'))
    cursor = db.cursor()
    cursor.execute('INSERT INTO games_notes (game, date, orig, summary) VALUES (?, ?, ?, ?);', (game.data['abbr'], time.strftime("%Y-%m-%d"), notes, response_text))
    db.commit()
    cursor.close()
    db.close()

    response = make_response([response_text])
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/getnote', methods=['POST'])
def getnote():
    notes_file = os.path.join(game_dir, request.form.get('date')+'.txt')
    notes = ""
    if notes_file != None:
        with open(notes_file, 'r') as f:
            notes = f.read()
    response = make_response([notes])
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/getnpc', methods=['POST', 'GET'])
def getnpc():
    id = request.form.get('id')
    name = request.form.get('name')
    quick = True if request.form.get('quick') == "1" else False
    if (id == '' and name == ''):
        npc = NPCs().add_npc(name)
        id = npc.data['id']
    elif (id == ''): # We have a name, but no id
        npc = NPCs().get_npc(name, game_id=game.data['id'] if game != None else None)
        if (npc == None):
            npc = NPCs().add_npc(name)
        id = npc.data['id']

    npc = get_npc(id, quick=quick)
    if (npc == None):
        response = make_response("ERROR: Could not find NPC")
        response.mimetype = "text/plain"
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    # Check if the NPC image exists
    npc_image = os.path.join(DIR_ROOT, 'static', 'img', 'npc', str(id)+'.png')
    npc_image_exists = os.path.isfile(npc_image)
    response_json:dict = npc.data
    response_json["image_exists"] = npc_image_exists

    response = make_response(response_json)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/regensummary', methods=['POST'])
def regensummary():
    id = request.form.get('id')
    gpt_response = get_npc_summary(id)
    response = make_response(gpt_response)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/regenkey', methods=['POST'])
def regenkey():
    id = request.form.get('id')
    key = request.form.get('key')
    gpt_response = regen_npc_key(id, key, temperature=0.9)
    response = make_response(gpt_response)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/createnpc', methods=['POST'])
def createnpc():
    # Get all the form data
    keys = request.form.keys()
    npc_dict = {}
    for key in keys:
        npc_dict[key] = request.form.get(key)
    
    gpt_response = gen_npc_from_dict(npc_dict)
    response = make_response(gpt_response.dict())
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/deletename', methods=['POST'])
def deletename():
    id = request.form.get('id')
    NPCs().delete_npc(id)

    # If the image exists, delete it
    npc_image = os.path.join(DIR_ROOT, 'static', 'img', 'npc', str(id)+'.png')
    if os.path.isfile(npc_image):
        os.remove(npc_image)

    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/gennpcimage', methods=['POST'])
def gennpcimage():
    id:int = int(request.form.get('id'))
    npc = NPCs().get_npc(id)
    print(npc.data['name'])
    prompt = "a highly realistic photo of a " +str(npc.data['age'])+" year old "+ str(npc.data['gender']) + " " + str(npc.data['race']) + " " + str(npc.data['npc_class']) + ", fantasy, looking at the camera, with " + str(npc.data['hair']) + " " + str(npc.data['hair_style']) + " " + " hair and " + str(npc.data['eyes']) + " " + str(npc.data['eyes_description']) + " eyes, " + str(npc.data['chin']) + " chin,  " + str(npc.data['clothing']) + ", " + str(npc.data['ears']) + " ears, " + str(npc.data['features']) + ", " + str(npc.data['mouth']) + " mouth, " + str(npc.data['nose'] + " nose")

    print(prompt)
    openai_response = openai.Image.create(
        prompt = prompt,
        n=1,
        size='512x512'
    )
    image_url = openai_response['data'][0]['url']
    print(image_url)

    image_file = os.path.join(DIR_ROOT, 'static', 'img', 'npc', str(id)+'.png')
    img = requests.get(image_url)
    open(image_file, 'wb').write(img.content)

    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/addname', methods=['POST'])
def addname():
    id = request.form.get('id')
    npc = NPCs().get_npc(id)
    npc.update(game_id = game.data['id'])
    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

if __name__ == '__main__':
    """Load the index from the loaders"""
    #reload_documents()

    """
    template="As a resource bot, your goal is to provide as accurate inforfmation as possible to the user. When possible site your sources. You can use the following resources to help you answer questions: \n{modules}\n\nQuestion: {message}\nAnswer:"
    PROMPT = PromptTemplate(template=template, input_variables=["modules", "message"])
    chain_type_kwargs = {"prompt": PROMPT}
    """
    if (ENABLE_CHATBOT == True):
        pinecone.init(api_key=os.environ["PINECONE_API_KEY"], environment=os.environ["PINECONE_ENVIRONMENT"])
        index_name = '5e'

        embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
        reference_instance = Pinecone.from_existing_index(index_name, embedding=embeddings)

        #reference_instance = Chroma(embedding_function=embeddings, persist_directory=DIR_PERSIST, )
        #reference_instance.persist()

    """Set up file watchdog in its own thread"""
    patterns = ["*.txt", "*.pdf"]
    ignore_patterns = None
    ignore_directories = True
    case_sensitive = True
    path = DIR_DOCS
    go_recursively = True

    """Start the webserver"""
    app.run(port=30003)
