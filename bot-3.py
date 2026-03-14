import os, random, sqlite3, logging, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "8586390943:AAFuVy8pX73HPsT2AZPP7e5pVCDnJqPsk38"
WEBAPP_URL = "https://eclectic-smakager-6dd44a.netlify.app"
ADMIN_ID = 7928994076

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUESTIONS = [
    {"c":"personnages","q":"Qui possède le pouvoir 'One For All' ?","o":["Bakugo","Izuku Midoriya","Todoroki","Iida"],"a":1,"anime":"MHA","d":"facile"},
    {"c":"personnages","q":"Maître de Naruto Uzumaki ?","o":["Iruka","Kakashi","Jiraiya","Minato"],"a":1,"anime":"Naruto","d":"facile"},
    {"c":"personnages","q":"Qui a mangé le Gomu Gomu no Mi ?","o":["Zoro","Sanji","Luffy","Ace"],"a":2,"anime":"One Piece","d":"facile"},
    {"c":"personnages","q":"Vrai nom de L dans Death Note ?","o":["Nate River","Mihael Keehl","Lawliet","Beyond Birthday"],"a":2,"anime":"Death Note","d":"difficile"},
    {"c":"personnages","q":"Démon lié à Denji dans Chainsaw Man ?","o":["Devil Sang","Pochita","Makima","Power"],"a":1,"anime":"Chainsaw Man","d":"facile"},
    {"c":"pouvoirs","q":"Technique de Naruto qui crée des clones ?","o":["Rasengan","Kage Bunshin","Chidori","Substitution"],"a":1,"anime":"Naruto","d":"facile"},
    {"c":"pouvoirs","q":"Pouvoir de Gojo Satoru ?","o":["Malédiction","Technique Limitrophe","Six Yeux","Domaine"],"a":1,"anime":"JJK","d":"moyen"},
    {"c":"pouvoirs","q":"Fruit du démon de Trafalgar Law ?","o":["Ope Ope no Mi","Nagi Nagi","Bara Bara","Mero Mero"],"a":0,"anime":"One Piece","d":"difficile"},
    {"c":"pouvoirs","q":"Énergie vitale des Hunters dans HxH ?","o":["Chakra","Reiatsu","Nen","Haki"],"a":2,"anime":"HxH","d":"moyen"},
    {"c":"isekai","q":"Pouvoir de Subaru dans Re:Zero ?","o":["Magie du temps","Retour par la mort","Immortalité","Vision"],"a":1,"anime":"Re:Zero","d":"facile"},
    {"c":"isekai","q":"Déesse avec Kazuma dans KonoSuba ?","o":["Eris","Aqua","Darkness","Megumin"],"a":1,"anime":"KonoSuba","d":"facile"},
    {"c":"isekai","q":"Vrai nom de Rimuru dans Tensura ?","o":["Taro Yamada","Satoru Mikami","Kazuma Sato","Naofumi"],"a":1,"anime":"Tensura","d":"moyen"},
    {"c":"isekai","q":"Duo frère/soeur dans No Game No Life ?","o":["Sora & Shiro","Kirito & Asuna","Kazuma & Aqua","Subaru & Emilia"],"a":0,"anime":"NGNL","d":"moyen"},
    {"c":"devinette","q":"Carnet qui tue quiconque dont on écrit le nom ?","o":["Code Geass","Death Note","Mirai Nikki","Talentless"],"a":1,"anime":"Death Note","d":"facile"},
    {"c":"devinette","q":"Humains derrière des murs contre des créatures dévorantes ?","o":["Kabaneri","Terra Formars","Attack on Titan","God Eater"],"a":2,"anime":"AoT","d":"facile"},
    {"c":"opening","q":"Opening Gurenge par LiSA ?","o":["JJK","Demon Slayer","SAO","Bleach"],"a":1,"anime":"Demon Slayer","d":"facile"},
    {"c":"opening","q":"Guren no Yumiya par Linked Horizon ?","o":["Kabaneri","Re:Zero","Attack on Titan","Overlord"],"a":2,"anime":"AoT","d":"facile"},
    {"c":"opening","q":"Hikaru Nara de Goose House ?","o":["Toradora","Your Lie in April","Clannad","Anohana"],"a":1,"anime":"Your Lie in April","d":"moyen"},
]

PTS = {"facile":10,"moyen":20,"difficile":30}

def init_db():
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS scores (user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, best_score INTEGER DEFAULT 0, games INTEGER DEFAULT 0, correct INTEGER DEFAULT 0, total INTEGER DEFAULT 0, banned INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS clans (tag TEXT PRIMARY KEY, name TEXT, chief_id INTEGER, score INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS members (user_id INTEGER PRIMARY KEY, clan_tag TEXT, role TEXT, contrib INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS duels (code TEXT PRIMARY KEY, p1_id INTEGER, p1_name TEXT, p2_id INTEGER, p2_name TEXT, score1 INTEGER, score2 INTEGER, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, q TEXT, o1 TEXT, o2 TEXT, o3 TEXT, o4 TEXT, answer INTEGER, anime TEXT, diff TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, pseudo TEXT, avatar TEXT, notif INTEGER DEFAULT 1, profile_public INTEGER DEFAULT 1)")
    conn.commit(); conn.close()

def db():
    return sqlite3.connect("quiz.db")

def is_banned(uid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT banned FROM scores WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    return row and row[0] == 1

def get_setting(uid, key, default=None):
    conn = db(); c = conn.cursor()
    c.execute(f"SELECT {key} FROM settings WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    return row[0] if row else default

def save_score(uid, name, username, score, correct, total):
    conn = db(); c = conn.cursor()
    c.execute("SELECT best_score FROM scores WHERE user_id=?", (uid,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE scores SET name=?, username=?, best_score=?, games=games+1, correct=correct+?, total=total+? WHERE user_id=?", (name, username, max(row[0],score), correct, total, uid))
    else:
        c.execute("INSERT INTO scores VALUES (?,?,?,?,?,?,?,?)", (uid,name,username,score,1,correct,total,0))
    c.execute("SELECT clan_tag FROM members WHERE user_id=?", (uid,))
    m = c.fetchone()
    if m:
        c.execute("UPDATE members SET contrib=contrib+? WHERE user_id=?", (score,uid))
        c.execute("UPDATE clans SET score=score+? WHERE tag=?", (score,m[0]))
    conn.commit(); conn.close()

def get_rank_pos(uid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*)+1 FROM scores WHERE best_score>(SELECT COALESCE(best_score,0) FROM scores WHERE user_id=?) AND banned=0",(uid,))
    pos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM scores WHERE banned=0")
    total = c.fetchone()[0]
    conn.close(); return pos, total

def get_top(limit=10):
    conn = db(); c = conn.cursor()
    c.execute("SELECT name, best_score FROM scores WHERE banned=0 ORDER BY best_score DESC LIMIT ?", (limit,))
    rows = c.fetchall(); conn.close(); return rows

def get_top_clans(limit=10):
    conn = db(); c = conn.cursor()
    c.execute("SELECT tag, name, score FROM clans ORDER BY score DESC LIMIT ?", (limit,))
    rows = c.fetchall(); conn.close(); return rows

def get_my_clan(uid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT cl.tag, cl.name, cl.score, cm.role, cm.contrib FROM members cm JOIN clans cl ON cm.clan_tag=cl.tag WHERE cm.user_id=?", (uid,))
    row = c.fetchone(); conn.close(); return row

def get_clan_members(tag):
    conn = db(); c = conn.cursor()
    c.execute("SELECT s.name, m.role, m.contrib FROM members m LEFT JOIN scores s ON m.user_id=s.user_id WHERE m.clan_tag=?", (tag,))
    rows = c.fetchall(); conn.close(); return rows

def home_kb(uid):
    kb = [
        [InlineKeyboardButton("🎮 Ouvrir l'Arena", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("🎯 Quiz Rapide", callback_data="quiz"), InlineKeyboardButton("🏆 Top", callback_data="top")],
        [InlineKeyboardButton("⚔️ Duel", callback_data="duel"), InlineKeyboardButton("🏰 Clan", callback_data="clan")],
        [InlineKeyboardButton("👤 Profil", callback_data="profil"), InlineKeyboardButton("⚙️ Réglages", callback_data="settings")],
    ]
    if uid == ADMIN_ID:
        kb.append([InlineKeyboardButton("🔧 ADMIN PANEL", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

async def check_ban(update: Update):
    uid = update.effective_user.id
    if is_banned(uid):
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if msg: await msg.reply_text("🚫 Tu as été banni du bot.")
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    u = update.effective_user
    conn = db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO settings VALUES (?,?,?,?,?)", (u.id, u.first_name, "🎌", 1, 1))
    conn.commit(); conn.close()
    pseudo = get_setting(u.id, "pseudo") or u.first_name
    avatar = get_setting(u.id, "avatar") or "🎌"
    await update.message.reply_text(
        f"Yo {avatar} *{pseudo}* ! 🎌\n\n*Anime Quiz Arena* est là !\n\n⚡ Chrono • ⚔️ Duels • 🏰 Clans • 🏆 Classement\n\nOuvre l'Arena ou joue directement ici 👇",
        parse_mode="Markdown", reply_markup=home_kb(u.id)
    )

async def go_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = update.effective_user
    pseudo = get_setting(u.id, "pseudo") or u.first_name
    avatar = get_setting(u.id, "avatar") or "🎌"
    await q.edit_message_text(
        f"{avatar} *{pseudo}* | Anime Quiz Arena\nQue veux-tu faire ?",
        parse_mode="Markdown", reply_markup=home_kb(u.id)
    )

# ═══ QUIZ ═══
async def quiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Tout mélanger", callback_data="cat_all")],
        [InlineKeyboardButton("🧑‍🎤 Personnages", callback_data="cat_personnages"), InlineKeyboardButton("⚡ Pouvoirs", callback_data="cat_pouvoirs")],
        [InlineKeyboardButton("🌀 Isekai", callback_data="cat_isekai"), InlineKeyboardButton("🎯 Devinettes", callback_data="cat_devinette")],
        [InlineKeyboardButton("🎵 Openings", callback_data="cat_opening"), InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text("📂 *Choisis une catégorie :*", parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text("📂 *Choisis une catégorie :*", parse_mode="Markdown", reply_markup=kb)

async def start_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cat = q.data.replace("cat_","")
    pool = QUESTIONS if cat=="all" else [x for x in QUESTIONS if x["c"]==cat]
    if not pool: await q.edit_message_text("❌ Aucune question dans cette catégorie !"); return
    selected = random.sample(pool, min(5, len(pool)))
    context.user_data.update({"queue":selected,"score":0,"correct":0,"total":0})
    await send_q(update, context)

async def send_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    queue = context.user_data.get("queue",[])
    if not queue: await end_quiz(update, context); return
    q = queue[0]; context.user_data["queue"] = queue[1:]; context.user_data["cur"] = q
    num = context.user_data.get("total",0)+1
    diff_e = {"facile":"🟢","moyen":"🟡","difficile":"🔴"}.get(q["d"],"⚪")
    text = f"{diff_e} Q{num} | 🎬 _{q['anime']}_\n\n❓ *{q['q']}*"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{chr(65+i)}. {o}", callback_data=f"a_{i}")] for i,o in enumerate(q["o"])])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    idx = int(q.data.split("_")[1])
    cur = context.user_data.get("cur")
    if not cur: await q.edit_message_text("❌ Tape /quiz pour recommencer."); return
    ok = idx == cur["a"]
    pts = PTS.get(cur["d"],10) if ok else 0
    context.user_data["score"] = context.user_data.get("score",0)+pts
    context.user_data["total"] = context.user_data.get("total",0)+1
    if ok: context.user_data["correct"] = context.user_data.get("correct",0)+1
    res = "✅ *CORRECT !*" if ok else f"❌ *FAUX !*\n✅ {cur['o'][cur['a']]}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Suivant", callback_data="next")]])
    await q.edit_message_text(f"{res}{' (+'+str(pts)+' pts)' if ok else ''}\n\n📊 Score : *{context.user_data['score']} pts*", parse_mode="Markdown", reply_markup=kb)

async def next_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await send_q(update, context)

async def end_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    score = context.user_data.get("score",0)
    correct = context.user_data.get("correct",0)
    total = context.user_data.get("total",0)
    pct = int((correct/total)*100) if total>0 else 0
    save_score(u.id, u.first_name, u.username or "", score, correct, total)
    pos, totalp = get_rank_pos(u.id)
    rank = "👑 Otaku God" if pct==100 else "⚡ Otaku Elite" if pct>=80 else "🎌 Vrai Weeb" if pct>=60 else "📺 Casual Viewer" if pct>=40 else "🌀 Débutant"
    text = f"🏆 *Quiz terminé !*\n\n✅ {correct}/{total} ({pct}%)\n🏆 Score : *{score} pts*\n🎖️ {rank}\n🌍 Rang : *#{pos}* / {totalp}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Rejouer", callback_data="quiz"), InlineKeyboardButton("🏠 Accueil", callback_data="home")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ═══ TOP ═══
async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    rows = get_top(10)
    medals = ["🥇","🥈","🥉"]+["▪️"]*7
    text = "🏆 *CLASSEMENT MONDIAL*\n\n"
    for i,(name,score) in enumerate(rows): text += f"{medals[i]} *{i+1}.* {name} — *{score} pts*\n"
    if not rows: text += "_Aucun score encore !_"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏰 Top Clans", callback_data="clantop"), InlineKeyboardButton("🏠 Accueil", callback_data="home")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ═══ PROFIL ═══
async def profil_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    u = update.effective_user
    conn = db(); c = conn.cursor()
    c.execute("SELECT best_score, games, correct, total FROM scores WHERE user_id=?", (u.id,))
    row = c.fetchone(); conn.close()
    clan = get_my_clan(u.id)
    pos, totalp = get_rank_pos(u.id)
    pseudo = get_setting(u.id, "pseudo") or u.first_name
    avatar = get_setting(u.id, "avatar") or "🎌"
    if not row:
        text = f"{avatar} *{pseudo}*\n\n_Pas encore joué ! Lance un quiz_ 🎯"
    else:
        pct = int((row[2]/row[3])*100) if row[3]>0 else 0
        rank = "👑 Otaku God" if pct==100 else "⚡ Otaku Elite" if pct>=80 else "🎌 Vrai Weeb" if pct>=60 else "📺 Casual Viewer" if pct>=40 else "🌀 Débutant"
        clan_txt = f"🏰 [{clan[0]}] {clan[1]}" if clan else "🏰 Pas de clan"
        text = f"{avatar} *{pseudo}*\n🎖️ {rank}\n🌍 #{pos} / {totalp}\n\n🏆 Meilleur : *{row[0]} pts*\n🎮 Parties : {row[1]}\n✅ Réussite : {pct}%\n{clan_txt}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Jouer", callback_data="quiz"), InlineKeyboardButton("⚙️ Réglages", callback_data="settings")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ═══ RÉGLAGES JOUEUR ═══
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    u = update.effective_user
    pseudo = get_setting(u.id, "pseudo") or u.first_name
    avatar = get_setting(u.id, "avatar") or "🎌"
    notif = get_setting(u.id, "notif", 1)
    public = get_setting(u.id, "profile_public", 1)
    text = (
        f"⚙️ *Réglages de {avatar} {pseudo}*\n\n"
        f"👤 Pseudo : *{pseudo}*\n"
        f"🎨 Avatar : *{avatar}*\n"
        f"🔔 Notifications : *{'ON' if notif else 'OFF'}*\n"
        f"🌍 Profil public : *{'OUI' if public else 'NON'}*"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Changer pseudo", callback_data="set_pseudo"),
         InlineKeyboardButton("🎨 Changer avatar", callback_data="set_avatar")],
        [InlineKeyboardButton(f"🔔 Notifs {'ON' if notif else 'OFF'}", callback_data="set_notif"),
         InlineKeyboardButton(f"🌍 Profil {'Public' if public else 'Privé'}", callback_data="set_public")],
        [InlineKeyboardButton("🗑️ Reset mon score", callback_data="set_reset")],
        [InlineKeyboardButton("🏰 Gérer mon clan", callback_data="clan_manage"),
         InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def set_pseudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["waiting"] = "pseudo"
    await q.edit_message_text("✏️ Envoie ton nouveau pseudo :")

async def set_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    avatars = ["🎌","⚔️","🌀","🔥","⚡","👁️","🗡️","🧿","🏮","🎭","🦊","🐉","💀","🌑","🏯"]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(a, callback_data=f"av_{a}")] for a in avatars] + [[InlineKeyboardButton("⬅️ Retour", callback_data="settings")]])
    await q.edit_message_text("🎨 Choisis ton avatar :", reply_markup=kb)

async def pick_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    av = q.data.replace("av_","")
    conn = db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO settings VALUES (?,?,?,?,?)", (q.from_user.id, q.from_user.first_name, av, 1, 1))
    c.execute("UPDATE settings SET avatar=? WHERE user_id=?", (av, q.from_user.id))
    conn.commit(); conn.close()
    await q.edit_message_text(f"✅ Avatar changé pour {av} !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Réglages", callback_data="settings")]]))

async def set_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    notif = get_setting(uid, "notif", 1)
    conn = db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO settings VALUES (?,?,?,?,?)", (uid, q.from_user.first_name, "🎌", 1, 1))
    c.execute("UPDATE settings SET notif=? WHERE user_id=?", (0 if notif else 1, uid))
    conn.commit(); conn.close()
    await q.edit_message_text(f"🔔 Notifications {'activées' if not notif else 'désactivées'} !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Réglages", callback_data="settings")]]))

async def set_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    pub = get_setting(uid, "profile_public", 1)
    conn = db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO settings VALUES (?,?,?,?,?)", (uid, q.from_user.first_name, "🎌", 1, 1))
    c.execute("UPDATE settings SET profile_public=? WHERE user_id=?", (0 if pub else 1, uid))
    conn.commit(); conn.close()
    await q.edit_message_text(f"🌍 Profil {'privé' if pub else 'public'} !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Réglages", callback_data="settings")]]))

async def set_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmer le reset", callback_data="confirm_reset"),
         InlineKeyboardButton("❌ Annuler", callback_data="settings")],
    ])
    await q.edit_message_text("⚠️ *Tu veux vraiment réinitialiser ton score ?*\nCette action est irréversible !", parse_mode="Markdown", reply_markup=kb)

async def confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    conn = db(); c = conn.cursor()
    c.execute("UPDATE scores SET best_score=0, games=0, correct=0, total=0 WHERE user_id=?", (uid,))
    conn.commit(); conn.close()
    await q.edit_message_text("✅ Score réinitialisé !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data="home")]]))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    waiting = context.user_data.get("waiting")
    if waiting == "pseudo":
        pseudo = update.message.text.strip()[:20]
        uid = update.effective_user.id
        conn = db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO settings VALUES (?,?,?,?,?)", (uid, pseudo, "🎌", 1, 1))
        c.execute("UPDATE settings SET pseudo=? WHERE user_id=?", (pseudo, uid))
        conn.commit(); conn.close()
        context.user_data["waiting"] = None
        await update.message.reply_text(f"✅ Pseudo changé pour *{pseudo}* !", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Réglages", callback_data="settings")]]))
    elif waiting == "admin_broadcast":
        msg = update.message.text.strip()
        conn = db(); c = conn.cursor()
        c.execute("SELECT user_id FROM scores")
        users = c.fetchall(); conn.close()
        sent = 0
        for (uid,) in users:
            try:
                await context.bot.send_message(uid, f"📢 *Message de l'admin :*\n\n{msg}", parse_mode="Markdown")
                sent += 1
            except: pass
        context.user_data["waiting"] = None
        await update.message.reply_text(f"✅ Message envoyé à {sent} joueurs !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔧 Admin", callback_data="admin")]]))
    elif waiting == "admin_add_q":
        try:
            parts = update.message.text.strip().split("|")
            cat, q_text, o1, o2, o3, o4, ans, anime, diff = [p.strip() for p in parts]
            conn = db(); c = conn.cursor()
            c.execute("INSERT INTO questions VALUES (NULL,?,?,?,?,?,?,?,?,?)", (cat,q_text,o1,o2,o3,o4,int(ans),anime,diff))
            conn.commit(); conn.close()
            QUESTIONS.append({"c":cat,"q":q_text,"o":[o1,o2,o3,o4],"a":int(ans),"anime":anime,"d":diff})
            context.user_data["waiting"] = None
            await update.message.reply_text("✅ Question ajoutée !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔧 Admin", callback_data="admin")]]))
        except:
            await update.message.reply_text("❌ Format incorrect !\nFormat : cat|question|opt1|opt2|opt3|opt4|réponse(0-3)|anime|difficulté")
    elif waiting == "admin_ban":
        try:
            uid = int(update.message.text.strip())
            conn = db(); c = conn.cursor()
            c.execute("UPDATE scores SET banned=1 WHERE user_id=?", (uid,))
            conn.commit(); conn.close()
            context.user_data["waiting"] = None
            await update.message.reply_text(f"✅ Joueur {uid} banni !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔧 Admin", callback_data="admin")]]))
        except:
            await update.message.reply_text("❌ ID invalide !")

# ═══ CLAN ═══
async def clan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    u = update.effective_user
    clan = get_my_clan(u.id)
    if not clan:
        text = "🏰 *CLANS*\n\nRejoins ou crée un clan !\n\n▪️ /creerCLAN TAG NOM\n▪️ /rejoindre TAG"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏆 Top Clans", callback_data="clantop"), InlineKeyboardButton("🏠 Accueil", callback_data="home")]])
    else:
        members = get_clan_members(clan[0])
        role_txt = "👑 Chef" if clan[3]=="chief" else "⚔️ Membre"
        text = f"🏰 *[{clan[0]}] {clan[1]}*\n\n🏆 Score : {clan[2]} pts\n👥 Membres : {len(members)}\n🎖️ Rôle : {role_txt}\n💪 Ta contrib : {clan[4]} pts"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Voir membres", callback_data="clan_members"),
             InlineKeyboardButton("🏆 Top Clans", callback_data="clantop")],
            [InlineKeyboardButton("⚙️ Gérer clan", callback_data="clan_manage"),
             InlineKeyboardButton("🏠 Accueil", callback_data="home")],
        ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def clan_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = update.effective_user
    clan = get_my_clan(u.id)
    if not clan: await q.edit_message_text("❌ T'es pas dans un clan !"); return
    members = get_clan_members(clan[0])
    text = f"👥 *Membres de [{clan[0]}] {clan[1]}*\n\n"
    for i,(name,role,contrib) in enumerate(members):
        icon = "👑" if role=="chief" else "⚔️"
        text += f"{icon} {name or '?'} — {contrib} pts\n"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="clan")]])
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

async def clan_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = update.effective_user
    clan = get_my_clan(u.id)
    if not clan: await q.edit_message_text("❌ T'es pas dans un clan !"); return
    is_chief = clan[3] == "chief"
    kb_rows = []
    if is_chief:
        kb_rows.append([InlineKeyboardButton("✏️ Renommer le clan", callback_data="clan_rename")])
        kb_rows.append([InlineKeyboardButton("🚪 Kicker un membre", callback_data="clan_kick")])
        kb_rows.append([InlineKeyboardButton("💥 Dissoudre le clan", callback_data="clan_dissolve")])
    kb_rows.append([InlineKeyboardButton("🚶 Quitter le clan", callback_data="clan_leave")])
    kb_rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="clan")])
    text = f"⚙️ *Gestion de [{clan[0]}] {clan[1]}*\n\nTon rôle : {'👑 Chef' if is_chief else '⚔️ Membre'}"
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb_rows))

async def clan_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = update.effective_user
    conn = db(); c = conn.cursor()
    c.execute("DELETE FROM members WHERE user_id=?", (u.id,))
    conn.commit(); conn.close()
    await q.edit_message_text("✅ T'as quitté le clan !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data="home")]]))

async def clan_dissolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = update.effective_user
    clan = get_my_clan(u.id)
    if not clan or clan[3] != "chief": await q.answer("❌ T'es pas le chef !"); return
    conn = db(); c = conn.cursor()
    c.execute("DELETE FROM members WHERE clan_tag=?", (clan[0],))
    c.execute("DELETE FROM clans WHERE tag=?", (clan[0],))
    conn.commit(); conn.close()
    await q.edit_message_text("💥 Clan dissous !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data="home")]]))

async def clantop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    rows = get_top_clans(10)
    medals = ["🥇","🥈","🥉"]+["▪️"]*7
    text = "🏰 *TOP CLANS*\n\n"
    for i,(tag,name,score) in enumerate(rows): text += f"{medals[i]} *{i+1}.* [{tag}] {name} — *{score} pts*\n"
    if not rows: text += "_Aucun clan encore !_"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Joueurs", callback_data="top"), InlineKeyboardButton("🏠 Accueil", callback_data="home")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def creer_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if len(context.args)<2: await update.message.reply_text("Usage: /creerCLAN TAG NOM\nEx: `/creerCLAN AKT Akatsuki`", parse_mode="Markdown"); return
    tag = context.args[0].upper()[:3]; name = " ".join(context.args[1:])[:20]
    conn = db(); c = conn.cursor()
    c.execute("SELECT tag FROM clans WHERE tag=?", (tag,))
    if c.fetchone(): conn.close(); await update.message.reply_text("❌ Tag déjà pris !"); return
    c.execute("SELECT clan_tag FROM members WHERE user_id=?", (u.id,))
    if c.fetchone(): conn.close(); await update.message.reply_text("❌ T'es déjà dans un clan !"); return
    c.execute("INSERT INTO clans VALUES (?,?,?,?)", (tag,name,u.id,0))
    c.execute("INSERT INTO members VALUES (?,?,?,?)", (u.id,tag,"chief",0))
    conn.commit(); conn.close()
    await update.message.reply_text(f"✅ *Clan [{tag}] {name} créé !*\n\nPartage le tag `{tag}` à tes amis !", parse_mode="Markdown")

async def rejoindre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not context.args: await update.message.reply_text("Usage: /rejoindre TAG"); return
    tag = context.args[0].upper()
    conn = db(); c = conn.cursor()
    c.execute("SELECT tag FROM clans WHERE tag=?", (tag,))
    if not c.fetchone(): conn.close(); await update.message.reply_text("❌ Clan introuvable !"); return
    c.execute("SELECT clan_tag FROM members WHERE user_id=?", (u.id,))
    if c.fetchone(): conn.close(); await update.message.reply_text("❌ T'es déjà dans un clan !"); return
    c.execute("INSERT INTO members VALUES (?,?,?,?)", (u.id,tag,"member",0))
    conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Clan `{tag}` rejoint !", parse_mode="Markdown")

# ═══ DUELS ═══
async def duel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    u = update.effective_user
    import string
    code = ''.join(random.choices(string.ascii_uppercase+string.digits, k=4))
    conn = db(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO duels VALUES (?,?,?,?,?,?,?,?)", (code,u.id,u.first_name,None,None,None,None,"waiting"))
    conn.commit(); conn.close()
    text = f"⚔️ *Duel créé !*\n\nCode : `{code}`\n\nEnvoie ce code à ton adversaire !\nIl tape : /joinduel {code}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Jouer ma partie", callback_data=f"dplay_{code}")], [InlineKeyboardButton("🏠 Accueil", callback_data="home")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def joinduel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not context.args: await update.message.reply_text("Usage : /joinduel CODE"); return
    code = context.args[0].upper()
    conn = db(); c = conn.cursor()
    c.execute("SELECT p1_id, status FROM duels WHERE code=?", (code,))
    row = c.fetchone()
    if not row: conn.close(); await update.message.reply_text("❌ Code invalide !"); return
    if row[0]==u.id: conn.close(); await update.message.reply_text("❌ C'est ton propre duel !"); return
    if row[1]!="waiting": conn.close(); await update.message.reply_text("❌ Duel déjà complet !"); return
    c.execute("UPDATE duels SET p2_id=?, p2_name=?, status='active' WHERE code=?", (u.id,u.first_name,code))
    conn.commit(); conn.close()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Jouer ma partie", callback_data=f"dplay_{code}")]])
    await update.message.reply_text(f"✅ *Duel rejoint !*\nCode : `{code}`", parse_mode="Markdown", reply_markup=kb)

async def duel_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    code = q.data.replace("dplay_","")
    context.user_data["duel_code"] = code
    selected = random.sample(QUESTIONS, min(5,len(QUESTIONS)))
    context.user_data.update({"queue":selected,"score":0,"correct":0,"total":0})
    await send_q(update, context)

# ═══ ADMIN PANEL ═══
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: await q.answer("❌ Accès refusé !", show_alert=True); return
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM scores")
    players = c.fetchone()[0]
    c.execute("SELECT SUM(games) FROM scores")
    games = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM clans")
    clans = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM scores WHERE banned=1")
    banned = c.fetchone()[0]
    conn.close()
    text = (
        f"🔧 *ADMIN PANEL*\n\n"
        f"👥 Joueurs : *{players}*\n"
        f"🎮 Parties jouées : *{games}*\n"
        f"🏰 Clans : *{clans}*\n"
        f"🚫 Bannis : *{banned}*\n"
        f"❓ Questions : *{len(QUESTIONS)}*"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("➕ Ajouter question", callback_data="admin_addq")],
        [InlineKeyboardButton("🚫 Bannir joueur", callback_data="admin_ban"),
         InlineKeyboardButton("✅ Débannir", callback_data="admin_unban")],
        [InlineKeyboardButton("🏆 Reset classement", callback_data="admin_reset_lb"),
         InlineKeyboardButton("📊 Stats détaillées", callback_data="admin_stats")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ])
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    context.user_data["waiting"] = "admin_broadcast"
    await q.edit_message_text("📢 Envoie le message à diffuser à tous les joueurs :")

async def admin_addq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    context.user_data["waiting"] = "admin_add_q"
    await q.edit_message_text(
        "➕ *Ajouter une question*\n\nFormat :\n`cat|question|opt1|opt2|opt3|opt4|réponse(0-3)|anime|difficulté`\n\nEx:\n`personnages|Qui est Naruto ?|Naruto|Sasuke|Sakura|Kakashi|0|Naruto|facile`",
        parse_mode="Markdown"
    )

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    context.user_data["waiting"] = "admin_ban"
    await q.edit_message_text("🚫 Envoie l'ID Telegram du joueur à bannir :")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    context.user_data["waiting"] = "admin_unban"
    await q.edit_message_text("✅ Envoie l'ID Telegram du joueur à débannir :")

async def admin_reset_lb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmer le reset", callback_data="admin_confirm_reset"),
         InlineKeyboardButton("❌ Annuler", callback_data="admin")],
    ])
    await q.edit_message_text("⚠️ *Reset le classement de TOUS les joueurs ?*", parse_mode="Markdown", reply_markup=kb)

async def admin_confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    conn = db(); c = conn.cursor()
    c.execute("UPDATE scores SET best_score=0, games=0, correct=0, total=0")
    c.execute("UPDATE clans SET score=0")
    c.execute("UPDATE members SET contrib=0")
    conn.commit(); conn.close()
    await q.edit_message_text("✅ Classement réinitialisé !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔧 Admin", callback_data="admin")]]))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    conn = db(); c = conn.cursor()
    c.execute("SELECT name, best_score FROM scores ORDER BY best_score DESC LIMIT 5")
    top5 = c.fetchall()
    c.execute("SELECT tag, name, score FROM clans ORDER BY score DESC LIMIT 3")
    top3c = c.fetchall()
    conn.close()
    text = "📊 *Stats détaillées*\n\n🏆 *Top 5 joueurs :*\n"
    for i,(n,s) in enumerate(top5): text += f"{i+1}. {n} — {s} pts\n"
    text += "\n🏰 *Top 3 clans :*\n"
    for i,(t,n,s) in enumerate(top3c): text += f"{i+1}. [{t}] {n} — {s} pts\n"
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin", callback_data="admin")]]))

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("profil", profil_cmd))
    app.add_handler(CommandHandler("duel", duel_cmd))
    app.add_handler(CommandHandler("joinduel", joinduel_cmd))
    app.add_handler(CommandHandler("creerCLAN", creer_clan))
    app.add_handler(CommandHandler("rejoindre", rejoindre_cmd))
    app.add_handler(CommandHandler("clantop", clantop_cmd))
    app.add_handler(CommandHandler("reglages", settings_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(go_home, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(quiz_cmd, pattern="^quiz$"))
    app.add_handler(CallbackQueryHandler(start_cat, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(answer, pattern="^a_"))
    app.add_handler(CallbackQueryHandler(next_q, pattern="^next$"))
    app.add_handler(CallbackQueryHandler(top_cmd, pattern="^top$"))
    app.add_handler(CallbackQueryHandler(profil_cmd, pattern="^profil$"))
    app.add_handler(CallbackQueryHandler(settings_cmd, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(set_pseudo, pattern="^set_pseudo$"))
    app.add_handler(CallbackQueryHandler(set_avatar, pattern="^set_avatar$"))
    app.add_handler(CallbackQueryHandler(pick_avatar, pattern="^av_"))
    app.add_handler(CallbackQueryHandler(set_notif, pattern="^set_notif$"))
    app.add_handler(CallbackQueryHandler(set_public, pattern="^set_public$"))
    app.add_handler(CallbackQueryHandler(set_reset, pattern="^set_reset$"))
    app.add_handler(CallbackQueryHandler(confirm_reset, pattern="^confirm_reset$"))
    app.add_handler(CallbackQueryHandler(duel_cmd, pattern="^duel$"))
    app.add_handler(CallbackQueryHandler(duel_play, pattern="^dplay_"))
    app.add_handler(CallbackQueryHandler(clan_cmd, pattern="^clan$"))
    app.add_handler(CallbackQueryHandler(clan_members, pattern="^clan_members$"))
    app.add_handler(CallbackQueryHandler(clan_manage, pattern="^clan_manage$"))
    app.add_handler(CallbackQueryHandler(clan_leave, pattern="^clan_leave$"))
    app.add_handler(CallbackQueryHandler(clan_dissolve, pattern="^clan_dissolve$"))
    app.add_handler(CallbackQueryHandler(clantop_cmd, pattern="^clantop$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_addq, pattern="^admin_addq$"))
    app.add_handler(CallbackQueryHandler(admin_ban, pattern="^admin_ban$"))
    app.add_handler(CallbackQueryHandler(admin_unban, pattern="^admin_unban$"))
    app.add_handler(CallbackQueryHandler(admin_reset_lb, pattern="^admin_reset_lb$"))
    app.add_handler(CallbackQueryHandler(admin_confirm_reset, pattern="^admin_confirm_reset$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    logger.info("Bot démarré !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
