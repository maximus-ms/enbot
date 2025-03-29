# EnBot - English Learning Assistant

In this document, I describe my project idea. The project is a tool based on Telegram Bot that helps to learn English words. The main ideas are that the bot should be a Telegram bot and should use the Telegram API.

The bot should be able to accept lists of words which users want to learn. The list of words will be just regular text with no translation. There's no transcription whatever. The bot should be able to take this list of words, parse it, and create a database for new words to learn.

Every word... not actually the bot... excuse me. Take every word... and not like this. The list of words to learn should be semicolon-separated, so it can be not a single word but a phrase. The bot takes this list, parses it, and puts them into the database for every single item (word or phrase).

Both should increase or add more data, more information about this word or phrase to learn. What should be added? First of all, the translation to Ukrainian should be added. Actually, the capability should be that users can select two languages: which to learn and what is their native language. So there should be an option for configuration. For example, users can select English as the target language and Ukrainian as their native language.

So when the bot receives the list of words, it parses it and adds additional information to each item. What should be the additional information? Additional information should include:

- Translation (this is very important and mandatory)
- Transcription (if it is in English)
- Pronunciation (taken from some online resource, maybe from some API from Google Translator or from 11 labs - we need to think about it)
- Pictures (if possible)
- Example sentences (3-5 different use cases for this word)

All this information about words is kept in a dictionary, and the dictionary is actually the database. We should decide which database should be used.

Another functionality for the bot is to teach users or help users learn words. Every time when a user wants to learn new words, the bot should select with some algorithm (we will think about this algorithm later) and select some words and propose to the user to learn them.

How can we learn with the bot? First of all, first option: so it is both right... the English word for example, and proposes two, three, or four options of translation, and the user should select that just to press a button and select this. So at the correct one, and the bot checks if it is correct or not and responds accordingly.

Every time when the bot proposes the word, there should be a button to pronounce this word, to show use cases, maybe pictures (now I don't know about the picture).

The second option how the bot could propose user to learn the word is to defend the translation in Ukrainian or in the native language and propose a few options (maybe 4 options) to guess what the word is in English. And those words should be... I mean, options should be like they should be really similar to the target word.

The third option to launch is: the bot proposes the native translation of this word, and the user should type the correct variant of this word. Every time when the user responds, the bot should answer if this is correct or if it is wrong, and maybe correct if it is just a small typo, and propose to the user again to ask if this word was remembered or the user just guessed it.

The next logic is about the algorithm how to learn words. Based on the answer from the user, if the word is learned, the system or the bot should accept if it is. If this word is learned or not, and apply some special algorithm. Of course, repetition of this word. The logic of this algorithm is to repeat the word in different time frames. For example:

1. First, the user learns the word, so this word is marked as learned at stage 1
2. The next time this word will appear in the study after one day
3. The next time again on the next day, user should mark it as learned
4. The next time this word should appear in this study process should be in three days
5. The next should be 5 days
6. Then 10 days
7. And one month

Those periods, the number of those periods, and the period itself should be configurable.

The Telegram Bot should be able to send kind of invitation message to the user to invite the user to start training/learning. For example, users can configure that they want to start learning every day at 11:00 PM. So users can configure this, and sometimes every day around this timeframe, the bot will send a message to the user that they should learn words.

The bot should count the number of learned words in total for the last day, one week, or one month. So it is kind of type of statistics. The bot should count the number of learned words and spent minutes every day and also have some statistics which will represent the learning tempo of the user for every day, every week, every month, whatever.

As well, it should track the number of learned words and spent minutes during this day and then notify the user like someone at the end of the day or before the end of the day that the user has not spent enough time on learning words. For example, users can configure that they want to spend 10 minutes every day on this and they want to learn three or five words every day.

The next feature should be that the multi-user bot should be able to keep the statistics per user ID. The statistics and all information about the user progress, about the user's learned words, etc., should be stored in the database. This database type we will decide later.

The Telegram bot should be written in Python, should be online 24/7, and should be implemented and packed in a Docker container. The Telegram Bot should have an admin panel, so one or more users can be added as admin in order to see the statistics for the Telegram bot (not per user but generally: how many words you have in the dictionary, how many users, how many minutes, how much time was spent on the learning, general or general any other information, maybe some configurations for this bot as well).

Configuration for the bot and for every user and all addition of proper dictionary should be stored in the database, and when we reboot the bot, it should continue. It should not lose the information and should be able to continue studying. I mean like learning the process.

Every dictionary for every pair (like English-Ukrainian, English-Russian, Polish, etc.) should be a separate database. The database type we think we will decide later.

1.1 any delimiter can be used
1.2 yes, in the same input can be single words and phrases
2. yes, these are default values, and user can set a number of periods and each period len in days
3. type of database we will define separatelly. every user can add multiple language pairs, the statistic and progress should be per user per pair (but in the same telegramm chat)
4. admin panel is not defined yet. everything we will find usefull will be added there, admin should be able see only statistic per user but not delete them. and admin can add another user as admin (more the one admin is possible). should be some security mechanism to add another admins. and only the master admin can add other admins.
5.1 every learning model shold be as a separate class, we will add more models if needed. word is learned only after model-set is passed (model-set is a set of learning models selected by user). currently these 3 models are selected by default for all users.
5.2 user can specify number of minutes or\and words he want to learn every day as minimum.
6. if there is no new words in the corresponding dictionary EnBot should notify user about this.
7. every words in the dictionry has learning priority (it is per user). from the beggining all words have same (low) priority. everytime user add new word(s) phrase bot ask which learning priority this set should have.
8. every time user add new words\phrases EnBot checks if it has it in internal dict of the corresponding pair, and doesn't add it but only edit correspinding priority for the item for this user.
9. all databeses should be accessabel/readable/editable manually in corresponding GIU.
10. pictures and pronosiations should be stored in sepatated dictionaries with corresponding file names (should be understandable for which word\phrase this prononsiation\picture is) and database only keep file path to the file.
11. sourse of prononciations, pictures, usecase examples - we will define later. most probably we will use some AI based resource with API to generate such materials once per word and safe it localy in data base. maybe we will try to use free subscription plan with limited number of requests per day, so EnBot will be able to add such materiald step-by-step everyday using only accessible free tockens.
12. everything should be writen in modular manner: frontend (telegram bot) is separated from backend, every dict-pair, evry user, every leraning method, etc.

The EnBot will be in git.
All database will be on disc in one big directory. reserve copy of this dir will be done separatelly. 
All user information (progress) will be stored forever, but can be deleted manualy by admin by deleting correspondin table in database GUI (every user should have own db with progres and config)
There shuld be 10 levels of priority. everytime when user add a new set of words with the higset priority (per day) all words with priority higher than 0 should get priority which is current_prio-1 (but only if we downgrade the priority for one prio-set of words steps on another prio-set of words) 
When user learn he should get words only from the highest prio-set. 
EnBot shold keep in learning cycle 10 words (configurable by user). meaning EnBot selects 10 words from the highest prio-set (if not enough, it can take words from the lower prio-set) and learn these words,
When user marked the word as learned this word in taken out from the learning-cycle for today. no new words are added. Once all 10 words from the learning-cycle are learned, EnBot offers to repeat oll these just learned words and proprse some easy test to repeat them (if user makes mistake on this stage the word should not be marked as non-learned)
Examples -  sentences shold be short but have sence. User should be able to ask EnBot to mark this example as not good (EnBot can even delete it and create another)
Pictures should not be large, maybe 320x240 we will define it separatelly.
Statistic: spent time, number of words, that's it for now, may be added later.
Gamification - not sure, not now. maybe later.

1. usual learning-cycle size is 10 words (can be configured)
- one learning-cycle is one day
 - if user finished the learning-cycle Enbot notifys, user can start one more leraning-cycle for todya.
 - if user didn't finish learning-cycle "today" this cycle will be continue next day.
 - user can config the when the next day starts (for example it can be at 3 AM (i think it has to be the default value))
2. cooldown: 1 mounth will couse -1 in prio level but only if the priority is higher than 5
- priority logging - yes, messages can be logged in database (per user)
- all changes should be lodded in db (per user) - learned words, finished learning-cycles, added words,, etc.
- all messages from EnBot to user should be short (do not overload chat in telegramm)
3. no max size per user
- no automatic optimization.
- admin user can ask EnBot a statistic of DBs memory size, etc.
4.No backup mechanism in this project. all data should be in a dir, so backup can be done manually by coping this entire dir.
5. Admin user can act as a regular user to learn words, and can switch to admin mode to ask as admin and switch back to user mode.