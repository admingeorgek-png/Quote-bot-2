"""
LifeSpark - Telegram Daily Quotes & Advice Bot
-----------------------------------------------
Features:
- /start          -> registers the user for the daily broadcast
- /stop           -> unsubscribes the user
- /today          -> Today's Quote
- /advice         -> Life Advice
- /motivation     -> Motivation
- /relationships  -> Relationships
- /mindset        -> Mindset
- /night          -> Night Reflection
- Daily job       -> automatically sends "Today's Quote" to every subscribed user

SETUP:
1. pip install -r requirements.txt
2. Set your bot token as an environment variable (do NOT hardcode it):
   export BOT_TOKEN="your-telegram-bot-token"
3. Run: python bot.py

Users are stored in users.json (chat IDs of everyone who has /start'd the bot).
Content is a curated local library per category, so it works instantly with
no external API dependency (fast and always available).
"""

import json
import logging
import os
import random
from pathlib import Path

import requests
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes_data.json"), "r", encoding="utf-8") as _f:
    QUOTE_LIBRARY = json.load(_f)

# ---------------------------------------------------------------------------
# Live quote API (ZenQuotes) -- supplements the local library with fresh,
# real, attributed quotes at runtime. The local library is the reliable
# base; this just adds variety on top and never breaks the bot if it fails.
# ---------------------------------------------------------------------------

ZENQUOTES_URL = "https://zenquotes.io/api/quotes"

CATEGORY_KEYWORDS = {
    "relationships": ["love", "friend", "together", "heart", "trust", "kindness"],
    "motivation": ["success", "dream", "never give up", "achieve", "goal", "effort", "persist"],
    "mindset": ["mind", "think", "belief", "perspective", "attitude", "wisdom"],
    "night": ["rest", "sleep", "peace", "calm", "quiet"],
    "advice": ["life", "wise", "truth", "character", "choice"],
    "feelings": ["feel", "emotion", "cry", "hurt", "sad", "lonely", "overwhelm", "grief"],
}
DEFAULT_CATEGORY = "today"


def categorize(quote_text: str) -> str:
    lower = quote_text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return cat
    return DEFAULT_CATEGORY


async def refresh_quotes_from_api(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch a fresh batch of real quotes and merge them into the in-memory
    library. Runs once shortly after startup, then every few hours. Any
    failure is logged and ignored -- the bot keeps working off the local
    library regardless."""
    try:
        response = requests.get(ZENQUOTES_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning("Live quote refresh failed, continuing with local library only: %s", e)
        return

    added = 0
    for entry in data:
        text = entry.get("q", "").strip()
        author = entry.get("a", "").strip()
        if not text or len(text) < 10:
            continue
        line = f"{text} — {author}" if author and author.lower() != "unknown" else text
        cat = categorize(text)
        items = CATEGORIES.get(cat, {}).get("items")
        if items is not None and line not in items:
            items.append(line)
            added += 1

    logger.info("Live quote refresh added %d new quotes across categories.", added)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable not set. "
        "Run: export BOT_TOKEN='your-token-here' before starting the bot."
    )

USERS_FILE = Path(__file__).parent / "users.json"

# Daily broadcast time, in UTC. 7:00 UTC = 8:00 AM in Nigeria (WAT, UTC+1).
DAILY_HOUR_UTC = 7
DAILY_MINUTE_UTC = 0

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Content library
# ---------------------------------------------------------------------------

CATEGORIES = {
    "today": {
        "label": "Today's Quote",
        "emoji": "💬",
        "items": [
            "The best time to plant a tree was 20 years ago. The second best time is now.",
            "You don't have to be great to start, but you have to start to be great.",
            "Difficult roads often lead to beautiful destinations.",
            "Small steps every day add up to big results.",
            "Your future is created by what you do today, not tomorrow.",
            "What lies behind you and what lies ahead matter less than what lies within you.",
            "Do what you can, with what you have, where you are.",
            "It always seems impossible until it's done.",
            "The only way to do great work is to love what you do.",
            "Turn your wounds into wisdom.",
        ],
    },
    "advice": {
        "label": "Life Advice",
        "emoji": "🌱",
        "items": [
            "Focus on progress, not perfection.",
            "Say no to things that don't align with your goals.",
            "Rest is productive too. Don't skip it.",
            "Write down your goals. It makes them real.",
            "Ask for help before you're overwhelmed, not after.",
            "Don't compare your chapter one to someone else's chapter twenty.",
            "Protect your peace like it's your job, because it is.",
            "You can't pour from an empty cup. Take care of yourself first.",
            "Slow progress is still progress. Keep going.",
            "Choose your battles. Not everything deserves your energy.",
        ],
    },
    "motivation": {
        "label": "Motivation",
        "emoji": "💪",
        "items": [
            "Push yourself, because no one else is going to do it for you.",
            "Great things never came from comfort zones.",
            "Dream it. Believe it. Build it.",
            "The pain of discipline weighs ounces, the pain of regret weighs tons.",
            "Success is the sum of small efforts repeated daily.",
            "You are capable of more than you know.",
            "Don't stop when you're tired. Stop when you're done.",
            "Every accomplishment starts with the decision to try.",
            "Discipline is choosing between what you want now and what you want most.",
            "Wake up with determination, go to bed with satisfaction.",
        ],
    },
    "relationships": {
        "label": "Relationships",
        "emoji": "❤️",
        "items": [
            "The best relationships are built on honesty, even when it's uncomfortable.",
            "Listen to understand, not just to reply.",
            "Show up for people consistently, not just when it's convenient.",
            "A good relationship gives you freedom, not control.",
            "Say what you mean, and mean what you say, kindly.",
            "The people who matter will always make time for you.",
            "Love grows where forgiveness lives.",
            "Healthy relationships take work from both sides, not just one.",
            "Be someone's safe place, not another source of stress.",
            "Real connection is built in the small, everyday moments.",
        ],
    },
    "mindset": {
        "label": "Mindset",
        "emoji": "🧠",
        "items": [
            "Your mindset shapes your reality more than your circumstances do.",
            "Whether you think you can or think you can't, you're right.",
            "A fixed mindset says 'I can't'. A growth mindset says 'not yet'.",
            "Change the way you look at things, and the things you look at change.",
            "Your thoughts become your words, your words become your actions.",
            "Replace 'I have to' with 'I get to'. It changes everything.",
            "The mind is everything. What you think, you become.",
            "Train your mind to see the good in every situation.",
            "You are not your thoughts. You are the one who notices them.",
            "Progress starts with believing change is possible.",
        ],
    },
    "night": {
        "label": "Night Reflection",
        "emoji": "🌙",
        "items": [
            "Today is done. Let it go, and rest well.",
            "You showed up today. That's enough.",
            "Not every day will be perfect, and that's okay.",
            "Reflect on one good thing that happened today before you sleep.",
            "Tomorrow is a fresh page. Tonight, just rest.",
            "Forgive yourself for today's mistakes. Growth isn't linear.",
            "Close the day with gratitude, not regret.",
            "You did your best with what you had today.",
            "Let go of what you can't control, and rest in what you can.",
            "Sleep well. You've earned it.",
        ],
    },
    "feelings": {
        "label": "Emotional Feelings",
        "emoji": "🫶",
        "items": [
            "It's okay to not be okay right now. You don't have to perform strength you don't feel.",
            "Whatever you're feeling is valid, even if you can't fully explain it yet.",
            "You are allowed to feel two opposite things at once, and still make sense.",
            "Crying isn't weakness. It's your body's way of releasing what words can't carry.",
            "You don't have to justify your feelings to anyone, including yourself.",
            "It's alright to need a moment before you're ready to talk about it.",
            "Numbness is sometimes just your mind protecting you until you're ready to feel it fully.",
            "You're not too sensitive. You just feel things deeply, and that's not a flaw.",
            "Some days the bravest thing you do is just keep breathing through it.",
            "You don't need to have the words for what you're feeling. It's still real.",
        ],
    },
}

# Merge the large auto-sourced quote library on top of the hand-picked lines above,
# so each category has hundreds of options instead of repeating quickly.
for _key, _extra in QUOTE_LIBRARY.items():
    if _key in CATEGORIES:
        CATEGORIES[_key]["items"].extend(_extra)

FALLBACK_TEXT = "Take a breath. You're doing better than you think."

HISTORY_FILE = Path(__file__).parent / "user_history.json"

def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_history(history: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(history))

# ---------------------------------------------------------------------------
# User storage (very simple JSON file; swap for a real DB if you scale up)
# ---------------------------------------------------------------------------

def load_users() -> set[int]:
    if USERS_FILE.exists():
        return set(json.loads(USERS_FILE.read_text()))
    return set()


def save_users(users: set[int]) -> None:
    USERS_FILE.write_text(json.dumps(list(users)))


# ---------------------------------------------------------------------------
# Content picker
# ---------------------------------------------------------------------------

def get_content(category_key: str, user_id: int | None = None) -> str:
    category = CATEGORIES.get(category_key)
    if not category:
        return FALLBACK_TEXT
    items = category["items"]
    if not items:
        return FALLBACK_TEXT
    if len(items) == 1 or user_id is None:
        text = items[0] if len(items) == 1 else random.choice(items)
        return f"{category['emoji']} {category['label']}\n\n{text}"

    # Per-user, per-category history: don't repeat a quote for this user
    # until they've seen every quote in the category, then reshuffle.
    history = load_history()
    user_key = str(user_id)
    seen = set(history.get(user_key, {}).get(category_key, []))

    unseen_indices = [i for i in range(len(items)) if i not in seen]
    if not unseen_indices:
        # They've seen everything in this category; start a fresh cycle.
        seen = set()
        unseen_indices = list(range(len(items)))

    index = random.choice(unseen_indices)
    seen.add(index)

    history.setdefault(user_key, {})[category_key] = list(seen)
    save_history(history)

    text = items[index]
    return f"{category['emoji']} {category['label']}\n\n{text}"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

ABOUT_TEXT = (
    "🌅 About LifeSpark ✨\n\n"
    "LifeSpark sends you daily quotes, honest life advice, and gentle reminders "
    "to help you stay grounded, motivated, and moving forward. Whether you need "
    "a spark of motivation, a moment of reflection, or just someone to say "
    "'what you're feeling is valid' — LifeSpark has a category for that.\n\n"
    "You'll get one quote automatically every morning, and you can pull more "
    "anytime using the commands or buttons below.\n\n"
)

COMMAND_LIST_TEXT = (
    "Commands:\n"
    "💬 /today - Today's Quote\n"
    "🌱 /advice - Life Advice\n"
    "💪 /motivation - Motivation\n"
    "❤️ /relationships - Relationships\n"
    "🧠 /mindset - Mindset\n"
    "🌙 /night - Night Reflection\n"
    "🫶 /feelings - Emotional Feelings\n"
    "🎲 /random - A surprise from any category\n"
    "❓ /help - Show what this bot does and this list again\n"
    "/stop - unsubscribe from daily messages\n\n"
    "Tip: you can also just tap a button below instead of typing a command."
)

ABOUT_TEXT = (
    "✨ About LifeSpark\n\n"
    "LifeSpark sends you a daily spark of quotes, advice, motivation, and gentle "
    "reflection across 7 categories, plus one automatic message every morning.\n\n"
    "🌍 Where the words come from\n"
    "Thousands of quotes and original reflections, including real, verified words "
    "from voices around the world such as:\n"
    "Herbert Macaulay, Nelson Mandela, Mahatma Gandhi, Martin Luther King Jr., "
    "Maya Angelou, Chinua Achebe, Wole Soyinka, Wangari Maathai, Desmond Tutu, "
    "Rabindranath Tagore, Rumi, Gabriel García Márquez, Frida Kahlo, Viktor Frankl, "
    "James Baldwin, Audre Lorde, Toni Morrison, C.S. Lewis, Malala Yousafzai, "
    "Brené Brown, Carol Dweck, Yuval Noah Harari, bell hooks, Albert Einstein, "
    "Winston Churchill, Confucius, Buddha, and many more, alongside original writing "
    "created for LifeSpark.\n\n"
    "🔁 No repeats\n"
    "Each quote won't repeat for you in a category until you've seen every quote in it.\n\n"
    f"{COMMAND_LIST_TEXT}"
)

# Maps the exact text shown on each menu button back to its category key,
# so tapping a button works exactly like typing the matching command.
BUTTON_LABELS = {
    "💬 Today's Quote": "today",
    "🌱 Life Advice": "advice",
    "💪 Motivation": "motivation",
    "❤️ Relationships": "relationships",
    "🧠 Mindset": "mindset",
    "🌙 Night Reflection": "night",
    "🫶 Emotional Feelings": "feelings",
    "🎲 Random": "__random__",
}

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💬 Today's Quote", "🌱 Life Advice"],
        ["💪 Motivation", "❤️ Relationships"],
        ["🧠 Mindset", "🌙 Night Reflection"],
        ["🫶 Emotional Feelings", "🎲 Random"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = load_users()
    users.add(update.effective_chat.id)
    save_users(users)
    await update.message.reply_text(
        ABOUT_TEXT + COMMAND_LIST_TEXT,
        reply_markup=MENU_KEYBOARD,
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = load_users()
    users.discard(update.effective_chat.id)
    save_users(users)
    await update.message.reply_text("You've been unsubscribed from daily messages. Send /start anytime to rejoin.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(ABOUT_TEXT, reply_markup=MENU_KEYBOARD)


async def random_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category_key = random.choice(list(CATEGORIES.keys()))
    await update.message.reply_text(get_content(category_key, update.effective_chat.id))


async def category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # context.chat_data / job stores which category via the command itself
    command = update.message.text.split()[0].lstrip("/").split("@")[0]
    await update.message.reply_text(get_content(command, update.effective_chat.id))


async def menu_button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category_key = BUTTON_LABELS.get(update.message.text)
    if category_key == "__random__":
        await random_cmd(update, context)
    elif category_key:
        await update.message.reply_text(get_content(category_key, update.effective_chat.id))


# ---------------------------------------------------------------------------
# Daily broadcast job
# ---------------------------------------------------------------------------

async def send_daily_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    users = load_users()
    if not users:
        logger.info("No subscribed users, skipping daily broadcast.")
        return

    logger.info("Sending daily broadcast to %d users", len(users))

    for chat_id in list(users):
        try:
            message = get_content("today", chat_id)
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            # If a user blocked the bot, remove them so we stop retrying
            logger.warning("Failed to message %s: %s", chat_id, e)
            users.discard(chat_id)

    save_users(users)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("random", random_cmd))
    for key in CATEGORIES:
        app.add_handler(CommandHandler(key, category_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_button_pressed))

    # Schedule the daily job
    from datetime import time as dtime

    app.job_queue.run_daily(
        send_daily_broadcast, time=dtime(hour=DAILY_HOUR_UTC, minute=DAILY_MINUTE_UTC)
    )

    # Refresh the live quote pool shortly after startup, then every 6 hours.
    app.job_queue.run_once(refresh_quotes_from_api, when=10)
    app.job_queue.run_repeating(refresh_quotes_from_api, interval=6 * 60 * 60, first=6 * 60 * 60)

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
