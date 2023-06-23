# TODO
## DM Screen
### v0.1 - Personal Use
- Craig needs to notice important events such as character death
- Move game notes into its own object
- Update ChatBot to use functions instead of LangChain templates
- Improve prompt to get only proper nouns back from ChatBot
- Find Todo messages in notes, and put them in plans and ideas
- Work on a way to organize plans and ideas
- Update ChatBot, let the user type the following
- - Create NPC with black hair...
- - Remind me to...
- Add Random Everything Generator
- Let user manage players and characters
- Let user manage locations
- Let user edit date for notes
- Let user edit/delete notes
- Show thinking... when ChatBot is working on a response
- Handle 500 errors
- Make toggle button bar work
- Move CSS and JS to their own files
- Noun dropdown option in ChatBot to "Tell me more..."
- Right click on ChatBot response to add it to notes
- Let user edit/type details for NPCs
- Let user edit/dropdown from XML for NPCs
- When game notes sees a proper noun, highlight it
- Call out spells/abilities/classes/races/etc. in ChatBot and add dropdown to see full details
- Pre-select pinecone filter based on the selected game
- Figure out how to stream chat responses
- Let user manage games (add/delete/preferences)
- Add notes to an NPC

### v0.2 - Private Beta
- Unify handling of wait messages while waiting for AI to complete
- Make sure all data is tied to a user/game
- Login/Register/Forgot Password
- Move to DigitalOcean
- HTTPS

### v0.3 - Welcome to the Future!
- Support other systems and genres

## ChadBot
- Bind ChadBot to a specific channel
- Record Audio
- Replace whisper.py/split_audio.py to transcribe audio
- Improve cost effectiveness of ChadBot (too many gpt4 queries)
- Audio listener should recognize when a command is given to it, and handle it.
- Update self based on voice wishes