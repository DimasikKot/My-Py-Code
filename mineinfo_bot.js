import { connect } from "cloudflare:sockets";

// ============================================================
// Telegram API helpers
// ============================================================
async function sendMessage(chatId, text, token, parseMode = null) {
  const body = { chat_id: chatId, text };
  if (parseMode) body.parse_mode = parseMode;

  const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return await res.json();
}

async function editMessage(chatId, messageId, text, token, parseMode = null) {
  const body = { chat_id: chatId, message_id: messageId, text };
  if (parseMode) body.parse_mode = parseMode;

  const res = await fetch(
    `https://api.telegram.org/bot${token}/editMessageText`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  return await res.json();
}

async function deleteMessage(chatId, messageId, token) {
  await fetch(`https://api.telegram.org/bot${token}/deleteMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, message_id: messageId }),
  });
}

async function sendChatAction(chatId, action, token) {
  await fetch(`https://api.telegram.org/bot${token}/sendChatAction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, action }),
  });
}

// ============================================================
// Minecraft Protocol — VarInt утилиты
// ============================================================

// Кодирование VarInt (поддерживает и отрицательные значения, напр. -1)
function writeVarInt(value) {
  const bytes = [];
  let v = value >>> 0; // приводим к unsigned 32-bit
  while (true) {
    if ((v & ~0x7f) === 0) {
      bytes.push(v);
      break;
    }
    bytes.push((v & 0x7f) | 0x80);
    v >>>= 7;
  }
  return new Uint8Array(bytes);
}

// Чтение VarInt из Uint8Array начиная с offset → [value, newOffset]
function readVarIntFromBuffer(buf, offset = 0) {
  let value = 0;
  let position = 0;
  while (true) {
    if (offset >= buf.length) throw new Error("VarInt: буфер закончился");
    const byte = buf[offset++];
    value |= (byte & 0x7f) << position;
    if ((byte & 0x80) === 0) break;
    position += 7;
    if (position >= 32) throw new Error("VarInt слишком большой");
  }
  return [value >>> 0, offset];
}

// Склейка нескольких Uint8Array в один
function concatBytes(...arrays) {
  const total = arrays.reduce((s, a) => s + a.length, 0);
  const out = new Uint8Array(total);
  let o = 0;
  for (const a of arrays) {
    out.set(a, o);
    o += a.length;
  }
  return out;
}

// ============================================================
// Minecraft Protocol — сборка пакетов
// ============================================================

// Handshake (state=1) — первое, что шлёт клиент
function buildHandshakePacket(host, port) {
  const hostBytes = new TextEncoder().encode(host);

  const payload = concatBytes(
    writeVarInt(0x00), // Packet ID
    writeVarInt(-1), // Protocol Version (-1 = "просто статус")
    writeVarInt(hostBytes.length), // длина адреса
    hostBytes, // адрес
    new Uint8Array([(port >> 8) & 0xff, port & 0xff]), // порт (big-endian)
    writeVarInt(1), // Next State = 1 (status)
  );

  // Спереди — длина всего пакета
  return concatBytes(writeVarInt(payload.length), payload);
}

// Status Request — пустой пакет длиной 1 с ID=0x00
function buildStatusRequestPacket() {
  return new Uint8Array([0x01, 0x00]);
}

// ============================================================
// Получение статуса Minecraft-сервера через mcsrvstat.us
// ============================================================
async function getMinecraftStatus(ip, port = 25565, timeoutMs = 10000) {
  try {
    // Таймаут через AbortController, чтобы запрос не висел
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    let res;
    try {
      res = await fetch(`https://api.mcsrvstat.us/3/${ip}:${port}`, {
        headers: { "User-Agent": "Cloudflare-Worker-Bot/1.0" },
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    if (!res.ok) {
      throw new Error(`API вернул ошибку: ${res.status}`);
    }

    const data = await res.json();

    // // Сервер оффлайн или не отвечает
    // if (!data.online) {
    //   return { error: "⏰ Сервер оффлайн" };
    // }

    // ---- Игроки ----
    const players = data.players || {};

    let playersList = "Нет игроков онлайн";
    if (Array.isArray(players.list) && players.list.length) {
      playersList = players.list.map((p) => `• ${p.name}`).join("\n");
    }

    // ---- Версия ----
    const version = data.version || "N/A";

    // ---- MOTD ----
    // mcsrvstat.us отдаёт motd.clean как массив строк
    let motd = "N/A";
    if (data.motd?.clean) {
      motd = Array.isArray(data.motd.clean)
        ? data.motd.clean.join(" ")
        : data.motd.clean;
    }

    return {
      online: players.online || 0,
      max: players.max || 0,
      version,
      motd,
      players_list: playersList,
    };
  } catch (error) {
    // Отдельно обрабатываем таймаут (AbortError)
    if (error.name === "AbortError") {
      return { error: "⏰ Таймаут подключения" };
    }
    return { error: `❌ Ошибка: ${error.message}` };
  }
}

// ============================================================
// Утилита задержки
// ============================================================
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ============================================================
// Обработчик команды /smp /purmur /purpur /vanilla
// ============================================================
async function handlePurMurVanilla(chatId, token) {
  const loading = await sendMessage(
    chatId,
    "🔄 Получение информации о сервере...",
    token,
  );
  const messageId = loading.result?.message_id;
  if (!messageId) return;

  const status = await getMinecraftStatus("purmur.exaroton.me", 58386);

  if (status.error) {
    for (let i = 15; i > 0; i--) {
      await editMessage(
        chatId,
        messageId,
        `❌ ${status.error}\n\n⏳ Сообщение будет удалено через ${i} сек...`,
        token,
      );
      await sleep(1000);
    }
    await deleteMessage(chatId, messageId, token);
    return;
  }

  const response =
    `🎮 **Полная информация о сервере PurMur Vanilla**\n` +
    `📌 **IP:** \`purmur.exaroton.me:58386\`\n` +
    `📡 **Версия:** ${status.version}\n` +
    `👥 **Игроки:** ${status.online}/${status.max}\n` +
    `📝 **MOTD:** ${status.motd}\n\n` +
    `**📋 Список игроков онлайн:**\n${status.players_list}`;

  for (let i = 15; i > 0; i--) {
    await editMessage(
      chatId,
      messageId,
      response + `\n\n⏳ Сообщение будет удалено через ${i} сек...`,
      token,
      "Markdown",
    );
    await sleep(1000);
  }
  await deleteMessage(chatId, messageId, token);
}

// ============================================================
// Обработчик команды /create /info
// ============================================================
async function handlePurMurCreate(chatId, token) {
  const loading = await sendMessage(
    chatId,
    "🔄 Получение информации о сервере...",
    token,
  );
  const messageId = loading.result?.message_id;
  if (!messageId) return;

  const status = await getMinecraftStatus("185.9.145.210", 32290);

  if (status.error) {
    for (let i = 15; i > 0; i--) {
      await editMessage(
        chatId,
        messageId,
        `❌ ${status.error}\n\n⏳ Сообщение будет удалено через ${i} сек...`,
        token,
      );
      await sleep(1000);
    }
    await deleteMessage(chatId, messageId, token);
    return;
  }

  const response =
    `🎮 **Полная информация о сервере PurMur Create**\n` +
    `📌 **IP:** \`${"185.9.145.210"}:${32290}\`\n` +
    `📡 **Версия:** ${status.version}\n` +
    `👥 **Игроки:** ${status.online}/${status.max}\n` +
    `📝 **MOTD:** ${status.motd}\n\n` +
    `**📋 Список игроков онлайн:**\n${status.players_list}`;

  for (let i = 15; i > 0; i--) {
    await editMessage(
      chatId,
      messageId,
      response + `\n\n⏳ Сообщение будет удалено через ${i} сек...`,
      token,
      "Markdown",
    );
    await sleep(1000);
  }
  await deleteMessage(chatId, messageId, token);
}

// ============================================================
// Обработка апдейта от Telegram
// ============================================================
async function handleUpdate(update, env) {
  const BOT_TOKEN = env.BOT_TOKEN;

  if (!update.message) return;

  const chatId = update.message.chat.id;
  const text = update.message.text;
  const userName = update.message.from?.first_name || "друг";

  if (!text) return;

  if (["/purmur", "/vanilla"].includes(text)) {
    await sendChatAction(chatId, "typing", BOT_TOKEN);
    await handlePurMurVanilla(chatId, BOT_TOKEN);
    return;
  }

  if (["/create", "/info"].includes(text)) {
    await sendChatAction(chatId, "typing", BOT_TOKEN);
    await handlePurMurCreate(chatId, BOT_TOKEN);
    return;
  }

  if (text === "/start") {
    const reply =
      `Привет, ${userName}\n\n` +
      `Я бот для мониторинга Minecraft серверов\n\n` +
      `🎮 **Доступные команды:**\n` +
      `/vanilla /purmur — PurMur Vanilla\n` +
      `/create /info — PurMur Create\n` +
      `ℹ️ Сообщения с информацией автоматически удаляются через 15 секунд.`;
    await sendMessage(chatId, reply, BOT_TOKEN, "Markdown");
    return;
  }

  if (text.startsWith("/")) {
    await sendMessage(
      chatId,
      `❓ Неизвестная команда: ${text}\n\nИспользуйте /start для списка команд.`,
      BOT_TOKEN,
    );
  }
}

// ============================================================
// ТОЧКА ВХОДА (ES Modules) — Cloudflare Workers
// ============================================================
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return new Response("Bot is running ✅", { status: 200 });
    }

    if (request.method === "POST") {
      try {
        const update = await request.json();
        ctx.waitUntil(handleUpdate(update, env));
      } catch (e) {
        console.error("Webhook parse error:", e);
      }
      return new Response("OK", { status: 200 });
    }

    return new Response("Not found", { status: 404 });
  },
};
