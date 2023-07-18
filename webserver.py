import os
import io
import warnings
from PIL import Image
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
import time
import logging
import sqlite3
import openai
import requests

from models import NPC, NPCs, GameNotes, Game, PlotPoints, Reminders, Reminder
from chatbot import ChatBot
from npc import AINPC

from typing import List

from flask import Flask, render_template, request, make_response
from dotenv import dotenv_values, load_dotenv
from watchdog.observers import Observer

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from langchain.chains.question_answering import load_qa_chain

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

""" CONSTANTS """
DIR_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR_DOCS = os.path.join(DIR_ROOT, 'docs')
DIR_PERSIST = os.path.join(DIR_ROOT, 'db')
DIR_NOTES = os.path.join(DIR_ROOT, 'notes')

#model_name = 'gpt-4'
model_name = 'gpt-3.5-turbo-16k'
notes_instance = None
game = None
game_dir = None
game_persist_dir = None

""" FLASK """
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

# Required Environment Variables
for key in ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'PINECONE_ENVIRONMENT', 'PINECONE_INDEX']:
    if key not in os.environ:
        print("Please set the "+key+" environment variable in .env")
        exit(1)
    
class NameList(BaseModel):
    names: List[str] = Field(description="A list of names")

names_parser = PydanticOutputParser(pydantic_object=NameList)

names_prompt = PromptTemplate(
    template="""Give me a list of {names_need} names appropriate for a Dungeons and Dragon fantasy setting. {format_instructions}""",
    input_variables=["names_need"],
    partial_variables={"format_instructions": names_parser.get_format_instructions()}
)

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

def generate_npc(npc: NPC, name:str, fields:dict={}, game_id:int=None):
    fields["game_id"] = game_id
    fields["name"] = name
    return npc.update(**fields)

def send_flask_response(make_response, parameters:list[str]):
    response = make_response(parameters)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

"""Required for flask webserver"""
@app.route('/')
@app.route('/home')
def home():
    db = sqlite3.connect(os.path.join(DIR_ROOT, 'db.sqlite3'))

    todays_date = time.strftime("%m/%d/%Y")
    return render_template('dmscreen.html', **locals())

@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():    
    global game
    message = request.form.get('question')
    modules = request.form.get('modules')
    temperature = request.form.get('temperature')
    chatbot = ChatBot(game.data['id'], os.getenv("OPENAI_API_KEY"), os.getenv("PINECONE_API_KEY"), os.getenv("PINECONE_ENVIRONMENT"))
    answer = chatbot.send_message(message, temperature=temperature, model='gpt-4')
    return send_flask_response(make_response, answer)

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

    # Check the db for a notes summary
    game_notes = GameNotes(game.data['abbr']).get_newest()
    notes_files = GameNotes(game.data['abbr']).get_dates()

    # If there is a notes summary in the db, use it, otherwise, generate one from ChatGPT
    notes_summary = game_notes.data["summary"] if game_notes != None else None

    # Get a list of NPCs
    names = []
    for name in get_names():
        names.append(name.data)

    game_names = []
    for name in get_names(game_id=game.data['id']):
        game_names.append(name.data)

    # Get the list of plot points from db
    plot_points = []
    for plot_point in PlotPoints(game.data['id']).get_all():
        plot_points.append(plot_point.data)

    reminders = []
    for reminder in Reminders(game.data['id']).get_all():
        reminders.append(reminder.data)

    return send_flask_response(make_response, [notes_summary, notes_files, names, game_names, plot_points, reminders])

@app.route('/savenotes', methods=['POST'])
def savenotes(model='text-davinci-003', temperature=0.2):
    notes = request.form.get('notes')
    date = time.strftime("%Y-%m-%d")
    note = GameNotes(game.data['abbr']).preprocess_and_add(notes, date).data['summary']
    return send_flask_response(make_response, [note])

@app.route('/getnote', methods=['POST'])
def getnote():
    date = request.form.get('date')
    note = GameNotes(game.data['abbr']).get_by_date(request.form.get('date'))
    return send_flask_response(make_response, [note.data['orig']])

@app.route('/getnpc', methods=['POST', 'GET'])
def getnpc():
    id = int(request.form.get('id'))
    name = request.form.get('name')
    quick = True if request.form.get('quick') == "1" else False

    if (id == '' and name == ''): # Create a completely new NPC
        npc = NPCs().add_npc(name)
        id = npc.data['id']
    
    npc = AINPC().get_npc(id, quick=quick)

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

@app.route('/getnpcs', methods=['POST'])
def getnpcs():
    names = []
    for name in get_names():
        names.append(name.data)
    return send_flask_response(make_response, names)

@app.route('/regensummary', methods=['POST'])
def regensummary():
    id = request.form.get('id')
    gpt_response = AINPC().get_npc_summary(id)
    response = make_response(gpt_response)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/regenkey', methods=['POST'])
def regenkey():
    id = request.form.get('id')
    key = request.form.get('key')
    gpt_response = AINPC().regen_npc_key(id, key, temperature=0.9)
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
    
    npc = AINPC().gen_npc_from_dict(npc_dict)
    response = make_response(npc.data)
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

@app.route('/gennpcimage_stability', methods=['POST'])
def gennpcimage_stability():
    id:int = int(request.form.get('id'))
    npc = NPC(id)
    print(npc.data['name'])
    prompt = "epic 300mm professional highly realistic photo of a " +str(npc.data['age'])+" year old "+ str(npc.data['gender']) + " " + str(npc.data['race']) + " " + str(npc.data['class_']) + ", fantasy, looking at the camera, with " + str(npc.data['hair']) + " " + str(npc.data['hair_style']) + " " + " hair and " + str(npc.data['eyes']) + " " + str(npc.data['eyes_description']) + " eyes, " + str(npc.data['chin']) + " chin,  " + str(npc.data['clothing']) + ", " + str(npc.data['ears']) + " ears, " + str(npc.data['features']) + ", " + str(npc.data['mouth']) + " mouth, " + str(npc.data['nose'] + " nose, trending on deviant art, best quality, masterpiece, extremely high detail digital RAW color photograph, 4k, highly detailed")
    negative_prompt = "ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, disfigured, extra limbs, cloned face, bad anatomy, gross proportions, malformed limbs, missing arms, fused fingers, extra arms, mutated hands, too many fingers, long neck"

    print(os.getenv("STABILITY_API_KEY"))
    stability_api = client.StabilityInference(
        key = os.getenv("STABILITY_API_KEY"),
        verbose=True,
        engine="stable-diffusion-xl-1024-v0-9"
    )

    answers = stability_api.generate(
        prompt = [
            generation.Prompt(text=prompt, parameters=generation.PromptParameters(weight=1)),
            generation.Prompt(text=negative_prompt, parameters=generation.PromptParameters(weight=-1))
        ],
        steps=50,
        cfg_scale=8.0,
        width=512,
        height=512,
        samples=1,
        sampler=generation.SAMPLER_K_DPMPP_2M,
    )



    for resp in answers:
        for artifact in resp.artifacts:
            if artifact.finish_reason == generation.FILTER:
                logging.warn("Your request activated the APIs safety filters and could not be processed.")
            if artifact.type == generation.ARTIFACT_IMAGE:
                img = Image.open(io.BytesIO(artifact.binary))
                img.save(os.path.join(DIR_ROOT, 'static', 'img', 'npc', str(id)+'.png'))

    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/gennpcimage', methods=['POST'])
def gennpcimage():
    id:int = int(request.form.get('id'))
    npc = NPC(id)
    print(npc.data['name'])
    prompt = "epic 300mm professional highly realistic photo of a " +str(npc.data['age'])+" year old "+ str(npc.data['gender']) + " " + str(npc.data['race']) + " " + str(npc.data['class_']) + ", fantasy, looking at the camera, with " + str(npc.data['hair']) + " " + str(npc.data['hair_style']) + " " + " hair and " + str(npc.data['eyes']) + " " + str(npc.data['eyes_description']) + " eyes, " + str(npc.data['chin']) + " chin,  " + str(npc.data['clothing']) + ", " + str(npc.data['ears']) + " ears, " + str(npc.data['features']) + ", " + str(npc.data['mouth']) + " mouth, " + str(npc.data['nose'] + " nose, trending on deviant art")

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
    npc = NPC(id)
    npc.update(game_id = game.data['id'])
    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/createplotpoint', methods=['POST'])
def createplotpoint():
    title = request.form.get('title')
    details = request.form.get('summary')
    plot_point = PlotPoints(game.data['id']).add(game.data['id'], title, details=details)
    response = make_response(plot_point.data)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/createreminder', methods=['POST'])
def createreminder():
    title = request.form.get('title')
    details = request.form.get('details')
    trigger = request.form.get('trigger')
    reminder = Reminders(game.data['id']).add(title, details=details, trigger=trigger)
    response = make_response(reminder.data)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/getreminders', methods=['POST'])
def getreminders():
    reminders = []
    for reminder in Reminders(game.data['id']).get_all():
        reminders.append(reminder.data)
    return send_flask_response(make_response, reminders)

@app.route('/deletereminder', methods=['POST'])
def deletereminder():
    id = request.form.get('id')
    Reminder(id).delete()
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

    """Start the webserver"""
    app.run(port=30003)
