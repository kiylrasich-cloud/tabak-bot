import os, requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

API_TOKEN = os.environ["BOT_TOKEN"]
SHEETS_URL = os.environ["SHEETS_URL"]

FLAVORS = [
    {"id": 1,  "name": "Каштан"},
    {"id": 2,  "name": "Блек афгано"},
    {"id": 3,  "name": "Амбровый перскик"},
    {"id": 4,  "name": "Байкал"},
    {"id": 5,  "name": "Зелёный крыжовник"},
    {"id": 6,  "name": "Байкальский чабрец"},
    {"id": 7,  "name": "Щавель"},
    {"id": 8,  "name": "Вишня-гранат"},
    {"id": 9,  "name": "Маргарита"},
    {"id": 10, "name": "Азиатская дыня"},
    {"id": 11, "name": "Киндер шоколад"},
    {"id": 12, "name": "Кубики манго"},
]

PHOTOS = {}
DEFAULT_PHOTO = None

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
state = {}

def sheet_append(row):
    try:
        r = requests.post(SHEETS_URL, json={"row": row}, timeout=10)
        print("sheet:", r.status_code, r.text[:100])
    except Exception as e:
        print("sheet error:", e)

def flavors_kb():
    kb = InlineKeyboardMarkup()
    for f in FLAVORS:
        kb.row(InlineKeyboardButton(text=f["name"], callback_data=f"fl:{f['id']}"))
    kb.row(InlineKeyboardButton(text="📊 Мои оценки", callback_data="mine"))
    return kb

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        "🗂 <b>Дегустация табака</b>\n"
        "🏛 Лаунж-бар «Дуть» · ул. Якуба Коласа, 7а · 22 ноября\n\n"
        "Выбери вкус, который сейчас пробуешь:",
        parse_mode=ParseMode.HTML, reply_markup=flavors_kb())

@dp.callback_query(F.startswith("fl:"))
async def pick(call: types.CallbackQuery):
    fid = int(call.data.split(":")[1])
    f = next(x for x in FLAVORS if x["id"] == fid)
    st = state.setdefault(call.from_user.id, {})
    st["fid"], st["d"], st["await"], st["mode"] = fid, {}, None, None
    photo = PHOTOS.get(fid, DEFAULT_PHOTO)
    caption = (f"🔥 <b>{f['name']}</b>\n\n"
               "1️⃣ Крепость — от 1 (лёгкий) до 10 (очень крепкий)\n"
               "2️⃣ «Тебе вкусно?» — от 1 (не вкусно) до 10 (вкусно)\n\nЖми кнопки 👇")
    kb = InlineKeyboardMarkup()
    kb.row(*[InlineKeyboardButton(text=str(i), callback_data=f"str:{fid}:{i}") for i in range(1, 11)])
    if photo:
        await call.message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await call.message.answer(caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    await call.answer()

@dp.callback_query(F.startswith("str:"))
async def score(call: types.CallbackQuery):
    _, fid, val = call.data.split(":")
    fid, val = int(fid), int(val)
    st = state.setdefault(call.from_user.id, {})
    st.setdefault("d", {})
    if "strength" not in st["d"]:
        st["d"]["strength"] = val
        kb = InlineKeyboardMarkup()
        kb.row(*[InlineKeyboardButton(text=str(i), callback_data=f"str:{fid}:{i}") for i in range(1, 11)])
        await call.message.answer(f"💪 Крепость: {val}/10. Теперь вкус 👇", reply_markup=kb)
    else:
        st["d"]["taste"] = val
        st["await"] = "comment"
        await call.message.answer("👅 Вкус принят. Напиши комментарий или «/пропустить».",
                                  reply_markup=types.ReplyKeyboardRemove())
    await call.answer()

@dp.message(F.text)
async def comment(msg: types.Message):
    st = state.get(msg.from_user.id, {})
    if st.get("await") != "comment":
        return
    txt = "" if msg.text.strip() == "/пропустить" else msg.text[:300]
    st["await"] = None
    f = next(x for x in FLAVORS if x["id"] == st["fid"]])
    d = st["d"]
    sheet_append([str(msg.from_user.id), msg.from_user.first_name or "", f["name"],
                  str(d.get("strength", "")), str(d.get("taste", "")), txt,
                  msg.date.strftime("%Y-%m-%d %H:%M")])
    await msg.answer(f"✅ <b>{f['name']}</b> записана!\n"
                     f"Крепость {d.get('strength')}/10 · Вкус {d.get('taste')}/10\n\nПробуем следующий вкус?",
                     parse_mode=ParseMode.HTML, reply_markup=flavors_kb())

@dp.callback_query(F(lambda c: c.data == "mine"))
async def mine(call: types.CallbackQuery):
    st = state.get(call.from_user.id, {})
    lines = []
    for f in FLAVORS:
        d = st.get("d") if st.get("fid") == f["id"] else None
        if d:
            lines.append(f"• {f['name']}: крепость {d.get('strength')}/10, вкус {d.get('taste')}/10")
    await call.message.answer("📊 Твои оценки:\n" + ("\n".join(lines) or "Пока пусто. Выбери вкус 👆"))
    await call.answer()

@dp.message(Command("logo"))
async def logo_cmd(msg: types.Message):
    state.setdefault(msg.from_user.id, {})["mode"] = "logo"
    await msg.answer("Пришли картинку-логотип — поставлю её ко всем 12 вкусам.")

@dp.message(Command("logooff"))
async def logo_off(msg: types.Message):
    global DEFAULT_PHOTO
    DEFAULT_PHOTO = None
    await msg.answer("Логотип убран.")

@dp.message(F.photo)
async def set_photo(msg: types.Message):
    global DEFAULT_PHOTO
    st = state.setdefault(msg.from_user.id, {})
    if st.get("mode") == "logo":
        DEFAULT_PHOTO = msg.photo[-1].file_id
        st["mode"] = None
        await msg.answer("✅ Логотип сохранён — теперь он у всех 12 вкусов.", reply_markup=flavors_kb())
        return
    fid = st.get("fid")
    if fid:
        PHOTOS[fid] = msg.photo[-1].file_id
        f = next(x for x in FLAVORS if x["id"] == fid)
        await msg.answer(f"✅ Фото для «{f['name']}» обновлено.", reply_markup=flavors_kb())

if __name__ == "__main__":
    print("BOT STARTED")
    dp.run_polling(bot)
