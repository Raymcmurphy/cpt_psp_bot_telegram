import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# PubMed Configuration
PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"
JOURNAL_TERM = "CPT+Pharmacometrics+Syst+Pharmacol"
DAYS_BACK = 30  # Number of days to look back for articles
MAX_ARTICLES = 200  # Maximum number of articles to fetch

# Bot Messages
WELCOME_MESSAGE = (
    "Welcome to the CPT Pharmacometrics & Systems Pharmacology Bot!\n\n"
    "Use /articles to get the latest articles from the past month."
)

ERROR_MESSAGE = "Sorry, there was an error fetching the articles. Please try again later."
NO_ARTICLES_MESSAGE = "No articles found for the past month."
FETCHING_MESSAGE = "Fetching latest articles from PubMed..."
START_MESSAGE = "Welcome to the CPT Pharmacometrics & Systems Pharmacology Bot!"
