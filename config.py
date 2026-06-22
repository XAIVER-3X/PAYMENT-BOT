import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path("/app/data/vip_bot.db")
IMG_DIR = BASE_DIR

CONFIG_JSON_PATH = BASE_DIR / "config.json"

# Load config from json if exists
config_data = {}
if CONFIG_JSON_PATH.exists():
    try:
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")

# Base configurations
APPROVE_DB_PATH = os.getenv("APPROVE_DB_PATH", config_data.get("approve_db_path", "/root/approve_bot/access.db"))
BOT_TOKEN = os.getenv("BOT_TOKEN", config_data.get("bot_token", "8604871158:AAEcr6e1OWrhTctRI7RzojlyuH7650T0Q4w"))
OWNER_ID = int(os.getenv("OWNER_ID", str(config_data.get("owner_id", 8650066383))))
PREVIEW_CHANNEL_ID = int(os.getenv("PREVIEW_CHANNEL_ID", str(config_data.get("preview_channel_id", -1003893166247))))

MAX_KEY_ATTEMPTS = config_data.get("max_key_attempts", 3)
SUPPORT_COOLDOWN_SECONDS = config_data.get("support_cooldown_seconds", 600)

# Image paths
images_cfg = config_data.get("images", {})
IMG_WELCOME = IMG_DIR / images_cfg.get("welcome", "start_new.png")
IMG_MENU    = IMG_DIR / images_cfg.get("menu", "menu.jpg")
IMG_SUPPORT = IMG_DIR / images_cfg.get("support", "vip_support.jpg")
IMG_START   = IMG_DIR / images_cfg.get("start", "start_new.png")

# Payment links
PAY_LINKS = config_data.get("pay_links", {
    "120": "https://www.google.com/aclk?sa=L&ai=DChsSEwjdzde4mciUAxXIgFAGHQe3F_AYACICCAEQHhoCZGc&co=1&sph=&sig=AOD64_3U7cW25mIxdL6HeCX97bB3QzdqYg&ctype=5&q=&ved=2ahUKEwj5ic-4mciUAxWYXUEAHbLbNagQwg8oAHoECAsQDQ&adurl=",
    "80": "https://www.g2a.com/paypal-gift-card-80-gbp-by-rewarble-global-i10000339995119",
    "60": "https://www.google.com/aclk?sa=L&ai=DChsSEwin6vKJ4qKUAxWakVAGHSZKNhcYACICCAEQLRoCZGc&co=1&sph=&cce=1&sig=AOD64_3kMRL0hTctMtcqRV891k7hJcWb8Q&ctype=5&q=&ved=2ahUKEwjo6-2J4qKUAxVAXUEAHfbLHHkQwg8oAHoECAgQDQ&adurl=",
    "40": "https://www.google.com/aclk?sa=L&ai=DChsSEwigrvWb4qKUAxUpj1AGHZVgIdwYACICCAEQARoCZGc&co=1&sph=&cce=1&sig=AOD64_1mw8i45i3S8mQHj6QNJrfSwmFTtw&ctype=5&q=&ved=2ahUKEwid0vCb4qKUAxX5QEEAHbiJGvMQwg8oAHoECAkQDQ&adurl=",
    "30": "https://www.google.com/aclk?sa=L&ai=DChsSEwiU_NSl4qKUAxWLk1AGHXEHFgAYACICCAEQJRoCZGc&co=1&sph=&cce=1&sig=AOD64_3MZEkYKt0q3LzZ6-uyxqTrG4356Q&ctype=5&q=&ved=2ahUKEwjjsNCl4qKUAxU6QkEAHTS9JkQQwg8oAHoECAoQDQ&adurl=",
})

json_vip_tiers = config_data.get("vip_tiers", {})

GIRLS_ALL_LINK = PAY_LINKS.get("60", "")
GIRLS_SEPARATE_LINK = PAY_LINKS.get("30", "")

GIRLS_LIST = config_data.get("girls_list", [
    "26Hadjar", "AlishaM4", "Eshaa", "Fatima", "Haja",
    "Hiba", "Laiba Ali", "Leemz", "Lush", "Queen",
    "Rabaul", "Rakhee", "Reallarii", "Sajida", "Samira",
    "Sara Iqbal", "Shivani", "Simran", "Tamxbegumx", "Taqdees",
    "xneeca",
])

# Tiers details
VIP_TIERS = {}
TIER_EXPECTED_AMOUNT = {}
INVITE_LINKS = {}
TIER_IMAGES = {}

# Reconstruct dictionaries for backward compatibility
for key, tier in json_vip_tiers.items():
    price = tier.get("price", 0)
    VIP_TIERS[key] = {
        "label": tier.get("label", ""),
        "btn": tier.get("btn", ""),
        "link": tier.get("link") or PAY_LINKS.get(str(price), ""),
        "lines": [(line[0] if isinstance(line, (list, tuple)) and len(line) > 1 else "check_green",
                   line[1] if isinstance(line, (list, tuple)) and len(line) > 1 else (line if isinstance(line, str) else line[0] if isinstance(line, (list, tuple)) and len(line) > 0 else ""))
                  for line in tier.get("lines", [])],
        "days": tier.get("days", 30)
    }
    TIER_EXPECTED_AMOUNT[key] = price
    INVITE_LINKS[key] = tier.get("invite_link", "")
    TIER_IMAGES[key] = IMG_DIR / tier.get("image", "allgirls.jpg")

# Update girls list/separate links dynamically from updated config
if "allgirls_all" in VIP_TIERS:
    GIRLS_ALL_LINK = VIP_TIERS["allgirls_all"]["link"]
if "allgirls_separate" in VIP_TIERS:
    GIRLS_SEPARATE_LINK = VIP_TIERS["allgirls_separate"]["link"]

# Fallback defaults if json empty
if not VIP_TIERS:
    # Fallback to the original dictionary
    TIER_EXPECTED_AMOUNT = {
        "permanent":         120,
        "desiheaven":        80,
        "allgirls":          60,
        "desibaits":         40,
        "hoejabthots":       40,
        "whitechavs":        30,
        "allgirls_all":      60,
        "allgirls_separate": 30,
    }
    INVITE_LINKS = {
        "permanent":         "https://t.me/+fGxNx2Y2Bi0zOWY0",
        "desiheaven":        "https://t.me/+yG-4bLuLpH5hMGE0",
        "allgirls":          "https://t.me/+1jwoHurKHmU2MWE0",
        "desibaits":         "https://t.me/+fzkljt_eDF81MGRk",
        "hoejabthots":       "https://t.me/+-UPhQVJq030xMWY0",
        "whitechavs":        "https://t.me/+xpZixR3s3aY3NDFk",
        "allgirls_all":      "https://t.me/+1jwoHurKHmU2MWE0",
        "allgirls_separate": "https://t.me/m/Uk4mchTTOGJk",
    }
    TIER_IMAGES = {
        "desiheaven":   IMG_DIR / "desiheaven.jpg",
        "allgirls":     IMG_DIR / "allgirls.jpg",
        "desibaits":    IMG_DIR / "desibaits.jpg",
        "hoejabthots":  IMG_DIR / "hoejabthots.jpg",
        "whitechavs":   IMG_DIR / "ukchavs.png",
        "permanent":    IMG_DIR / "permanent.png",
    }
    VIP_TIERS = {
        "permanent": {
            "label":  "DH ELITE ( 16 GCs ) - £120",
            "btn":    "🚀 DH ELITE ( 16 GCs ) - £120",
            "link":   PAY_LINKS["120"],
            "lines": [
                ("check_green", "Full Admin Access ( Included )"),
                ("check_green", "All Premiums (16 GCs)"),
                ("check_green", "Future GCs Included"),
                ("new",         "Premium Group CHAT"),
                ("check_green", "DesiCave Inner Circle"),
                ("lock",        "Backup access — no loss"),
            ],
            "days":   30,
        },
        "desiheaven": {
            "label":  "DESIHEAVEN (13 VIP GCs) — £80",
            "btn":    "🏆 DESIHEAVEN (13 ViP GCs) — £80",
            "link":   PAY_LINKS["80"],
            "lines": [
                ("check_green", "Access to ALL VIPs & Girls"),
                ("check_green", "27,890+ Photos"),
                ("check_green", "230,856+ Videos"),
                ("new",         "Updated regularly"),
                ("check_green", "Save & keep everything"),
                ("lock",        "Backup access — no loss"),
            ],
            "days":   30,
        },
        "allgirls": {
            "label":  "ALL GIRLS (170+) — £60",
            "btn":    "💎 ALL GIRLS (170+) — £60",
            "link":   PAY_LINKS["60"],
            "lines": [
                ("check_green", "278+ Exclusive Girls"),
                ("check_green", "19,500+ Photos"),
                ("check_green", "57,500+ Videos"),
                ("lock",        "Exclusive content only"),
                ("new",         "Updated when new girls drop"),
                ("siren",       "Separate girls Available"),
            ],
            "days":   30,
        },
        "desibaits": {
            "label":  "DESI BAITS VIP — £40",
            "btn":    "🇧🇩🇮🇳🇵🇰 DESI BAITS VIP — £40",
            "link":   PAY_LINKS["40"],
            "lines": [
                ("check_green", "Largest DesiBaits collection"),
                ("check_green", "28,145+ Photos"),
                ("check_green", "86,952+ Videos"),
                ("new",         "Updated regularly"),
                ("lock",        "Save & keep everything"),
                ("check_green", "No recycled content"),
            ],
            "days":   30,
        },
        "hoejabthots": {
            "label":  "HoeJabThots — £40",
            "btn":    "🧕 HIJABI PREMIUM — £40",
            "link":   PAY_LINKS["40"],
            "lines": [
                ("uk",          "UK Hijabi Collection"),
                ("check_green", "Organised Premium"),
                ("new",         "Updated Regularly"),
                ("lock",        "Save & Keep Everything"),
                ("diamond",     "Unseen Content (No Reposts)"),
            ],
            "days":   30,
        },
        "whitechavs": {
            "label":  "UK CHAVS (ENTRY) — £30",
            "btn":    "🇬🇧 UK CHAVS (ENTRY) — £30",
            "link":   PAY_LINKS["30"],
            "lines": [
                ("uk",          "UK Chav collection"),
                ("check_green", "4,200+ Photos"),
                ("check_green", "11,800+ Videos"),
                ("new",         "Updated regularly"),
                ("lock",        "Save & keep everything"),
                ("check_green", "Backup access included"),
            ],
            "days":   30,
        },
        "allgirls_all": {
            "label":  "All Girls Full Package — £60",
            "btn":    "💠 All Girls Full — £60",
            "link":   PAY_LINKS["60"],
            "lines": [
                ("check_green", "All 21+ Girls"),
                ("check_green", "Every VIP Folder"),
                ("new",         "Daily updates"),
            ],
            "days":   30,
        },
        "allgirls_separate": {
            "label":  "Single Girl VIP — £30",
            "btn":    "👤 Single Girl VIP — £30",
            "link":   GIRLS_SEPARATE_LINK,
            "lines": [
                ("check_green", "Your selected girl's VIP folder"),
                ("check_green", "Full content access"),
            ],
            "days":   30,
        },
    }

EMOJI_JSON_PATH = BASE_DIR / "emoji.json"
CUSTOM_EMOJI = {}
if EMOJI_JSON_PATH.exists():
    try:
        with open(EMOJI_JSON_PATH, "r", encoding="utf-8") as f:
            CUSTOM_EMOJI = json.load(f)
    except Exception as e:
        print(f"Error loading emoji.json: {e}")

default_emojis = {
    "adult":           ("5348485489097717994", "🔞"),
    "check":           ("5913315955294868588", "☑️"),
    "check_green":     ("5206607081334906820", "✔️"),
    "pound":           ("5290017777174722330", "💷"),
    "card":            ("6129870117619634982", "💳"),
    "new":             ("6269421275878265370", "🆕"),
    "lock":            ("5348223165380179822", "🔒"),
    "siren":           ("6257780484281997093", "🚨"),
    "uz":              ("5449829434334912605", "🇺🇿"),
    "recycle":         ("5274156304036800055", "🔵"),
    "uk":              ("5202196682497859879", "🇬🇧"),
    "diamond":         ("5427168083074628963", "💎"),
    "warn":            ("4958534696645428119", "‼️"),
    "box_dot":   ("5913344229064577598", "☑️"),
    "users_i":   ("5350778980158956492", "👥"),
    "money_i":   ("6001434068435079689", "💰"),
    "pkg_i":     ("6030474915008745842", "📦"),
    "trophy_i":  ("5458612419116933783", "🏆"),
    "trend_i":   ("5244837092042750681", "📈"),
    "id_i":      ("6323600780783781848", "🆔"),
    "msg_i":     ("5472239203590888751", "📩"),
    "online":    ("5215670591905869044", "🟢"),
    "bell":      ("5451927229506268442", "🔔"),
    "star":      ("5368324170671202286", "⭐"),
    "link":      ("5440539497383087970", "🔗"),
    "gift":      ("5445284737759586608", "🎁"),
    "broadcast": ("5472164874456408254", "📢"),
    "admin":     ("5215561933736808510", "🔧"),
    "profile":   ("5372981976804366741", "👤"),
    "channel":   ("5361541234971020219", "📡"),
    "error":     ("5382173019027638596", "🚨"),
    "money":     ("5445284737759586608", "💰"),
    "stats":     ("5379748062124056162", "📊"),
    "crown":     ("5217822164362739968", "👑"),
    "fire":      ("5472423702501006989", "🔥"),
    "ticket":    ("5418010521309815154", "🎫"),
    "pencil":    ("5395444784611480792", "✏️"),
    "globe":     ("5395558210402807000", "🌐"),
}

for k, v in default_emojis.items():
    if k not in CUSTOM_EMOJI:
        CUSTOM_EMOJI[k] = v

STICKER_IDS = {
    "welcome": "",
    "verified": "",
}

BOT_USERNAME = config_data.get("bot_username", "DurkViPBOT")

# ─── USER-FACING BUTTON LABELS & NAVIGATION ───────────────────────────────────
BTN_LIVE_CHAT = "💬  LIVE CHAT"
BTN_PROFILE = "👤  PROFILE"
BTN_SUPPORT = "🎫  SUPPORT"
BTN_VIP_STATUS = "👑  VIP STATUS"
BTN_CHANNEL = "📡  CHANNEL"
BTN_CONTACT_SUPPORT = "🧑  Contact Support"
BTN_PAY_NOW = "💳  Pay Now"
BTN_IVE_PAID = "✅  I've Paid — Verify"
BTN_SHOW_SEPARATE = "👑  Show Separate Options"
BTN_BACK = "◂  Back"
BTN_BACK_TO_PLANS = "◂  Back to Plans"
BTN_BUY_SEPARATE = "🛍️  Buy Separate — £25"
BTN_BUY_ALL = "💠  Buy All — £50"
BTN_REDEEM_COMMISSION = "🎁  Redeem Commission"
BTN_TOP_REFERRERS = "🏆  Top Referrers"
BTN_CLOSE_CHAT = "🔒  Close Chat"
BTN_CLOSE_SESSION = "🔒  Close Session"
BTN_CANCEL = "✖  Cancel"
BTN_ACCEPT = "✅  Accept"
BTN_REJECT = "❌  Reject"
BTN_REPLY = "💬  Reply"
BTN_CLOSE = "🔒  Close"
BTN_STATS = "📊  STATS"
BTN_ANALYTICS = "📈  ANALYTICS"
BTN_PAID_USERS = "💰  PAID USERS"
BTN_LEADERBOARD = "🏆  LEADERBOARD"
BTN_BLOCK_USER = "🚫  BLOCK USER"
BTN_UNBLOCK_USER = "✅  UNBLOCK USER"
BTN_OPEN_TICKETS = "🎫  OPEN TICKETS"
BTN_GIVE_VIP = "🎁  GIVE VIP"
BTN_MANAGE_USERS = "👥  MANAGE USERS"
BTN_BROADCAST = "📢  BROADCAST"
BTN_SET_CHANNELS = "📡  SET CHANNELS"
BTN_REPLY_SUPPORT = "💬  REPLY SUPPORT"
BTN_PREV = " ◀  Prev "
BTN_NEXT = " Next  ▶ "
BTN_ADMIN_PANEL = " ◂  Admin Panel "

# ─── CUSTOMIZABLE TEXT TEMPLATES ──────────────────────────────────────────────
MSG_PLAN_LIST_HEADER = "DESI VIP ACCESS"
MSG_PLAN_LIST_FEATURES = [
    "Instant Premium Access",
    "Fresh Content Added Daily",
    "Save & Keep Everything",
    "Backup Access Included",
    "Premium Support"
]
MSG_PLAN_LIST_FOOTER = "Choose Your Plan ↓"

MSG_CODE_PROMPT_TITLE = "Almost there!"
MSG_CODE_PROMPT_BODY = "Send your Rewarble voucher code to verify payment."
MSG_CODE_PROMPT_FOOTER = "Your code is verified securely and instantly."

MSG_SUPPORT_SUBJECT_TITLE = "VIP SUPPORT"
MSG_SUPPORT_SUBJECT_STEP = "Step 1 of 2 — Subject"
MSG_SUPPORT_SUBJECT_QUESTION = "What is your issue about?"
MSG_SUPPORT_SUBJECT_EXAMPLE = "e.g. Payment problem, Access issue"
MSG_SUPPORT_SUBJECT_CANCEL = "Press Back to cancel."

MSG_SUPPORT_BLOCKED_TITLE = "VIP SUPPORT"
MSG_SUPPORT_BLOCKED_STEP = "Describe your issue:"
MSG_SUPPORT_BLOCKED_HELP = "Write your problem in full detail — we will reply as soon as possible."
MSG_SUPPORT_BLOCKED_CANCEL = "Press Back to cancel."

MSG_PAYMENT_SUCCESS_TITLE = "PAYMENT VERIFIED"
MSG_PAYMENT_SUCCESS_WELCOME = "Welcome to VIP — you're in!"
MSG_PAYMENT_SUCCESS_ACTIVE = "Access active for"
MSG_PAYMENT_SUCCESS_VOUCHER = "Voucher Details"

MSG_MYSTATUS_TITLE = "VIP STATUS"
MSG_MYSTATUS_ACTIVE = "Active"
MSG_MYSTATUS_EXPIRES = "Expires:"
MSG_MYSTATUS_JOIN = "Join Private Group →"
MSG_MYSTATUS_NOT_VIP = "Not a VIP member"
MSG_MYSTATUS_NOT_VIP_HELP = "Tap /start to browse plans and purchase."

MSG_ADMIN_TITLE = "ADMIN PANEL"
MSG_ADMIN_WELCOME = "Welcome,"
MSG_ADMIN_TOTAL_USERS = "Total Users"
MSG_ADMIN_VIP_MEMBERS = "VIP Members"
MSG_ADMIN_PENDING_PAY = "Pending Pay."
MSG_ADMIN_OPEN_TICKETS = "Open Tickets"
MSG_ADMIN_SELECT_ACTION = "Select an action ↓"

MSG_ACCOUNT_RESTRICTED_HEADER = "━━━━ ACCOUNT RESTRICTED ━━━━"
MSG_ACCOUNT_RESTRICTED_BODY = "Your account has been flagged due to too many invalid key submissions.\n\n📩 Contact support below to resolve this."
MSG_SESSION_CANCELLED = "⚠️ Session cancelled. Use /start to start over."
MSG_VERIFY_TEXT_ONLY = "❌ Please send your voucher code as a text message."



