import os
import logging
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from flask import Flask
import threading

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PubMedBot:
    def __init__(self, token):
        self.token = token
        self.base_url = PUBMED_BASE_URL
        
    def get_date_range(self, custom_start=None, custom_end=None):
        """Calculate date range for the past month or custom range"""
        if custom_start and custom_end:
            # Use custom dates
            start_date = datetime.strptime(custom_start, "%Y-%m-%d")
            end_date = datetime.strptime(custom_end, "%Y-%m-%d")
        else:
            # Use past month
            end_date = datetime.now()
            start_date = end_date - timedelta(days=DAYS_BACK)
        
        # Format dates for PubMed URL - use proper URL encoding
        start_str = start_date.strftime("%Y/%m/%d").replace("/", "%2F")
        end_str = end_date.strftime("%Y/%m/%d").replace("/", "%2F")
        
        return start_str, end_str
    
    def scrape_pubmed(self, custom_start=None, custom_end=None):
        """Scrape PubMed for CPT Pharmacometrics & Systems Pharmacology articles"""
        start_date, end_date = self.get_date_range(custom_start, custom_end)
        
        # Construct the PubMed URL
        url = f"{self.base_url}?term=%22{JOURNAL_TERM}%22%5BJournal%5D&filter=dates.{start_date}-{end_date}&sort=date&format=pubmed&size={MAX_ARTICLES}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return self.parse_pubmed_response(response.text)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching PubMed data: {e}")
            return []
    
    def parse_pubmed_response(self, html_content):
        """Parse PubMed HTML response to extract article information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = []
        
        # Find the pre tag containing the PubMed data
        pre_tag = soup.find('pre', class_='search-results-chunk')
        if not pre_tag:
            logger.warning("No search results found in response")
            return articles
        
        content = pre_tag.get_text()
        logger.info(f"Found pre tag with content length: {len(content)}")
        
        # Split by PMID entries
        entries = content.split('PMID- ')
        logger.info(f"Found {len(entries)-1} PMID entries to parse")
        
        for entry in entries[1:]:  # Skip first empty entry
            try:
                lines = entry.strip().split('\n')
                
                # The first line should contain the PMID (without the 'PMID- ' prefix)
                pmid = lines[0].strip() if lines else None
                date = None
                title = None
                abstract = None
                doi = None
                
                for i, line in enumerate(lines[1:], 1):  # Start from second line
                    line = line.strip()
                    if line.startswith('DP  - '):
                        date = line.replace('DP  - ', '').strip()
                    elif line.startswith('TI  - '):
                        title = line.replace('TI  - ', '').strip()
                        # Handle multi-line titles - continue until we hit LID
                        title_lines = [title]
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            # Stop when we hit LID section
                            if next_line.strip().startswith('LID -'):
                                break
                            # Continue if line starts with spaces (continuation of title)
                            # Check for 6 or more spaces at the beginning
                            elif next_line.startswith('      '):
                                title_lines.append(next_line.strip())
                            # If we hit any other section, stop
                            elif any(next_line.strip().startswith(prefix) for prefix in ['AB  -', 'CI  -', 'FAU -', 'AU  -', 'AD  -', 'LA  -', 'PT  -', 'DEP -', 'PL  -', 'TA  -', 'JT  -', 'JID -', 'SB  -', 'MH  -', 'RN  -', 'PMC -', 'OTO -', 'OT  -', 'COIS-', 'EDAT-', 'MHDA-', 'PMCR-', 'CRDT-', 'PHST-', 'AID -', 'PST -', 'SO  -']):
                                break
                        title = ' '.join(title_lines)
                    elif line.startswith('AB  - '):
                        abstract = line.replace('AB  - ', '').strip()
                        # Handle multi-line abstracts - continue until we hit CI
                        abstract_lines = [abstract]
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            # Stop when we hit CI section
                            if next_line.strip().startswith('CI  -'):
                                break
                            # Continue if line starts with spaces (continuation of abstract)
                            # Check for 6 or more spaces at the beginning
                            elif next_line.startswith('      '):
                                abstract_lines.append(next_line.strip())
                            # If we hit any other section, stop
                            elif any(next_line.strip().startswith(prefix) for prefix in ['FAU -', 'AU  -', 'AD  -', 'LA  -', 'PT  -', 'DEP -', 'PL  -', 'TA  -', 'JT  -', 'JID -', 'SB  -', 'MH  -', 'RN  -', 'PMC -', 'OTO -', 'OT  -', 'COIS-', 'EDAT-', 'MHDA-', 'PMCR-', 'CRDT-', 'PHST-', 'AID -', 'PST -', 'SO  -']):
                                break
                        abstract = ' '.join(abstract_lines)
                    elif line.startswith('LID - '):
                        doi = line.replace('LID - ', '').strip()
                        # Clean DOI by removing any extra text like [doi] or other suffixes
                        if ' ' in doi:
                            doi = doi.split(' ')[0]  # Take only the first part before any space
                
                if pmid and date and title:
                    articles.append({
                        'pmid': pmid,
                        'date': date,
                        'title': title,
                        'abstract': abstract,
                        'doi': doi
                    })
                    logger.info(f"Parsed article: PMID={pmid}, Date={date}, Title={title[:50]}...")
                else:
                    logger.warning(f"Incomplete article data: PMID={pmid}, Date={date}, Title={title}")
                    
            except Exception as e:
                logger.warning(f"Error parsing article entry: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(articles)} articles from PubMed response")
        return articles
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🔬 CPT Pharmacometrics & Systems Pharmacology Bot\n\n"
            "Available Commands:\n"
            "• /articles - Get articles from the past month\n"
            "• /custom - Get articles from custom date range\n"
            "• /abstract <PMID> - Get abstract for specific article\n\n"
            "Example: /abstract 41014576",
            disable_web_page_preview=True
        )
    
    async def articles_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /articles command - quick past month update"""
        await update.message.reply_text("🔄 Fetching articles from the past month...")
        
        try:
            articles = self.scrape_pubmed()
            
            if not articles:
                await update.message.reply_text("❌ No articles found for the past month.")
                return
            
            # Split articles into chunks to avoid Telegram's 4096 character limit
            chunk_size = 5  # Number of articles per message
            total_articles = len(articles)
            
            for chunk_start in range(0, total_articles, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_articles)
                chunk_articles = articles[chunk_start:chunk_end]
                
                if chunk_start == 0:
                    response = f"📚 CPT Pharmacometrics & Systems Pharmacology Articles (Past Month)\n\n"
                else:
                    response = ""
                
                for i, article in enumerate(chunk_articles, chunk_start + 1):
                    response += f"{i}. PMID: {article['pmid']}\n"
                    response += f"Date: {article['date']}\n"
                    response += f"Title: _{article['title']}_\n"
                    response += f"Abstract: /abstract {article['pmid']}\n\n"
                
                await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
                
        except Exception as e:
            logger.error(f"Error in articles command: {e}")
            await update.message.reply_text("❌ Error fetching articles. Please try again later.")
    
    async def custom_range_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /custom command for custom date range"""
        await update.message.reply_text(
            "📅 Custom Date Range\n\n"
            "Please send the date range in the format:\n"
            "YYYY-MM-DD to YYYY-MM-DD\n\n"
            "Example: 2025-01-01 to 2025-01-31",
            disable_web_page_preview=True
        )
    
    async def abstract_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /abstract command to get abstract for a specific PMID"""
        if not context.args:
            await update.message.reply_text(
                "📄 Abstract Lookup\n\n"
                "Please provide a PMID to get the abstract.\n"
                "Usage: /abstract <PMID>\n\n"
                "Example: /abstract 41014576",
                disable_web_page_preview=True
            )
            return
        
        pmid = context.args[0].strip()
        await update.message.reply_text(f"🔄 Fetching abstract for PMID {pmid}...")
        
        try:
            # Get articles from the past month to find the specific PMID
            articles = self.scrape_pubmed()
            
            # Find the article with the matching PMID
            target_article = None
            for article in articles:
                if article['pmid'] == pmid:
                    target_article = article
                    break
            
            if not target_article:
                await update.message.reply_text(f"❌ Article with PMID {pmid} not found in recent articles.")
                return
            
            if not target_article.get('abstract'):
                await update.message.reply_text(f"❌ No abstract available for PMID {pmid}.")
                return
            
            # Format the response
            response = f"📄 **Abstract for PMID {pmid}**\n\n"
            response += f"**Title:** _{target_article['title']}_\n\n"
            response += f"**Date:** {target_article['date']}\n\n"
            response += f"**Abstract:**\n{target_article['abstract']}\n\n"
            response += f"🔗 [View on PubMed](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
            
            # Add Wiley link if DOI is available
            if target_article.get('doi'):
                wiley_link = f"https://ascpt.onlinelibrary.wiley.com/doi/{target_article['doi']}"
                response += f"\n🔗 [View Full Article]({wiley_link})"
            
            await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error in abstract command: {e}")
            await update.message.reply_text("❌ Error fetching abstract. Please try again later.")

    async def handle_custom_range(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle custom date range input"""
        text = update.message.text.strip()
        
        if " to " not in text:
            await update.message.reply_text(
                "❌ Invalid format. Please use: YYYY-MM-DD to YYYY-MM-DD\n"
                "Example: 2025-01-01 to 2025-01-31",
                disable_web_page_preview=True
            )
            return
        
        try:
            start_date, end_date = text.split(" to ")
            start_date = start_date.strip()
            end_date = end_date.strip()
            
            # Validate date format
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
            
            await update.message.reply_text(f"🔄 Fetching articles from {start_date} to {end_date}...")
            
            articles = self.scrape_pubmed(start_date, end_date)
            
            if not articles:
                await update.message.reply_text(f"❌ No articles found for the period {start_date} to {end_date}.")
                return
            
            # Split articles into chunks to avoid Telegram's 4096 character limit
            chunk_size = 5  # Number of articles per message
            total_articles = len(articles)
            
            for chunk_start in range(0, total_articles, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_articles)
                chunk_articles = articles[chunk_start:chunk_end]
                
                if chunk_start == 0:
                    response = f"📚 CPT Pharmacometrics & Systems Pharmacology Articles ({start_date} to {end_date})\n\n"
                else:
                    response = ""
                
                for i, article in enumerate(chunk_articles, chunk_start + 1):
                    response += f"{i}. PMID: {article['pmid']}\n"
                    response += f"Date: {article['date']}\n"
                    response += f"Title: _{article['title']}_\n"
                    response += f"Abstract: /abstract {article['pmid']}\n\n"
                
                await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
                
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Please use: YYYY-MM-DD to YYYY-MM-DD\n"
                "Example: 2025-01-01 to 2025-01-31",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error in custom range: {e}")
            await update.message.reply_text("❌ Error fetching articles. Please try again later.")

# Create Flask app for healthcheck
app = Flask(__name__)

@app.route('/')
def healthcheck():
    """Healthcheck endpoint for Railway"""
    return "CPT PSP Bot is running!", 200

def run_flask():
    """Run Flask app in a separate thread"""
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

def main():
    """Main function to run the bot"""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    # Start Flask server in a separate thread for healthcheck
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Create bot instance
    bot = PubMedBot(token)
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("articles", bot.articles_command))
    application.add_handler(CommandHandler("custom", bot.custom_range_command))
    application.add_handler(CommandHandler("abstract", bot.abstract_command))
    
    # Add message handler for custom date range input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_custom_range))
    
    # Start the bot
    logger.info("Starting CPT PSP Bot...")
    
    # Handle graceful shutdown
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == '__main__':
    main()