from pyrogram import Client, filters
from pymongo import MongoClient
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import logging

# MongoDB connection and initial setup
mongo_client = MongoClient("mongodb://localhost:27017/")
my_bot_db = mongo_client["myBotDB"]  # Your database name here
users_collection = my_bot_db["users"]

# Your Pyrogram and MongoDB setup
api_id = "25853361"
api_hash = "d48600a21703b6dbcb24d5e3b9b2c417"
bot_token = "6666250520:AAE-nww-R-l39a-srkaII26CL6vT6gjZ3rY"

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Client("my_bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def is_user_registered(user_id):
    return users_collection.count_documents({"user_id": user_id}) > 0

def register_user(user_id, username):
    users_collection.insert_one({
        "user_id": user_id,
        "username": username,
        "phone_number": None,
        "full_name": None,
        "team": None,
        "birthday": None,
        "is_approved": False
    })

async def ask_for_team(chat_id):
    team_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Design", callback_data="team_Design")],
        [InlineKeyboardButton("Leadgen", callback_data="team_Leadgen")],
        [InlineKeyboardButton("Sales", callback_data="team_Sales")]
    ])
    await app.send_message(chat_id, "Please select your team:", reply_markup=team_keyboard)

@app.on_message(filters.contact)
async def handle_contact(client, message):
    user_id = message.from_user.id
    if not is_user_registered(user_id):
        register_user(user_id, message.from_user.username)
        users_collection.update_one({"user_id": user_id}, {"$set": {"phone_number": message.contact.phone_number}})
        await ask_for_team(message.chat.id)
    else:
        await message.reply("You are already registered.")

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    if not is_user_registered(user_id):
        await message.reply("Welcome! Please share your phone number.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Share Phone Number", request_contact=True)]], one_time_keyboard=True, resize_keyboard=True))
    else:
        await message.reply("You are already registered. Use /profile to view or update your details.")

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    data = callback_query.data
    if data.startswith("team_"):
        team = data.split("_")[1]
        user_id = callback_query.from_user.id
        await update_user_data(user_id, {"team": team})
        await callback_query.answer("Team selected: " + team)
        await callback_query.message.edit_text(f"Team {team} selected. Please enter your full name:")

async def update_user_data(user_id, data):
    users_collection.update_one({"user_id": user_id}, {"$set": data})

@app.on_message(filters.command("profile"))
async def profile(client, message):
    user_id = message.from_user.id  # This is always an integer.
    logger.info(f"Received /profile command from user_id: {user_id}")

    try:
        # Ensure data type consistency; convert user_id to string if necessary.
        user_data = users_collection.find_one({"user_id": user_id})
        
        if user_data:
            logger.info(f"User data: {user_data}")  # Debugging line to check what data is retrieved.
            profile_message = f"Your Profile Details:\n\n" \
                  f"Full Name: {user_data.get('full_name', 'N/A')}\n" \
                  f"Team: {user_data.get('team', 'N/A')}\n" \
                  f"Birthday: {user_data.get('birthday', 'N/A')}\n" \
                  f"Phone Number: {user_data.get('phone_number', 'N/A')}"
            await message.reply_text(profile_message)
            logger.info("Profile details sent to the user.")
        else:
            logger.warning(f"No user data found for user_id: {user_id}")
            await message.reply_text("Profile details not found.")
    except Exception as e:
        logger.error(f"Error in /profile command: {e}", exc_info=True)
        await message.reply_text("An error occurred while fetching profile details.")


@app.on_message(filters.text)
async def handle_text_input(client, message):
    # Manually check if the message starts with a slash, indicating a command
    if message.text.startswith('/'):
        return  # Ignore commands

    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    # Your existing logic here...


    if "phone_number" in user_data and not user_data.get("full_name"):
        await update_user_data(user_id, {"full_name": message.text})
        await message.reply("Please enter your birthday (YYYY-MM-DD):")
    elif "full_name" in user_data and not user_data.get("birthday"):
        try:
            # Validate birthday format
            birthday = datetime.strptime(message.text, "%Y-%m-%d")
            await update_user_data(user_id, {"birthday": message.text})
            # After collecting all data, offer to show the profile
            profile_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("View Profile", callback_data="view_profile")]
            ])
            await message.reply("Registration complete! You can view your profile anytime.", reply_markup=profile_button)
        except ValueError:
            await message.reply("Invalid date format. Please enter your birthday in YYYY-MM-DD format.")

# Run the bot
app.run()
