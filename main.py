import os
import random
import httpx
import json
import supabase
import os
import db as db
import datetime 
from datetime import timedelta
import rain
from io import BytesIO

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK = os.environ.get("WEBHOOK", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect_db()
    app.state.http = httpx.AsyncClient(timeout=15)
    yield
    await app.state.http.aclose()

app = FastAPI(lifespan=lifespan)

async def telegram_request(method, data):
    if not TOKEN:
        print("BOT_TOKEN is not set.")
        return None

    try:
        response = await app.state.http.post(
            f"{TELEGRAM_API}/{method}",
            json=data
        )

        if response.status_code != 200:
            print("Telegram Error:", response.text)

        response.raise_for_status()
        return response.json()

    except Exception as e:
        print("Telegram API Error:", e)
        return None


async def send_reply(chat_id, message_id, text):
    return await telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": message_id
        }
    )


async def send_message(chat_id, text):
    return await telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )

async def send_message_data(data):
    return await telegram_request(
            "sendMessage",data
        )

async def delete_message(chat_id, message_id):
    return await telegram_request(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id
        }
    )

async def edit_message(data):
    try:
        return await telegram_request(
            "editMessageText",data
        )
    except Exception as e:
        return str(e)

async def setWebhook(token, secret) -> list:
    try:
        response = await app.state.http.post(f"https://api.telegram.org/bot{token}/setWebhook?url={WEBHOOK}")
        return response.json()
    except Exception as e:
        return str(e)

async def get_status(msg):
    try:
        status = await db.get_status(eq="user_id", eq_value=int(msg.user.id))
        if len(status) != 0:
            return str(status[0].get("status","main"))
        else:
            if msg.user.id != 0:
                await db.insert(data={
                    "name": f'{msg.user.first_name} {msg.user.last_name}',
                    "username": str(msg.user.username),
                    "user_id": int(msg.user.id)
                })
                return "main"
        return "none"

    except Exception as e:
        return str(e)

async def get_data() -> list:
    response = None
    async with httpx.AsyncClient() as client:
        response = await client.post("https://webapp.irimo.ir/metapi/msglist.php")
    resp = response.json()
    
    stations = []
    for data in resp:
        if data["province"] == "Mazandaran":
            stations.append(
                {
                    "name": data["station"],
                    "rain_24": float(data["rrr24"]),
                    "rain_6": float(data["rrr6"]),
                    "temp": float(data["t"]),
                    "t_min": float(data["t_min"]),
                    "t_max": float(data["t_max"]),
                    "lat": float(data["lat"]),                    
                    "lon": float(data["lon"]),
                    "data_time": data["data_time"]
                }
            )

    return stations

async def fix_database(args, user_id):
    if "token" in args: await db.db.table("tokens").delete().eq("creator_id", int(user_id)).eq("token","NONE").execute()

@app.get("/")
async def index():
    return PlainTextResponse("ok good")


@app.post("/")
async def webhook(request: Request):

    update = await request.json()
    message = update.get("message", {}) or update.get("edited_message", {})

    class msg:
        chat_id = message.get("chat",{}).get("id",0)
        message_id = message.get("message_id",0)
        class user:
            user = message.get("from", {})
            id = user.get("id", 0)
            first_name = user.get("first_name", "")
            last_name = user.get("last_name", "")
            username = user.get("username","")
        chat_type = message.get("chat",{}).get("type","")
        text = str(message.get("text", ""))

    status = await get_status(msg)

    if "callback_query" in update:
        class callback:
            data = update.get("callback_query",{})
            id = data.get("id",0)
            chat_id = data.get("message",{}).get("chat",{}).get("id",0)
            message_id = data.get("message",{}).get("message_id",0)
            button = data.get("data",{})
            class user:
                user = update.get("callback_query",{}).get("from",{})
                id = user.get("id", 0)
                first_name = user.get("first_name", "")
                last_name = user.get("last_name", "")
                username = user.get("username","")

        match callback.button:
            case "main":
                pass
            case "account":
                text = (
                    f"نام: <b>{callback.user.first_name} {callback.user.last_name}</b>\n"
                    f"یوزنیم: {callback.user.username if callback.user.username != "" else "🟥"}\n"
                    f"آیدی: <code>{callback.user.id}</code>\n"
                    f"اشتراک: ❌"
                )

                await edit_message(data={
                    "chat_id": callback.chat_id,
                    "message_id": callback.message_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {"text": "Back", "callback_data": "back_1", "style": "danger"}
                            ]
                        ]
                    }
                })
            case "24_rain":
                data = await get_data()
                data.sort(key=lambda x:x["rain_24"], reverse=True)

                text = "<b>مقدار بارش 24 ساعت گذشته ایستگاه های مازندران:</b>\n\n"
                for i, _data in enumerate(data):
                    dt = datetime.datetime.strptime(_data["data_time"], "%Y-%m-%d %H:%M:%S")
                    dt += timedelta(hours=3, minutes=30)
                    text += f"<b>{i+1}- {_data["name"]}: ({_data["rain_24"]}) میلی متر</b>\n"

                await edit_message(data={
                    "chat_id": callback.chat_id,
                    "message_id": callback.message_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup":
                    {
                        "inline_keyboard":
                        [
                            [
                                {"text": "زمان آخرین آپدیت", "callback_data": "up_time_24", "style": "primary"}
                            ],
                            [
                                {"text": "Back", "callback_data": "back_2", "style": "danger"}
                            ]
                        ]
                    }
                })
            case "6_rain":
                data = await get_data()
                data.sort(key=lambda x:x["rain_24"], reverse=True)

                text = "<b>مقدار بارش 6 ساعت گذشته ایستگاه های مازندران:</b>\n\n"
                for i, _data in enumerate(data):
                    dt = datetime.datetime.strptime(_data["data_time"], "%Y-%m-%d %H:%M:%S")
                    dt += timedelta(hours=3, minutes=30)
                    text += f"<b>{i+1}- {_data["name"]}: ({_data["rain_6"]}) میلی متر</b>\n"

                await edit_message(data={
                    "chat_id": callback.chat_id,
                    "message_id": callback.message_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup":
                    {
                        "inline_keyboard":
                        [
                            [
                                {"text": "زمان آخرین آپدیت", "callback_data": "up_time_6", "style": "primary"}
                            ],
                            [
                                {"text": "Back", "callback_data": "back_2", "style": "danger"}
                            ]
                        ]
                    }                    
                })
            case t if "up_time" in t:
                j = t[8:]
                data = await get_data()
                text = "<b>زمان آخرین آپدیت ایستگاه های مازندران:</b>\n\n"
                
                for i, _data in enumerate(data):
                    dt = datetime.datetime.strptime(_data["data_time"], "%Y-%m-%d %H:%M:%S")
                    dt += timedelta(hours=3, minutes=30)
                    text += f"<b>{_data["name"]}: {dt.hour}:{dt.minute}</b>\n"
                
                await edit_message(data={
                    "chat_id": callback.chat_id,
                    "message_id": callback.message_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup":
                    {
                        "inline_keyboard":
                        [
                            [
                                {"text": "مقدار بارش", "callback_data": f"{j}_rain", "style": "primary"}
                            ],
                            [
                                {"text": "Back", "callback_data": "back_2", "style": "danger"}
                            ]
                        ]
                    }
                })
                
            case "rain_chart":
                data = await get_data()
                data.sort(key=lambda x:x["rain_24"], reverse=True)

                stations = []
                for d in data:
                    stations.append({"name": d["name"], "rain": float(d["rain_24"])})
                img = rain.do_rain(stations)
                buffer = BytesIO()

                img.save(buffer, format="PNG")
                buffer.seek(0)
                url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        data={"chat_id": callback.chat_id, "reply_to_message_id": callback.message_id},
                        files={
                            "photo": ("report.png", buffer, "image/png")
                        }
                    )
            case "back_2":
                await edit_message(data={
                    "chat_id": callback.chat_id,
                    "message_id": callback.message_id,
                    "text": (
                        "گزینه مورد نظر را انتخاب کنید"
                    ),
                    "reply_markup":
                    {
                        "inline_keyboard": 
                        [
                            [
                                {"text": "آمار کل", "callback_data": "rain", "style": "success"}   
                            ],
                            [
                                {"text": "بارش 24 ساعته", "callback_data": "24_rain", "style": "success"},
                                {"text": "بارش 6 ساعته", "callback_data": "6_rain", "style": "success"}
                            ]
                        ],
                    }
                })
            case "back_1":
                await db.set_status(eq="user_id", eq_value=int(callback.user.id), status="main")
                await send_message_data(data={
                    "chat_id": callback.chat_id,
                    "text": (
                        f"سلام <b>{callback.user.first_name}</b> به ربات هواشناسی مازندران خوش آمدید\n"
                        "از منوی زیر میتونید برای دریافت خدمات استفاده کنید"
                    ),
                    "parse_mode": "HTML",
                    "reply_markup": {
                        "inline_keyboard": 
                        [
                            [
                                {"text": "حساب کاربری", "callback_data": "account", "style": "success"}
                            ]
                        ],
                        "keyboard":
                        [
                            [
                                {"text": "آمار بارش"},
                                {"text": "آمار دما"},
                                {"text": "ایستگاه ها"}
                            ],
                            [
                                {"text": "پیش بینی آب و هوا"}
                            ]
                        ],
                        "resize_keyboard": True
                    }
                })

        await telegram_request("answerCallbackQuery", {"callback_query_id": callback.id})
        return {"ok": True}

    if msg.text == "/start":
        await db.set_status(eq="user_id", eq_value=int(msg.user.id), status="main")
        await send_message_data(data={
            "chat_id": msg.chat_id,
            "text": (
                f"سلام <b>{msg.user.first_name}</b> به ربات هواشناسی مازندران خوش آمدید\n"
                "از منوی زیر میتونید برای دریافت خدمات استفاده کنید"
            ),
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": 
                [
                    [
                        {"text": "حساب کاربری", "callback_data": "account", "style": "success"}
                    ]
                ],
                "keyboard":
                [
                    [
                        {"text": "آمار بارش"},
                        {"text": "آمار دما"},
                        {"text": "ایستگاه ها"}
                    ],
                    [
                        {"text": "پیش بینی آب و هوا"}
                    ]
                ],
                "resize_keyboard": True
            }
        })
        return

    if "/start" and "آمار بارش" not in msg.text and len(msg.text) != 0:
        await send_message(msg.chat_id, "ربات درحال تکمیل و توسعه است.\nدرحال حاضر فقط آمار بارش در دسترس میباشد.")

    match msg.text:
        case "آمار بارش":
            await send_message_data(data={
                "chat_id": msg.chat_id,
                "text": (
                    "گزینه مورد نظر را انتخاب کنید"
                ),
                "reply_markup":
                {
                    "inline_keyboard": 
                    [
                        [
                           {"text": "آمار کل", "callback_data": "rain_stats", "style": "success"}   
                        ],
                        [
                           {"text": "نمودار مقایسه بارش", "callback_data": "rain_chart", "style": "success"}   
                        ],
                        [
                            {"text": "بارش 24 ساعته", "callback_data": "24_rain", "style": "success"},
                            {"text": "بارش 6 ساعته", "callback_data": "6_rain", "style": "success"},
                        ]   
                    ],
                }
            })
        case "آمار دما":
            # await send_message_data(data={
            #     "chat_id": msg.chat_id,
            #     "text": (
            #         "گزینه مورد نظر را انتخاب کنید"
            #     ),
            #     "reply_markup":
            #     {
            #         "inline_keyboard": 
            #         [
            #             [
            #                 {"text": "دمای فعلی", "callback_data": "now_temp", "style": "success"},
            #                 {"text": "دمای کمینه و بیشینه", "callback_data": "maxmin_temp", "style": "primary"},
            #             ]   
            #         ],
            #     }
            # })
            pass
            
    match status:
        case "main":
            pass
        case "enter_bot_name_1":
           pass
        case text if "enter_bot_token_1" in text:
           pass

    return {"ok": True}

