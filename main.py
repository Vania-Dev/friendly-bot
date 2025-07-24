import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import schedule
import threading
import time
from dotenv import load_dotenv

from Agents.prompt_congif import PROMPT_TEMPLATES, user_prompt_selection
from Agents.text_agent import generate_conversation_stream

load_dotenv()
bot = telebot.TeleBot(os.getenv('API_TOKEN'))
USERS_ALLOWED = [int(u) for u in os.getenv('USERS_ALLOWED', '').split(',') if u]

@bot.message_handler(commands=['start'])
def send_bienvenida(message):
    if message.chat.id in USERS_ALLOWED:
        bot.reply_to(message, 'Bienvenido a NaviBot. Usa /prompt para elegir tu estilo.')

LANGUAGES = {
    "Español": "es",
    "English": "en",
    "Français": "fr"
}

@bot.message_handler(commands=["language"])
def elegir_idioma(message):
    if message.chat.id in USERS_ALLOWED:
        markup = InlineKeyboardMarkup()
        for lang_name, lang_code in LANGUAGES.items():
            markup.add(InlineKeyboardButton(lang_name, callback_data=f"lang_{lang_code}"))
        
        sent_msg = bot.send_message(message.chat.id, "🌍 Elige tu idioma / Choose your language:", reply_markup=markup)

        # Guardamos el mensaje con el teclado para poder borrarlo luego
        user_prompt_selection[str(message.chat.id)] = {"message_id": sent_msg.message_id}
        print(user_prompt_selection)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def callback_idioma(call):
    if call.message.chat.id in USERS_ALLOWED:
        lang_code = call.data.replace("lang_", "")
        user_id = str(call.from_user.id)

        if user_id not in user_prompt_selection:
            user_prompt_selection[user_id] = {}

        user_prompt_selection[user_id]["language"] = lang_code

        # Borrar mensaje anterior con los botones
        try:
            message_id_to_delete = user_prompt_selection[user_id].get("message_id")
            if message_id_to_delete:
                bot.delete_message(chat_id=call.message.chat.id, message_id=message_id_to_delete)
        except Exception as e:
            print(f"❌ Error al borrar mensaje de idioma: {e}")

        bot.answer_callback_query(call.id, "🌐 Idioma actualizado correctamente.")
        bot.send_message(call.message.chat.id, f"✅ Tu idioma ha sido cambiado a: {lang_code}")
        print(user_prompt_selection)

@bot.message_handler(commands=["prompt"])
def elegir_prompt(message):
    if message.chat.id in USERS_ALLOWED:
        markup = InlineKeyboardMarkup()
        for nombre in PROMPT_TEMPLATES:
            markup.add(InlineKeyboardButton(nombre, callback_data=nombre))
        
        # Guarda el mensaje que contiene los botones
        sent_msg = bot.send_message(message.chat.id, "Elige el prompt template:", reply_markup=markup)

        # Guarda temporalmente el ID del mensaje para borrarlo luego
        user_prompt_selection[str(message.chat.id)] = {"message_id": sent_msg.message_id}
        print(user_prompt_selection)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.message.chat.id in USERS_ALLOWED:
        selected = call.data
        user_id = str(call.from_user.id)
        user_prompt_selection[user_id]["selected_prompt"] = selected
        print(user_prompt_selection)

        # Intenta borrar el mensaje que contenía el teclado
        try:
            message_id_to_delete = user_prompt_selection[user_id].get("message_id")
            if message_id_to_delete:
                bot.delete_message(chat_id=call.message.chat.id, message_id=message_id_to_delete)
        except Exception as e:
            print(f"❌ Error al borrar mensaje: {e}")

        bot.answer_callback_query(call.id, f"Seleccionaste: {selected}")
        bot.send_message(call.message.chat.id, "✅ Prompt actualizado correctamente.")

@bot.message_handler(func=lambda msg: True, content_types=['text'])
def handle_all_messages(message):
    if message.chat.id in USERS_ALLOWED:
        user_text = message.text
        prompt_key = user_prompt_selection.get(str(message.from_user.id), {}).get("selected_prompt", "Novia Rusa")
        language = user_prompt_selection.get(str(message.from_user.id), {}).get("language", "Español")
        response = generate_conversation_stream(user_text, str(message.chat.id), prompt_key, language)
        bot.send_message(message.chat.id, response)


def send_scheduled_message():
    for user_id in USERS_ALLOWED:
        texto = "💖 ¡Hola mi amor! Solo pasaba a recordarte cuánto te amo..."
        prompt_key = user_prompt_selection.get(str(user_id), {}).get("selected_prompt", "Novia Rusa")
        language = user_prompt_selection.get(str(user_id), {}).get("language", "Español")
        response = generate_conversation_stream(texto, str(user_id), prompt_key, language)
        bot.send_message(user_id, response)

schedule.every().day.at("08:00").do(send_scheduled_message)
schedule.every().day.at("21:46").do(send_scheduled_message)

threading.Thread(target=lambda: [schedule.run_pending() or time.sleep(1)], daemon=True).start()
bot.polling(True)
