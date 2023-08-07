# TODO
## DM Screen

### v0.2 
- BUG: I can see Red Hand of Doom
- BUG: You should not be able to "Save Notes" When a game is not selected
- Set up billing
- Move Logs to their own folder

### v0.5 - Public Beta
- Click on a chat message to make a DM Screen helpful note (Holywater does 2d6 damage). Click to get full description of rules
- Add ability to delete a game
- Audio Transcripts
- - Remember to check upload status when returning to a game (and disable upload if needed)
- - Inject notes to vectorstore when processing complete
- - Send email when processing complete
- Add ability to upload documents
- Add ability to upload a picture of an NPC instead of generating one
- Let user edit/type details for NPCs
- Add Random Everything Generator
- Unify handling of wait messages while waiting for AI to complete
- Make sure all data is tied to a user/game
- Login/Register/Forgot Password
- Craig needs to listen for explicit future ideas
- There needs to be an option for Craig to suggest story direction.
- Let user manage players and characters
- Let user manage locations
- When game notes sees a proper noun, highlight it
- Call out spells/abilities/classes/races/etc. in ChatBot and add dropdown to see full details
- Figure out how to stream chat responses
- Add notes to an NPC
- Right click on ChatBot response to add it to notes
- Make toggle button bar work
- Add a button for creative output from chatbot (that does not use context)
- Find Todo messages in notes, and put them in plans and ideas
- Add a button to chatbot to report when it doesn't do what the user expected
- Noun dropdown option in ChatBot to "Tell me more..."
- Let user edit/dropdown from XML for NPCs
- Add ability to maximize a section for better handling/visibility
- Create stock NPC names based on race
- Migrate to MySql
- - Set up proper relationships between tables (foreign/unique keys, etc)

#### Multi-Game Support
- Let user manage games (add/delete/preferences)
- Pre-select pinecone filter based on the selected game
- When refresshing, either remember the selected game

#### Chadbot
- Train Chad on whether a message is intended for him or not
- Record Audio
- Audio listener should recognize when a command is given to it, and handle it.

### v1.0 - Initial Release
- Work on a way to organize plans and ideas
- Manage Locations
- Integrated Random Everything Generator
- Manage TODO
- Manage Players
- - Import from D&D Beyond
- - - Sync?
- - Import from Demiplane?
- - Foundry Support
- - Roll20 Support
- - Other VTT Support?
- - Manage Story Board

#### Chadbot
- Update self based on voice wishes

### v1.1 - Welcome to the Future!
- Add Plot Points. 
- - Nodes that are draggable and linkable to each other
- - Add tags
- - Filter on tags
- - Add status indicators
- - Attach images, notes, npcs, maps, etc.
- - Link from npcs to plotpoints
- - Set alarms. Notify when conditions are met (time, session, events in notes)
- - AI to suggest other plot points
- Support other systems and genres