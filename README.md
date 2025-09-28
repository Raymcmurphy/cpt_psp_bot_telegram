# CPT Pharmacometrics & Systems Pharmacology Telegram Bot

A Telegram bot that scrapes and provides access to articles from the "CPT Pharmacometrics & Systems Pharmacology" journal published in the past month or custom date ranges.

## Features

- **Article Discovery**: Get articles from the past month or custom date ranges
- **Article Details**: View PMID, publication date, and full titles
- **Abstract Access**: Retrieve full abstracts for specific articles
- **Journal Links**: Direct links to articles on PubMed and Wiley Online Library
- **Chronological Order**: Articles sorted by publication date (newest first)

## Commands

- `/start` - Welcome message and help
- `/articles` - Get articles from the past month
- `/custom` - Get articles from custom date range
- `/abstract <PMID>` - Get abstract for specific article

## Deployment

This bot is designed to run on Railway. To deploy:

1. Fork this repository
2. Connect your GitHub repository to Railway
3. Set the environment variable `TELEGRAM_BOT_TOKEN` in Railway dashboard
4. Deploy!

## Environment Variables

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (required)

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variable: `export TELEGRAM_BOT_TOKEN="your_bot_token"`
4. Run the bot: `python bot.py`

## Dependencies

- python-telegram-bot
- requests
- beautifulsoup4
- lxml

## License

MIT License