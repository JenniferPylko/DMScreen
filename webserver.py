import os
import io
from PIL import Image
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
import time
import logging
import openai
import requests
import bcrypt
from models import NPC, NPCs, GameNotes, GameNote, Game, PlotPoints, Reminders, Reminder, TokenLog, Users, Games, Tasks, Task, Waitlist, User
from chatbot import ChatBot
from npc import AINPC
from openaihandler import OpenAIHandler
import uuid
import threading
from pydub import AudioSegment
import ffmpeg
import glob
import stripe
import subprocess
import functools

from typing import List

from flask import Flask, render_template, request, make_response, session, redirect, url_for
from dotenv import dotenv_values, load_dotenv
from werkzeug.utils import secure_filename

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from langchain.chains.question_answering import load_qa_chain
from langchain.callbacks import get_openai_callback
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate

import build_scss

handler = logging.FileHandler('logs/webserver.log')
handler.setLevel(logging.DEBUG)
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)
root_logger.debug('Starting webserver')
logging.basicConfig(level=logging.DEBUG, filename='webserver.log')

load_dotenv()

""" CONSTANTS """
DIR_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR_DOCS = os.path.join(DIR_ROOT, 'docs')
DIR_PERSIST = os.path.join(DIR_ROOT, 'db')
DIR_NOTES = os.path.join(DIR_ROOT, 'notes')
DIR_AUDIO = os.path.join(DIR_ROOT, 'audio')

model_name = OpenAIHandler.MODEL_GPT3

""" FLASK """
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = True
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024 # 300 MB
app.secret_key = os.getenv('SESSION_SECRET')

# Required Environment Variables
for key in ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'PINECONE_ENVIRONMENT', 'PINECONE_INDEX']:
    if key not in os.environ:
        print("Please set the "+key+" environment variable in .env")
        exit(1)
    
class NameList(BaseModel):
    names: List[str] = Field(description="A list of names")

names_parser = PydanticOutputParser(pydantic_object=NameList)

names_prompt = PromptTemplate(
    template="""Give me a list of {names_need} names appropriate for a Dungeons and Dragon fantasy
    setting. The names should be first and last names. The names should include names appropriate for
    humans, elves, dwarves, halflings, gnomes, and half-orcs. Do not include published names. Do not
    include generic names

    GOOD EXAMPLES:
    - Eleanor Silverleaf
    - Kethryllia
    - Glimmer Moonbrook
    - Daelin Proudmoore

    BAD EXAMPLES:
    - John Smith
    - Bob
    - Frodo Underhill
    - Gandalf
    - Merlin

    {format_instructions}""",
    input_variables=["names_need"],
    partial_variables={"format_instructions": names_parser.get_format_instructions()}
)

def get_names(temperature=0.9, model='text-davinci-003', game_id=None) -> list[str]:
    names = NPCs().get_all(game_id=game_id)
    
    # If we get here, we are getting unassigned names
    names_need = 5 - len(names)
    if (names_need > 0):
        logging.info("Getting "+str(names_need)+" names from OpenAI")
        _input = names_prompt.format_prompt(names_need=names_need)
        messages = _input.to_messages()
        chat = ChatOpenAI(model_name=model_name, temperature=0.9)
        logging.debug("Sending prompt to OpenAI using model: "+model_name+"\n\n"+_input.to_messages().pop().content)
        with get_openai_callback() as cb:
            answer = chat(_input.to_messages())
            TokenLog().add("Generate Names", cb.prompt_tokens, cb.completion_tokens, cb.total_cost, session.get('user_id'))
        logging.debug("Received answer from OpenAI: "+answer.content)

        parsed_answer = names_parser.parse(answer.content)

        for name in parsed_answer.names:
            NPCs().add_npc(name, attributes={"game_id": game_id})
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

def send_simple_message(email, subject, msg):
    logging.info("Sending email to "+email)
    return requests.post(
        "https://api.mailgun.net/v3/"+os.getenv("MAILGUN_DOMAIN")+"/messages" ,
        auth=("api", os.getenv("MAILGUN_API_KEY")),
        data={
            "from": "DM Assistant <mailgun@"+os.getenv("MAILGUN_DOMAIN")+">",
            "to": [email],
            "subject": subject,
            "text": msg
        })

def split_audio(task_id, file_path, game):
    logging.debug("Splitting audio file: "+file_path)
    task = Task(task_id)
    task.update(status="Running", message="Loading audio file")

    #audio = AudioSegment.from_mp3(file_path)
    #audio_length = audio.duration_seconds

    # Get the audio length first
    audio_length_cmd = ["ffmpeg", "-i", file_path, "-f", "null", "-"]
    result = subprocess.run(audio_length_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    output = result.stdout
    start = output.rfind("Duration: ")
    end = output.rfind(", start: ")
    duration = output[start+10:end]
    h, m, s = map(float, duration.split(':'))
    audio_length = (h * 3600) + (m * 60) + s

    #TokenLog().add("Split Audio", 0, 0, OpenAIHandler.GPT_COST_WHISPER * (audio_length/60), session.get('user_id'))
    logging.debug("Audio length: " + str(audio_length))
    chunk_duration = 1400 # 23 minutes

    for i in range(int(audio_length/chunk_duration)):
        task.update(message="Preparing audio for transcription.")
        start_time = i * chunk_duration
        chunk_name = os.path.join(DIR_AUDIO, f"{task_id}--chunk{i}.mp3")
        logging.debug("Exporting " + chunk_name)
        chunk_audio_cmd = ["ffmpeg", "-i", file_path, "-ss", str(start_time), "-t", str(chunk_duration), "-f", "mp3", chunk_name]
        subprocess.run(chunk_audio_cmd)

    logging.debug("Done")
    task.update(message="Split Complete")

    """
    for (i, chunk) in enumerate(audio[::1400000]):
        task.update(message="Preparing audio for transcription.")
        chunk_name = os.path.join(DIR_AUDIO, f"{task_id}--chunk{i}.mp3")
        logging.debug("Exporting " + chunk_name)
        chunk.export(chunk_name, format="mp3")
    logging.debug("Done")
    task.update(message="Split Complete")
    """

    note = whisper(task)

    date = time.strftime("%Y-%m-%d")
    GameNotes(game.data['abbr']).preprocess_and_add(note['bullets'], date, session.get('user_id')).data['summary']

    # Delete the audio files
    audio_files = glob.glob(DIR_AUDIO + f"""/{task_id}--chunk*.mp3""")
    for f in audio_files:
        os.remove(f)
    txt_files = glob.glob(DIR_AUDIO + f"""/{task_id}--chunk*.mp3.transcript.txt""")
    for f in txt_files:
        os.remove(f)
    os.remove(file_path)

def whisper(task):
    task.update(message="Transcribing audio files")
    llm = ChatOpenAI(temperature=0, openai_api_key=os.environ["OPENAI_API_KEY"], model_name=OpenAIHandler.MODEL_GPT3)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
    text = ""
    audio_files = glob.glob(DIR_AUDIO + f"""/{task.data['id']}--chunk*.mp3""")
    for f in audio_files:
        output_file = f + ".transcript.txt"
        if not os.path.exists(output_file):
            audio_file = open(f, "rb")
            logging.debug("Transcribing audio file: " + f)
            task.update(message="Transcribing audio")
            try:
                transcript = openai.Audio.transcribe(OpenAIHandler.MODEL_WHISPER, audio_file, api_key=os.environ["OPENAI_API_KEY"])
                text += transcript.text + "\n"
            except Exception as e:
                logging.error(e)

    task.update(message="Summarizing transcripts")
    docs = text_splitter.create_documents([text])
    num_docs = len(docs)
    logging.debug(f"Number of documents: {num_docs}")

    map_prompt = """
    Write a concise summary of the following. When summarizing combat, only include the key points of
    the combat. Do not include the dice rolls or the results of the dice rolls. Do not include the
    narrative of the combat. Only include the key points of the combat, or funny/odd/unique moments.
    Be sure to include character deaths, if any. Be sure to include new character inductions, if any.
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

    logging.debug("Loading summarization chain...")
    with get_openai_callback() as cb:
        summary_chain = load_summarize_chain(llm=llm, chain_type="map_reduce",
                                            map_prompt=map_prompt_template,
                                            combine_prompt=combine_prompt_template, verbose=True)
        output = summary_chain.run(docs)
        #TokenLog().add("Summarize Transcript", cb.prompt_tokens, cb.completion_tokens, cb.total_cost, session.get('user_id'))

    task.update(status="Complete", message="")
    return {
        "bullets": output,
        "fulltext": text
    }

""" Decorators """
def require_loggedin(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if (session.get('user_id') == None):
            return render_template('loginprompt.html', error="You must be logged in to view this page")
        return func(User(session.get('user_id')), *args, **kwargs)
    return wrapper

def require_loggedin_ajax(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if (session.get('user_id') == None):
            return send_flask_response(make_response, ["ERROR: You must be logged in to view this page"])
        return func(User(session.get('user_id')), *args, **kwargs)
    return wrapper

"""Required for flask webserver"""
@app.route('/')
@app.route('/loginprompt')
def loginprompt():
    return render_template('loginprompt.html')

@app.route('/forgot')
def forgotpassword():
    return render_template('forgotpassword.html')

@app.route('/forgot_2', methods=['POST'])
def forgotpassword_2():
    email = request.form.get('email')
    user = Users().get_by_email(email)
    if user != None:
        reset = user.pre_reset_password()
        r = send_simple_message(email, "DM Assistant Password Reset", "A request was made to reset your password at dmscreen.net. If you did not make this request, please ignore this email. If you made this request, please click the following link to reset your password: http://dmscreen.net/reset?email="+email+"&key="+str(reset)+"\n\nIf you did not make this request, please ignore this email.")
        logging.debug("Email response: "+str(r))

    # Send the user back to the login prompt even if they didn't have an account. Don't clue an
    # attacker in that they have the wrong email address
    return render_template('loginprompt.html', reset=True)

@app.route('/reset', methods=['GET'])
def resetpassword():
    email = request.args.get('email')
    key = request.args.get('key')
    user = Users().get_by_email(email)
    if user == None:
        return render_template('loginprompt.html', error="Invalid email or password")
    if str(user.data['reset']) != key:
        return render_template('loginprompt.html', error="Invalid email or password")
    return render_template('resetpassword.html', email=email, key=key)

@app.route('/reset_2', methods=['POST'])
def resetpassword_2():
    email = request.form.get('email')
    key = request.form.get('key')
    password = request.form.get('psw1').encode('utf-8')
    user = Users().get_by_email(email)
    if user == None:
        return render_template('loginprompt.html', error="Invalid email or password")
    if str(user.data['reset']) != key:
        return render_template('loginprompt.html', error="Invalid email or password")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
    user.update(password=hashed_password, reset="")
    return render_template('loginprompt.html', info="Your password has been reset. Please login with your new password")

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('psw').encode('utf-8')
    remember = request.form.get('remember')
    user = Users().get_by_email(email)
    if user == None:
        return render_template('loginprompt.html', error="Invalid email or password")
    if not bcrypt.checkpw(password, user.data['password']):
        return render_template('loginprompt.html', error="Invalid email or password")
    
    session['user_id'] = user.data['id']
    return redirect(url_for('home'))

@app.route('/createaccount')
def createaccount():
    if (int(os.getenv("MAX_USERS")) > -1):
        count = Users().count()
        if count >= int(os.getenv("MAX_USERS")):
            return render_template('waitlist.html')
    return render_template('createaccount.html')

@app.route('/createaccount_2', methods=['POST'])
def createaccount_2():
    email = request.form.get('email')
    password = request.form.get('psw1').encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
    user = Users().add(email, hashed_password)
    # send email
    send_simple_message(email, "Welcome to DM Assistant!", "Your account has been created. Please click the following link to verify your email address: http://dmscreen.net/verify?email="+email+"&key="+str(user.data['verify']))
    return render_template('loginprompt.html', created=True)

@app.route('/home')
@require_loggedin
def home(user):
    todays_date = time.strftime("%m/%d/%Y")
    game_list = []
    print(session.get('user_id'))
    membership = user.data['membership']
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    stripe_priceId_10 = os.getenv("STRIPE_PRICEID_BASIC")
    userid = session.get('user_id')
    for game in Games().get_by_owner(userid):
        game_list.append({
            "id": game.data['id'],
            "name": game.data['name']
        })
    return render_template('dmscreen.html', **locals())

@app.route('/ask', methods=['POST', 'OPTIONS'])
@require_loggedin_ajax
def ask(user):
    message = request.form.get('question')
    game_id = int(request.form.get('game_id')) if len(request.form.get('game_id')) > 0 else None
    chatbot = ChatBot(game_id, user.data['id'], os.getenv("OPENAI_API_KEY"), os.getenv("PINECONE_API_KEY"), os.getenv("PINECONE_ENVIRONMENT"))
    answer = chatbot.send_message(message, model=OpenAIHandler.MODEL_GPT3)
    return send_flask_response(make_response, answer)

@app.route('/setgame', methods=['POST'])
@require_loggedin_ajax
def setgame(user):
    game = Game(int(request.form.get('game_id')))

    # Check the db for a notes summary
    game_notes = GameNotes(game.data['abbr']).get_newest()
    all_notes = GameNotes(game.data['abbr']).get_all()
    r_notes = []
    for note in all_notes:
        r_notes.append({
            "date": note.data['date'],
            "id": note.data['id']
        })

    # If there is a notes summary in the db, use it
    notes_summary = game_notes.data["summary"] if game_notes != None else None

    # Get a list of NPCs
    names = []
    for name in get_names(game_id=game.data['id']):
        names.append(name.data)

    # Get the list of plot points from db
    plot_points = []
    for plot_point in PlotPoints(game.data['id']).get_all():
        plot_points.append(plot_point.data)

    reminders = []
    for reminder in Reminders(game.data['id']).get_all():
        reminders.append(reminder.data)

    return send_flask_response(make_response, [notes_summary, r_notes, names, plot_points, reminders])

@app.route('/savenotes', methods=['POST'])
@require_loggedin_ajax
def savenotes(user):
    notes = request.form.get('notes')
    game = Game(int(request.form.get('game_id')))
    date = time.strftime("%Y-%m-%d")
    note = GameNotes(game.data['abbr']).preprocess_and_add(notes, date, user.data['id']).data['summary']
    return send_flask_response(make_response, [note])

@app.route('/updatenote', methods=['POST'])
@require_loggedin_ajax
def updatenote(user):
    date = request.form.get('date')
    note = request.form.get('note')
    game = Game(int(request.form.get('game_id')))
    game_note = GameNotes(game.data['abbr']).get_by_date(date)
    game_note.update(note)
    return send_flask_response(make_response, ["OK"])

@app.route('/getnote', methods=['POST'])
@require_loggedin_ajax
def getnote(user):
    id = request.form.get('id')
    note = GameNote(id)
    return send_flask_response(make_response, [note.data['orig']])

@app.route('/getnotes', methods=['POST'])
@require_loggedin_ajax
def getnotes(user):
    game = Game(int(request.form.get('game_id')))
    notes = []
    for note in GameNotes(game.data['abbr']).get_all():
        notes.append(note.data)
    return send_flask_response(make_response, notes)

@app.route('/deletenote', methods=['POST'])
@require_loggedin_ajax
def deletenote(user):
    date = request.form.get('date')
    game = Game(int(request.form.get('game_id')))
    GameNotes(game.data['abbr']).get_by_date(date).delete()
    return send_flask_response(make_response, ["OK"])

@app.route('/update_notes_date', methods=['POST'])
@require_loggedin_ajax
def update_notes_date(user):
    id = request.form.get('id')
    new_date = request.form.get('new_date')
    note = GameNote(id)
    note.update_date(new_date)
    return send_flask_response(make_response, ["OK"])

@app.route('/getnpc', methods=['POST', 'GET'])
@require_loggedin_ajax
def getnpc(user):
    id = int(request.form.get('id'))
    name = request.form.get('name')
    quick = True if request.form.get('quick') == "1" else False

    if (id == '' and name == ''): # Create a completely new NPC
        npc = NPCs().add_npc(name)
        id = npc.data['id']
    
    npc = AINPC(session.get('user_id')).get_npc(id, quick=quick)

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
@require_loggedin_ajax
def getnpcs(user):
    game_id = int(request.form.get('game_id'))
    names = []
    for name in get_names(game_id=game_id):
        names.append(name.data)
    return send_flask_response(make_response, names)

@app.route('/regensummary', methods=['POST'])
@require_loggedin_ajax
def regensummary(user):
    id = request.form.get('id')
    gpt_response = AINPC(session.get('user_id')).get_npc_summary(id)
    response = make_response(gpt_response)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/regenkey', methods=['POST'])
@require_loggedin_ajax
def regenkey(user):
    id = request.form.get('id')
    key = request.form.get('key')
    gpt_response = AINPC(session.get['user_id']).regen_npc_key(id, key, temperature=0.9)
    response = make_response(gpt_response)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/createnpc', methods=['POST'])
@require_loggedin_ajax
def createnpc(user):
    # Get all the form data
    keys = request.form.keys()
    npc_dict = {}
    game_id = request.form.get('game_id')
    for key in keys:
        if (key == 'game_id'):
            continue
        npc_dict[key] = request.form.get(key)
    
    npc = AINPC(session.get['user_id']).gen_npc_from_dict(game_id=game_id, npc_dict=npc_dict)
    response = make_response(npc.data)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/deletename', methods=['POST'])
@require_loggedin_ajax
def deletename(user):
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
@require_loggedin_ajax
def gennpcimage_stability(user):
    id:int = int(request.form.get('id'))
    npc = NPC(id)
    print(npc.data['name'])
    prompt = "epic 300mm professional highly realistic photo of a " +str(npc.data['age'])+" year old "+ str(npc.data['gender']) + " " + str(npc.data['race']) + " " + str(npc.data['class_']) + ", fantasy, looking at the camera, with " + str(npc.data['hair']) + " " + str(npc.data['hair_style']) + " " + " hair and " + str(npc.data['eyes']) + " " + str(npc.data['eyes_description']) + " eyes, " + str(npc.data['chin']) + " chin,  " + str(npc.data['clothing']) + ", " + str(npc.data['ears']) + " ears, " + str(npc.data['features']) + ", " + str(npc.data['mouth']) + " mouth, " + str(npc.data['nose'] + " nose, trending on deviant art, best quality, masterpiece, extremely high detail digital RAW color photograph, 4k, highly detailed, upper body")
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
                TokenLog().add("Generate Stability Image", 0, 0, 0.002, session.get('user_id'))
                img = Image.open(io.BytesIO(artifact.binary))
                img.save(os.path.join(DIR_ROOT, 'static', 'img', 'npc', str(id)+'.png'))

    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/gennpcimage', methods=['POST'])
@require_loggedin_ajax
def gennpcimage(user):
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
    TokenLog().add("Generate OpenAI Image", 0, 0, 0.018, session.get('user_id'))
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
@require_loggedin_ajax
def addname(user):
    id = request.form.get('id')
    game_id = request.form.get('game_id')
    npc = NPC(id)
    npc.update(game_id = game_id)
    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/createplotpoint', methods=['POST'])
@require_loggedin_ajax
def createplotpoint(user):
    title = request.form.get('title')
    details = request.form.get('summary')
    game_id = request.form.get('game_id')
    plot_point = PlotPoints(game_id).add(game_id, title, details=details)
    response = make_response(plot_point.data)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/createreminder', methods=['POST'])
@require_loggedin_ajax
def createreminder(user):
    title = request.form.get('title')
    details = request.form.get('details')
    trigger = request.form.get('trigger')
    game_id = request.form.get('game_id')
    reminder = Reminders(game_id).add(title, details=details, trigger=trigger)
    response = make_response(reminder.data)
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/getreminders', methods=['POST'])
@require_loggedin_ajax
def getreminders(user):
    game_id = request.form.get('game_id')
    reminders = []
    for reminder in Reminders(game_id).get_all():
        reminders.append(reminder.data)
    return send_flask_response(make_response, reminders)

@app.route('/deletereminder', methods=['POST'])
@require_loggedin_ajax
def deletereminder(user):
    id = request.form.get('id')
    Reminder(id).delete()
    response = make_response("OK")
    response.mimetype = "text/plain"
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/uploadaudio', methods=['POST'])
@require_loggedin_ajax
def uploadaudio(user):
    audio_file = request.files['audio_file']
    if audio_file.filename == '':
        return send_flask_response(make_response, [{"error": "No file selected"}])
    uploaded_filename = secure_filename(audio_file.filename)
    uploaded_ext = os.path.splitext(uploaded_filename)[1]
    if uploaded_ext not in ['.mp3']:
        return send_flask_response(make_response, [{"error": "Invalid file type"}])
    
    game_id = request.form.get('game_id')
    file_name = str(game_id) + "-" + str(uuid.uuid4())+".mp3"
    file_path = os.path.join(DIR_ROOT, 'tmp', file_name)
    audio_file.save(file_path)

    task = Tasks().add(game_id, "Process Audio", "Queued")
    #p = Process(target=split_audio, args=(task_id,file_path))
    #p.start()
    thread = threading.Thread(target=split_audio, args=(task.data['id'],file_path, Game(game_id)))
    thread.start()
    return send_flask_response(make_response, [task.data['id']])

@app.route('/getaudiostatus', methods=['POST'])
@require_loggedin_ajax
def getaudiostatus(user):
    task_id = request.form.get('task_id')
    task = Task(task_id)
    return send_flask_response(make_response, [task.data['status'], task.data['message']])

@app.route('/creategame', methods=['POST'])
@require_loggedin_ajax
def creategame(user):
    name = request.form.get('game_name')
    abbr = request.form.get('abbr')
    game = Games().add(name, abbr, session.get('user_id'))
    return send_flask_response(make_response, [game.data['id']])

@app.route('/waitlist', methods=['POST'])
def waitlist():
    email = request.form.get('email')
    user = Waitlist().add(email)
    return render_template('loginprompt.html', message="You have been added to the waitlist. You will be notified when your account is ready.")

@app.route('/cancelmembership', methods=['POST'])
@require_loggedin_ajax
def cancelmembership(user):
    stripe.api_key = os.getenv("STRIPE_API_KEY")
    stripe.Subscription.modify(
        user.data['stripe_subscription_id'],
        cancel_at_period_end=True
    )

    user.update(membership="free")

    return send_flask_response(make_response, ["OK"])

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
    app.run(port=os.getenv("SERVER_HTTP_PORT"))
