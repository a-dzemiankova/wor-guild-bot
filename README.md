### How to run a project:
#### *Local development*
- GuildBotWoR> `python -m venv venv`
- GuildBotWoR> `\myenv\Scripts\activate`
- (venv) GuildBotWoR> `pip install -r  requirements.txt`
- Use an interpreter from venv
- Add your .env-variables from your telegram-bot(see .env-example)
- (venv) GuildBotWoR> `python bot_interface.py`

#### *Docker*
- GuildBotWoR>  `docker build wor_bot .`
- GuildBotWoR> `docker run -e SERVICE_ACCOUNT_FILE=<account_file> -e TOKEN=<token> -e TABLE_LINK=<table_link> wor_bot`
- to enable debug mode for a logger add another env-variable`-e DEBUG=1` to the previous line (before the image name)