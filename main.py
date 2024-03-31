import telebot
import requests
import json

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Initialize the bot with your token
bot = telebot.TeleBot(config['telegramToken'])

# Global dictionary to store user states
user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome to animedown use /animedown")

@bot.message_handler(commands=['animedown'])
def animedown(message):
    user_id = message.from_user.id
    query = ' '.join(message.text.split()[1:])
    search_url = f"{config['searchBaseUrl']}/{query}"

    try:
        response = requests.get(search_url)
        data = response.json()

        if not data['results']:
            bot.reply_to(message, "no info")
            return

        # Store the search results in the user's state
        user_states[user_id] = {
            'state': 'select',
            'results': data['results']
        }

        # Create an inline keyboard with the anime options
        keyboard = telebot.types.InlineKeyboardMarkup()
        for index, anime in enumerate(data['results']):
            keyboard.add(telebot.types.InlineKeyboardButton(text=f"{index + 1}. {anime['title']}", callback_data=str(index)))

        bot.send_message(message.chat.id, "Search Results:", reply_markup=keyboard)

    except Exception as e:
        print('Error searching for anime:', e)
        bot.reply_to(message, "An error occurred while searching for the anime.")

@bot.callback_query_handler(func=lambda call: True)
def button_click(call):
    user_id = call.from_user.id
    if user_id in user_states and user_states[user_id]['state'] == 'select':
        selected_index = int(call.data)
        selected = user_states[user_id]['results'][selected_index]

        # Update the user's state
        user_states[user_id] = {
            'state': 'enter',
            'selected': selected
        }

        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"You selected: {selected['title']}\nPlease enter the episode number:")

@bot.message_handler(func=lambda message: True)
def handle_episode_input(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id]['state'] == 'enter':
        episode_number = message.text

        if not episode_number.isdigit():
            bot.reply_to(message, "Please enter a valid episode number.")
            return

        episode_number = int(episode_number)
        selected = user_states[user_id]['selected']

        # Fetch and send the download links for the selected anime and episode
        send_links(selected['id'], episode_number, message)

        # Clear the user's state after processing
        del user_states[user_id]

def shorten_url(long_url):
    response = requests.get(f"http://tinyurl.com/api-create.php?url={long_url}")
    return response.text

def send_links(anime_id, episode_number, message):
    watch_url = f"{config['searchBaseUrl']}/watch/{anime_id}-episode-{episode_number}"
    download_url = f"{config['downloadBaseUrl']}/download/{anime_id}-episode-{episode_number}"

    try:
        watch_response = requests.get(watch_url, params={'server': 'gogocdn'})
        download_response = requests.get(download_url)

        watch_data = watch_response.json()
        download_data = download_response.json()

        streaming_links = []
        for source in watch_data.get('sources', []):
            shortened_url = shorten_url(source['url'])
            streaming_links.append(f"[{source['quality']}]({shortened_url})")

        download_links = []
        for quality, url in download_data.get('results', {}).items():
            shortened_url = shorten_url(url)
            download_links.append(f"[{quality}]({shortened_url})")

        links_text = ""
        if streaming_links:
            links_text += f"**Streaming Links:**\n{', '.join(streaming_links)}\n\n"
        else:
            links_text += "No streaming links available.\n\n"

        if download_links:
            links_text += f"**Download Links:**\n{', '.join(download_links)}"
        else:
            links_text += "No download links available."

        bot.send_message(message.chat.id, text=links_text, parse_mode="MarkdownV2")

    except Exception as e:
        print('Error fetching download links:', e)
        bot.reply_to(message, "An error occurred while fetching the download links.")

# Start the bot
bot.polling()
