# meta pic: https://img.icons8.com/fluency/48/000000/chatbot.png

import inspect
from .. import loader, utils, main, security
from telethon.tl.functions.channels import JoinChannelRequest
import logging

from telethon.tl.types import Message

logger = logging.getLogger(__name__)


@loader.tds
class HelpMod(loader.Module):
    """Yordam boʻlimi"""

    strings = {
        "name": "Помощь",
        "bad_module": "<b>📂 Modul topilmadi</b> <code>{}</code>",
        "single_mod_header": "🥷 <b>Имя модуля: </b> {}\n<b>├╴╴╴╴╴╴╴╴╴╴</b>",
        "single_cmd": "\n 👾 <b>{}{}</b> - ",
        "undoc_cmd": "📂 Hujjatlar yoʻq!",
        "all_header": "🥷 <b>Общие модули: <code>{}</code>\n🧟‍♀️ Скрытые: <code>{}</code></b>",
        "mod_tmpl": "\n{} <b>{}</b>",
        "first_cmd_tmpl": ": [ <code>{}</code>",
        "cmd_tmpl": " | <code>{}</code>",
        "args": "🚫 <b>Аргументы неверны</b>",
        "set_cat": "ℹ️ <b>{} входит в категорию {}</b>",
        "no_mod": "🥷 <b>Введите имя модуля...</b>",
        "hidden_shown": "<b>🥷 Скрытые модули: {}\n🧟‍♀️ Koʻrsatilgan modullar: {}\n\n</b>{}{}",
        "ihandler": "\n 👾 <b>{}</b> - ",
        "undoc_ihandler": "📂 Нет документов!!",
        "joined": "😎 <b> Вы уже являетесь участником группы!</b>",
        "join": "🥱 <b>Присоединяйтесь к группе обсуждения UMod!\n\nВсе обсуждения проходят только в формальных группах!</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "core_emoji",
            "👾",
            lambda: "Core module bullet",
            "geek_emoji",
            "👾",
            lambda: "Geek-only module bullet",
            "plain_emoji",
            "👾",
            lambda: "Plain module bullet"
        )

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

    async def berkcmd(self, message: Message) -> None:
        """modul berkitish <modul nomi>"""
        modules = utils.get_args(message)
        if not modules:
            await utils.answer(message, self.strings("no_mod"))
            return

        mods = [
            i.strings["name"]
            for i in self.allmodules.modules
            if hasattr(i, "strings") and "name" in i.strings
        ]

        modules = list(filter(lambda module: module in mods, modules))
        currently_hidden = self.get("hide", [])
        hidden, shown = [], []
        for module in modules:
            if module in currently_hidden:
                currently_hidden.remove(module)
                shown += [module]
            else:
                currently_hidden += [module]
                hidden += [module]

        self.set("hide", currently_hidden)

        await utils.answer(
            message,
            self.strings("hidden_shown").format(
                len(hidden),
                len(shown),
                "\n".join([f"🔇 <b>Спрятано:</b> <i>{m}</i>" for m in hidden]),
                "\n".join([f"🔈 <b>Открыто:</b> <i>{m}</i>" for m in shown]),
            ),
        )

    @loader.unrestricted
    async def helpcmd(self, message: Message) -> None:
        """barcha modullar [-f]"""
        args = utils.get_args_raw(message)
        force = False        
        if "-f" in args:
            args = args.replace(" -f", "").replace("-f", "")
            force = True

        prefix = utils.escape_html(
            (self._db.get(main.__name__, "command_prefix", False) or ".")
        )

        if args:
            module = None
            for mod in self.allmodules.modules:
                if mod.strings("name", message).lower() == args.lower():
                    module = mod

            if module is None:
                args = args.lower()
                args = args[1:] if args.startswith(prefix) else args
                if args in self.allmodules.commands:
                    module = self.allmodules.commands[args].__self__
                else:
                    await utils.answer(message, self.strings("bad_module").format(args))
                    return

            try:
                name = module.strings("name")
            except KeyError:
                name = getattr(module, "name", "ERROR")

            reply = self.strings("single_mod_header").format(utils.escape_html(name))
            if module.__doc__:
                reply += (
                    "<b>\n└ 🧟‍♀️ Функция модуля:</b> " + utils.escape_html(inspect.getdoc(module)) + "\n"
                )

            commands = {
                name: func
                for name, func in module.commands.items()
                if await self.allmodules.check_security(message, func)
            }

            if hasattr(module, "inline_handlers"):
                for name, fun in module.inline_handlers.items():
                    reply += self.strings("ihandler", message).format(
                        f"@{self.inline.bot_username} {name}"
                    )

                    if fun.__doc__:
                        reply += utils.escape_html(
                            "\n".join(
                                [
                                    line.strip()
                                    for line in inspect.getdoc(fun).splitlines()
                                    if not line.strip().startswith("@")
                                ]
                            )
                        )
                    else:
                        reply += self.strings("undoc_ihandler", message)

            for name, fun in commands.items():
                reply += self.strings("single_cmd").format(prefix, name)
                if fun.__doc__:
                    reply += utils.escape_html(inspect.getdoc(fun))
                else:
                    reply += self.strings("undoc_cmd")

            await utils.answer(message, reply)
            return

        count = 0
        for i in self.allmodules.modules:
            try:
                if i.commands or i.inline_handlers:
                    count += 1
            except Exception:
                pass

        mods = [
            i.strings["name"]
            for i in self.allmodules.modules
            if hasattr(i, "strings") and "name" in i.strings
        ]

        hidden = list(filter(lambda module: module in mods, self.get("hide", [])))
        self.set("hide", hidden)

        reply = self.strings("all_header").format(count, len(hidden) if not force else 0)
        shown_warn = False
        cats = {}

        for mod_name, cat in self._db.get("Help", "cats", {}).items():
            if cat not in cats:
                cats[cat] = []

            cats[cat].append(mod_name)

        plain_ = []
        core_ = []
        inline_ = []

        for mod in self.allmodules.modules:
            if not hasattr(mod, "commands"):
                logger.error(f"Module {mod.__class__.__name__} is not inited yet")
                continue

            if mod.strings["name"] in self.get("hide", []) and not force:
                continue

            tmp = ""

            try:
                name = mod.strings["name"]
            except KeyError:
                name = getattr(mod, "name", "ERROR")

            inline = (
                hasattr(mod, "callback_handlers")
                and mod.callback_handlers
                or hasattr(mod, "inline_handlers")
                and mod.inline_handlers
            )

            for cmd_ in mod.commands.values():
                try:
                    "self.inline.form(" in inspect.getsource(cmd_.__code__)
                except Exception:
                    pass

            core = mod.__origin__ == "<file>"

            if core:
                emoji = self.config['core_emoji']
            elif inline:
                emoji = self.config['geek_emoji']
            else:
                emoji = self.config['plain_emoji']

            tmp += self.strings("mod_tmpl").format(emoji, name)

            first = True

            commands = [
                name
                for name, func in mod.commands.items()
                if await self.allmodules.check_security(message, func) or force
            ]

            for cmd in commands:
                if first:
                    tmp += self.strings("first_cmd_tmpl").format(cmd)
                    first = False
                else:
                    tmp += self.strings("cmd_tmpl").format(cmd)

            icommands = [
                name
                for name, func in mod.inline_handlers.items()
                if self.inline.check_inline_security(func, message.sender_id) or force
            ]

            for cmd in icommands:
                if first:
                    tmp += self.strings("first_cmd_tmpl").format(f"🎹 {cmd}")
                    first = False
                else:
                    tmp += self.strings("cmd_tmpl").format(f"🎹 {cmd}")

            if commands or icommands:
                tmp += " ]"
                if inline:
                    inline_ += [tmp]
                elif core:
                    core_ += [tmp]
                else:
                    plain_ += [tmp]
            elif not shown_warn and (mod.commands or mod.inline_handlers):
                reply = (
                    "<i>You have permissions to execute only this commands</i>\n"
                    + reply
                )
                shown_warn = True

        plain_.sort(key=lambda x: x.split()[1])
        core_.sort(key=lambda x: x.split()[1])
        inline_.sort(key=lambda x: x.split()[1])

        await utils.answer(message, f"{reply}\n{''.join(core_)}{''.join(plain_)}{''.join(inline_)}")

    async def client_ready(self, client, db) -> None:
        self._client = client
        self.is_bot = await client.is_bot()
        self._db = db
