import requests
import random
import string
import datetime
from telegram import Update, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from telegram.constants import ParseMode  # Updated import for ParseMode

# API Keys
DEEPAI_API_KEY = "c6e15240-074c-40e0-9650-eae94c5e75a4"  # Replace with DeepAI API key
TMDB_API_KEY = "526cadfefc9e1883d7e4d73e799bd07c"      # Replace with TMDB API key
BOT_TOKEN = "7908847221:AAFo2YqgQ4jYG_Glbp96sINg79zF8T6EWoo"   # Replace with Telegram bot token
OWNER_ID = 7877197608                    # Replace with your Telegram user ID

# Storage for redeem codes and subscriptions
redeem_codes = {}
user_subscriptions = {}
subscription_expiry = {}  # Store expiration dates

# Function to check subscription
def is_subscribed(user_id):
    return user_subscriptions.get(user_id, False) or user_id == OWNER_ID

# Function to check if subscription is about to expire
def check_subscription_expiry(context: CallbackContext):
    for user_id, expiry_date in subscription_expiry.items():
        if expiry_date - datetime.timedelta(days=1) == datetime.date.today():
            # Notify user one day before expiry
            context.bot.send_message(
                user_id, text="Your subscription is about to expire tomorrow! Renew it to continue enjoying premium features."
            )

# /aimg command handler
def ai_image(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        update.message.reply_text("You need a subscription to use this feature. Use /redeem to activate.")
        return

    user_prompt = ' '.join(context.args)
    if not user_prompt:
        update.message.reply_text("Please provide a prompt for the AI image generation.")
        return

    try:
        url = "https://api.deepai.org/api/text2img"
        headers = {"api-key": DEEPAI_API_KEY}
        data = {"text": user_prompt}

        response = requests.post(url, headers=headers, data=data).json()
        image_url = response.get("output_url", None)
        if image_url:
            update.message.reply_photo(photo=image_url, caption="Here is your AI-generated image!")
        else:
            update.message.reply_text("Failed to generate image.")
    except Exception as e:
        update.message.reply_text(f"Error generating image: {e}")

# /moviesearch command handler
def movie_search(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        update.message.reply_text("You need a subscription to use this feature. Use /redeem to activate.")
        return

    movie_name = ' '.join(context.args)
    if not movie_name:
        update.message.reply_text("Please provide the name of the movie you want to search for.")
        return

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    response = requests.get(url).json()

    if response.get("results"):
        movie = response["results"][0]
        title = movie.get("title", "N/A")
        overview = movie.get("overview", "N/A")
        poster_path = movie.get("poster_path")
        image_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

        message = f"🎬 *{title}*\n\n{overview}"
        if image_url:
            update.message.reply_photo(photo=image_url, caption=message, parse_mode=ParseMode.MARKDOWN)
        else:
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text("No results found for your movie search.")

# /genredeem command handler (Owner only)
def genredeem(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 1 or context.args[0] not in ["bronze", "silver", "gold"]:
        update.message.reply_text("Usage: /genredeem <plan>\nPlans: bronze (1 week), silver (3 weeks), gold (1 month)")
        return

    plan = context.args[0]
    code = '-'.join([''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)])
    redeem_codes[code] = {"plan": plan, "used": False}

    update.message.reply_text(f"Generated Redeem Code for {plan.capitalize()} Plan:\n`{code}`", parse_mode=ParseMode.MARKDOWN)

# /redeem command handler
def redeem(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if len(context.args) != 1:
        update.message.reply_text("Usage: /redeem <code>")
        return

    code = context.args[0]
    if code not in redeem_codes:
        update.message.reply_text("Invalid redeem code.")
        return

    if redeem_codes[code]["used"]:
        update.message.reply_text("This redeem code has already been used.")
        return

    # Activate subscription based on plan
    plan = redeem_codes[code]["plan"]
    redeem_codes[code]["used"] = True
    duration = {"bronze": "1 week", "silver": "3 weeks", "gold": "1 month"}[plan]

    user_subscriptions[user_id] = True
    expiry_date = datetime.date.today() + datetime.timedelta(weeks={"bronze": 1, "silver": 3, "gold": 4}[plan])
    subscription_expiry[user_id] = expiry_date

    update.message.reply_text(f"Subscription activated! Enjoy your {duration} of premium access. Your subscription expires on {expiry_date}. User ID: {user_id}")

# Main function to start the bot
def main():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("aimg", ai_image))
    dispatcher.add_handler(CommandHandler("moviesearch", movie_search))
    dispatcher.add_handler(CommandHandler("genredeem", genredeem))
    dispatcher.add_handler(CommandHandler("redeem", redeem))

    # Check subscription expiry every day
    job_queue = updater.job_queue
    job_queue.run_daily(check_subscription_expiry, time=datetime.time(12, 0, 0))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
