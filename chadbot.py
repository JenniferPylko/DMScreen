import nextcord
from nextcord.ext import commands
import os
import json
import dotenv

from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    HumanMessage,
    SystemMessage,
)
from langchain.tools import format_tool_to_openai_function
from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.question_answering import load_qa_chain

VERSION: float = 0.1
#DEFAULT_MODEL: str = "gpt-4-0613"
DEFAULT_MODEL: str = "gpt-3.5-turbo-0613"
DEFAULT_TEMPERATURE: float = 0.9
BOT_DESCRIPTION = "A bot that records sessions, and interacts with the players"
PERSONALITY="""You are a friendly assistant named Chad that is an expert on the topic of D&D. You are
        Craig's replacement and are insecure about your abilities. You are very sassy. You worry that
        you are not as good as Craig, which makes you a little overconfident at times, but you are
        eager to learn new skills, and improve your-self.

        If you are not directly mentioned in a message, you should only respond with "NONE"        
        """
PINECONE_INDEX_NAME = "5e"

if "OPENAI_API_KEY" not in os.environ:
    print("Please set the OPEN_API_KEY environment variable to your OpenAI API key.")
    exit(1)

intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(description=BOT_DESCRIPTION, intents=intents, command_prefix='$')
chat = ChatOpenAI(model_name=DEFAULT_MODEL, temperature=DEFAULT_TEMPERATURE, openai_api_key=os.environ["OPENAI_API_KEY"])
chat_history:list = [
    SystemMessage(content=PERSONALITY)
]

embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
reference_instance = Pinecone.from_existing_index(PINECONE_INDEX_NAME, embedding=embeddings)

sessions = []

functions = [{
    "name": "help",
    "description": "Get help with the bot, and its capabilities",
    "parameters": {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "enum": ["help", "doc search"],
                "description": "The tool to get help with"
            }
        },
        "required": ["tool"]
    },
    "name":"query_vectorstore",
    "description": "Query the official D&D documentation for an answer to your question",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question you want to ask"
            }
        },
        "required": ["query"]
    }
}]

def show_help_message():
    return """
    Here are the tools I can use:
- help: Get help with the bot, and its capabilities
- doc search: Chat with Chat about D&D based on all of the published D&D books, as well as lots of 3rd party content
    """

def search_vectorstore(query, model_name=DEFAULT_MODEL, temperature=DEFAULT_TEMPERATURE):
    docs = reference_instance.similarity_search(query, k=4)
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=temperature, openai_api_key=os.environ["OPENAI_API_KEY"])
    chain = load_qa_chain(llm, chain_type="stuff", verbose=True)
    answer = chain.run(input_documents=docs, question=query, verbose=True)
    return answer

def send_llm_message(message, temperature=DEFAULT_TEMPERATURE, model=DEFAULT_MODEL):
    print(f"Sending to LLM: {message}")
    human_message = HumanMessage(content=message)
    chat_history.append(human_message)
    response = chat.predict_messages(chat_history, functions=functions)
    print(response)
    print(type(response))

    if "function_call" in response.additional_kwargs:
        function_call = response.additional_kwargs["function_call"]
        print(f"Calling function: {function_call['name']}")
        match function_call["name"]:
            case "help":
                return show_help_message()
            case "query_vectorstore":
                arguments = json.loads(function_call["arguments"])
                return search_vectorstore(query=arguments["query"])
            case _:
                return "I don't know how to do that."
    else:
        chat_history.append(response)
        print(response.content)
        answer = response.content
        print(f"LLM Answer: {answer}")
        return answer

@bot.slash_command(description="Invite Chad to your channel!")
async def join(interaction: nextcord.Interaction):
    print(interaction.channel)
    print(interaction.channel_id)
    print(interaction.guild)
    print(interaction.user)
    print(interaction.user.id)
    print(interaction.user.name)
    sessions.append(interaction)
    await interaction.send("Howdy folks! I just logged in.", ephemeral=False)

@bot.slash_command(description="Ask Chad to leave the channel")
async def leave(interaction: nextcord.Interaction):
    for session in sessions:
        if session.channel_id == interaction.channel_id:
            sessions.remove(session)
    await interaction.send("Bye folks! I'm logging out.", ephemeral=False)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord with user ID: {bot.user.id}!')

@bot.event
async def on_message(message: nextcord.Message):
    # don't respond to ourselves and only in the right channel
    if message.author == bot.user:
        return
    in_session = False
    for session in sessions:
        if session.channel_id == message.channel.id:
            in_session = True
    if not in_session:
        return
    
    print(f"{message.author.name} said {message.content}")
    llm_response = send_llm_message(message.content)
    print(f"LLM Response: {llm_response}")
    if (llm_response != "NONE"):
        await message.channel.send(llm_response)

    await bot.process_commands(message)

bot.run(os.environ["DISCORD_API_KEY"])