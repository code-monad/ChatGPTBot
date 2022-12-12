# Requirements

- [Latest python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Latest ChatGPT](https://github.com/acheong08/ChatGPT)

# Usage

First, you should install `python-telegram-bot` and `ChatGPT` library from source 
```bash
# Install telegram bot library
git clone https://github.com/python-telegram-bot/python-telegram-bot
cd python-telegram-bot && python setup.py install --user
# For proxy support
pip install python-telegram-bot[socks] 

# Install ChatGPT API
git clone https://github.com/acheong08/ChatGPT
cd ChatGPT && python setup.py install --user
```

First, create a `config.toml` from the [template file](./config.example.toml)

Modify the content, replace with the correct keys/session-ids

```bash
python main.py
```

# Avaliable Commands

- `/start` -- Initialize
- `/list` -- List all memories
- `/check` -- Check current session detail
- `/reborn` -- Start a new session
- `/rollback` -- Forgot last prompt 