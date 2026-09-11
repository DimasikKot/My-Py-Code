// https://api.telegram.org/botВАШ_ТОКЕН/setWebhook?url=URL_ВАШЕГО_WORKERA

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

// Функция отправки сообщений в Telegram
async function sendMessage(chatId, text, token) {
  const url = `https://api.telegram.org/bot${token}/sendMessage`;

  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
    }),
  });
}

async function handleRequest(request) {
  const BOT_TOKEN = env.BOT_TOKEN;

  // Telegram шлет POST-запросы, когда кто-то пишет боту
  if (request.method === "POST") {
    const update = await request.json();

    // Если пришло сообщение
    if (update.message) {
      const chatId = update.message.chat.id;
      const text = update.message.text;
      const userName = update.message.from.first_name;

      // Логика ответов
      let reply = "";

      if (text === "/start") {
        reply = `Йоу, ${userName}! 👋\n\nЯ бот на Cloudflare Workers, и я ваще не падаю.`;
      } else if (text === "/help") {
        reply =
          "🤖 Команды:\n/start - Начать\n/help - Эта хуйня\n\nОстальное пока не завезли.";
      } else {
        reply = `Ты написал: "${text}"\n\n...и что мне с этим делать? 🤔`;
      }

      // Шлем ответ юзеру
      await sendMessage(chatId, reply, BOT_TOKEN);
    }

    return new Response("OK", { status: 200 });
  }

  // Если кто-то просто открыл ссылку на Worker'а
  return new Response("🤖 Бот живой, здоровый, не ебет.", { status: 200 });
}
