import os
import json
import logging
from typing import List
from models import NPCs, NPC
import dmscreenxml
import openai

logging.basicConfig(level=logging.DEBUG)

class AINPC():
    __default_model = "gpt-3.5-turbo-0613"
    __dir_xml = os.path.join(os.path.dirname(os.path.realpath(__file__)), "xml")
    create_npc_openai_functions = {
        "name": "generate_npc",
        "description": "Generate a NPC for Dungeons and Dragons 5e. If you do not know the value of a field, create a new one. Keep it as realistic as possible.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the NPC"
                },
                "race": {
                    "type": "string",
                    "description": "The race of the NPC"
                },
                "class_": {
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
            "required": ["name", "race", "class_", "background", "alignment",
                        "gender", "age", "height", "weight", "hair", "eyes",
                        "eyes_description", "hair_style", "ears", "nose", "mouth",
                        "chin", "features", "flaws", "ideals", "bonds", "personality",
                        "mannerisms", "talents", "abilities", "skills", "languages",
                        "inventory", "body", "clothing", "hands", "jewelry", "voice",
                        "attitude", "deity", "occupation", "wealth", "family", "faith",
                        "summary"]
        }
    }

    def __init__(self, model_name=None):
        self.__default_model = model_name if model_name is not None else self.__default_model

    def get_npc(self, id: int, temperature: float = 0.9, model: str = 'gpt-3.5-turbo-16k', quick: bool = False):
        npc = NPC(id) # First, try to get the NPC from the database, before doing the expensive GPT-3.5-0613 call

        # if npc has the key, race, then it is a completed NPC, so we can just return it
        if (npc.data["background"] != None):
            return npc

        # If we get here, the NPC is in the database as a placeholder, so we need to generate the all of the details
        if (quick == True):
            # Quick mode, use DMScreenXML
            dmscreen_npc = dmscreenxml.DMScreenXML(os.path.join(self.__dir_xml, 'npc.xml'))
            npc_dict = dmscreen_npc.get_all_values()
            npc_dict["name"] = npc.data["name"]
            return npc.update(**npc_dict)
        else:
            # Slow mode, use GPT-3.5-0613 functions to generate the NPC
            response = openai.ChatCompletion.create(
                model = 'gpt-3.5-turbo-0613',
                messages = [{
                    "role": "user",
                    "content": "Create a NPC for Dungeons and Dragons 5e whose name is "+npc.data["name"]+"."
                }],
                functions = [ self.create_npc_openai_functions ],
                function_call = {"name": "generate_npc"}
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
                logging.error("No function call in response from OpenAI")
                return None

    def get_npc_summary(self, id:int, model="gpt-3.5-turbo-0613", temperature="0.5"):
        npc = NPC(id)
        npc_description = ""
        for key in npc.data:
            if npc.data[key] != None:
                npc_description += str(npc.data[key]) + "\n"
        print(npc_description)
        response = openai.ChatCompletion.create(
            model = model,
            messages = [{
                "role": "user",
                "content": f"Write a summary of the following NPC:\n{npc_description}"
            }],
            functions = [
                {
                    "name": "show_npc_summary",
                    "description": "Display a summary of an NPC for Dungeons and Dragons 5e",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "A summary of the NPC"
                            }
                        },
                        "required": ["summary"]
                    }
                }
            ],
            function_call = {"name": "show_npc_summary"}
        )
        print(response)
        message = response["choices"][0]["message"]
        if (message.get("function_call")):
            function_name = message["function_call"]["name"]
            args = message.get("function_call")["arguments"]
            print(args)
            args_json = json.loads(args)
            print(args_json)
            npc.update(summary=args_json["summary"])
            return args_json["summary"]
        else:
            logging.error("No function call in response from OpenAI")
            return None

    def regen_npc_key(self, id, field_, model="gpt-3.5-turbo-0613", temperature="0.5"):
        npc = NPC(id)
        values = ""
        for key in npc.data:
            if npc.data[key] != None:
                if key == 'id':
                    continue
                values += str(key) + ": " + str(npc.data[key]) + "\n"
        response = openai.ChatCompletion.create(
            model = model,
            messages = [{
                "role": "user",
                "content": f"""Create a new value for the following field. The value should make
                sense in the context of the NPC, and should not be the same as its original
                value.:
                {values}

                Field to change: {field_}
                Original Value: {npc.data[key]}

                """
            }],
            functions = [
                {
                    "name": "regen_npc_key",
                    "description": "Save the new value for the field: {field_}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "The new value of {field_}"
                            }
                        },
                        "required": ["value"]
                    }
                }
            ],
            function_call = {"name": "regen_npc_key"}
        )
        print(response)
        message = response["choices"][0]["message"]
        if (message.get("function_call")):
            function_name = message["function_call"]["name"]
            args = message.get("function_call")["arguments"]
            print(args)
            args_json = json.loads(args)
            print(args_json)
            npc.update(**{key: args_json["value"]})
            return args_json["value"]
        else:
            logging.error("No function call in response from OpenAI")
            return None

    def gen_npc_from_dict(self, npc_dict=None) -> NPC:
        attributes: str = ""
        for key in npc_dict:
            if npc_dict[key] != None and len(npc_dict[key]) > 0:
                attributes += str(key) + ": " + str(npc_dict[key]) + "\n"

        function_args = ["name", "race", "class_", "background", "alignment", "gender", "age",
                         "height", "weight", "hair", "eyes", "eyes_description", "hair_style",
                         "ears", "nose", "chin", "mouth", "features", "flaws", "ideals", "bonds",
                         "personality", "mannerisms", "talents", "abilities", "skills", "languages",
                         "inventory", "body", "clothing", "hands", "jewelry", "voice", "attitude",
                         "deity", "occupation", "wealth", "family", "faith"]
        function_properties = {}
        for key in function_args:
            function_properties[key] = {
                "type": "string",
                "description": f"The {key} of the NPC"
            }
        function_args.append("summary")
        function_properties["summary"] = {
            "type": "string",
            "description": "A summary of the NPC"
        }

        response = openai.ChatCompletion.create(
            model = self.__default_model,
            messages = [{
                "role": "user",
                "content": f"""Create an NPC for Dungeons and Dragons 5e that has the following
                attributes. These are only the known attributes of the NPC. Create all other 
                attributes. The NPC should be as realistic as possible, and should be able to
                be used in a game of Dungeons and Dragons 5e. The NPC should be able to be
                non-player character. Do not leave any fields blanks.

                KNOWN ATTRIBUTES:
                {attributes}

                CREATED ATTRIBUTES:
                """,
            }],
            functions = [
                {
                    "name": "gen_npc_from_dict",
                    "description": "Generate a NPC for Dungeons and Dragons 5e",
                    "parameters": {
                        "type": "object",
                        "properties": function_properties,
                        "required": function_args
                    }
                }
            ],
            function_call = {"name": "gen_npc_from_dict"}
        )
        print(response)
        message = response["choices"][0]["message"]
        if (message.get("function_call")):
            function_name = message["function_call"]["name"]
            args = message.get("function_call")["arguments"]
            print(args)
            args_json = json.loads(args)
            print(args_json)
            return NPCs().add_npc(args_json["name"], args_json)
        else:
            logging.error("No function call in response from OpenAI")
            return None
