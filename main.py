import os
import tempfile
import requests
import asyncio
import threading
import logging
from mega import Mega
from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", "0"))  # Must be set!
WELCOME_ANIMATION_URL = os.getenv(
    "WELCOME_ANIMATION_URL", 
    "https://i.imgur.com/7V8dZ0l.gif"  # Professional bot welcome animation
)
DOCUMENT_AS_FILE = os.getenv("DOCUMENT_AS_FILE", "True").lower() == "true"
USE_THUMBNAIL = os.getenv("USE_THUMBNAIL", "True").lower() == "true"

# In-memory admin storage
ADMINS = {MAIN_ADMIN_ID}  # Only main admin can manage other admins
ADDITIONAL_ADMINS = set()  # Regular admins who can use the bot

def create_progress_bar(percentage, width=20):
    """Create a visually appealing progress bar with stars"""
    filled = int(width * percentage / 100)
    empty = width - filled
    progress = "⭐" * filled + "☆" * empty
    return f"[{progress}] {percentage}%"

async def send_alive_notification(application: Application):
    """Send alive notification to all admins when bot starts"""
    if not ADMINS:
        logger.warning("No admins configured for alive notification")
        return
    
    message = (
        "Hey Arsynox Bot is Alive 🥳\n\n"
        "✅ Bot is ready to process Mega links\n"
        "✅ Admin management active (MAIN ADMIN ONLY)\n"
        f"👑 Main Admin: {MAIN_ADMIN_ID}\n"
        f"👥 Regular Admins: {', '.join(map(str, ADDITIONAL_ADMINS)) if ADDITIONAL_ADMINS else 'None'}"
    )
    
    for admin_id in ADMINS:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text=message,
                disable_notification=True
            )
            logger.info(f"Sent alive notification to admin {admin_id}")
        except Exception as e:
            logger.error(f"Failed to send alive message to {admin_id}: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with animation"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot")
    
    # Create caption based on user status
    if user_id not in ADMINS:
        caption = (
            "🔒 <b>Access Restricted</b>\n\n"
            "You need to be an admin to use this bot.\n"
            "Contact the main admin for access:\n"
            f"<code>{MAIN_ADMIN_ID}</code>\n\n"
            "⚠️ Only the main admin can grant access"
        )
    else:
        caption = (
            "🚀 <b>Mega to Gofile Uploader Bot</b>\n\n"
            "Send <code>/gofile [mega_link]</code> to upload files\n\n"
            "🔐 <b>Admin Management (MAIN ADMIN ONLY)</b>\n"
            "• <code>/admin [user_id]</code> - Add regular admin\n"
            "• <code>/remove [user_id]</code> - Remove regular admin\n\n"
            f"👑 <b>Main Admin</b>: <code>{MAIN_ADMIN_ID}</code>\n"
            f"👥 <b>Regular Admins</b>: {', '.join(map(str, ADDITIONAL_ADMINS)) if ADDITIONAL_ADMINS else 'None'}"
        )
    
    try:
        # Send animation with caption
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=WELCOME_ANIMATION_URL,
            caption=caption,
            parse_mode=constants.ParseMode.HTML,
            disable_notification=True
        )
        logger.info(f"Sent welcome animation to user {user_id}")
    except Exception as e:
        logger.error(f"Animation error for user {user_id}: {str(e)}")
        # Fallback to text message if animation fails
        await update.message.reply_text(
            caption.replace("<b>", "**").replace("</b>", "**"),
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new regular admin (MAIN ADMIN ONLY)"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} attempting to add admin")
    
    # ONLY main admin can add admins
    if user_id != MAIN_ADMIN_ID:
        await update.message.reply_text(
            "❌ <b>ACCESS DENIED!</b>\n\n"
            "Only the main admin can add new admins.\n"
            f"Main Admin ID: <code>{MAIN_ADMIN_ID}</code>",
            parse_mode=constants.ParseMode.HTML
        )
        logger.warning(f"User {user_id} (not main admin) attempted to add admin")
        return
    
    if not context.args:
        await update.message.reply_text(
            "UsageId: <code>/admin <user_id></code>",
            parse_mode=constants.ParseMode.HTML
        )
        return
    
    try:
        new_admin_id = int(context.args[0])
        logger.info(f"Main admin {user_id} attempting to add {new_admin_id} as admin")
        
        if new_admin_id == MAIN_ADMIN_ID:
            await update.message.reply_text("👑 You're already the main admin!")
            return
            
        if new_admin_id in ADDITIONAL_ADMINS:
            await update.message.reply_text(
                f"⚠️ User <code>{new_admin_id}</code> is already a regular admin!",
                parse_mode=constants.ParseMode.HTML
            )
            return
        
        ADDITIONAL_ADMINS.add(new_admin_id)
        ADMINS.add(new_admin_id)  # Add to full admin list for bot access
        
        await update.message.reply_text(
            f"✅ Added regular admin: <code>{new_admin_id}</code>\n\n"
            f"👑 Main Admin: <code>{MAIN_ADMIN_ID}</code>\n"
            f"👥 Regular Admins: {', '.join(map(str, ADDITIONAL_ADMINS))}",
            parse_mode=constants.ParseMode.HTML
        )
        logger.info(f"Main admin {user_id} added {new_admin_id} as regular admin")
    
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID! Must be a number.",
            parse_mode=constants.ParseMode.HTML
        )
        logger.warning(f"Main admin {user_id} provided invalid user ID")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a regular admin (MAIN ADMIN ONLY)"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} attempting to remove admin")
    
    # ONLY main admin can remove admins
    if user_id != MAIN_ADMIN_ID:
        await update.message.reply_text(
            "❌ <b>ACCESS DENIED!</b>\n\n"
            "Only the main admin can remove admins.\n"
            f"Main Admin ID: <code>{MAIN_ADMIN_ID}</code>",
            parse_mode=constants.ParseMode.HTML
        )
        logger.warning(f"User {user_id} (not main admin) attempted to remove admin")
        return
    
    if not context.args:
        await update.message.reply_text(
            "UsageId: <code>/remove <user_id></code>",
            parse_mode=constants.ParseMode.HTML
        )
        return
    
    try:
        target_id = int(context.args[0])
        logger.info(f"Main admin {user_id} attempting to remove {target_id} as admin")
        
        if target_id == MAIN_ADMIN_ID:
            await update.message.reply_text("👑 Cannot remove the main admin!")
            return
        
        if target_id not in ADDITIONAL_ADMINS:
            await update.message.reply_text(
                f"⚠️ User <code>{target_id}</code> is not a regular admin!",
                parse_mode=constants.ParseMode.HTML
            )
            return
        
        ADDITIONAL_ADMINS.remove(target_id)
        ADMINS.remove(target_id)  # Remove from full admin list
        
        await update.message.reply_text(
            f"🗑️ Removed regular admin: <code>{target_id}</code>\n\n"
            f"👑 Main Admin: <code>{MAIN_ADMIN_ID}</code>\n"
            f"👥 Regular Admins: {', '.join(map(str, ADDITIONAL_ADMINS)) if ADDITIONAL_ADMINS else 'None'}",
            parse_mode=constants.ParseMode.HTML
        )
        logger.info(f"Main admin {user_id} removed {target_id} as regular admin")
    
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID! Must be a number.",
            parse_mode=constants.ParseMode.HTML
        )
        logger.warning(f"Main admin {user_id} provided invalid user ID")

async def handle_gofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process Mega links and upload to Gofile with progress bars"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} initiated /gofile command")
    
    if user_id not in ADMINS:
        await update.message.reply_text(
            "❌ <b>Access denied!</b>\n\n"
            "You need to be an admin to use this bot.\n"
            f"Contact main admin: <code>{MAIN_ADMIN_ID}</code>",
            parse_mode=constants.ParseMode.HTML
        )
        logger.warning(f"Non-admin user {user_id} attempted to use /gofile")
        return
    
    if not context.args:
        await update.message.reply_text(
            "UsageId: <code>/gofile <mega_link></code>",
            parse_mode=constants.ParseMode.HTML
        )
        return
    
    mega_link = " ".join(context.args)  # Handle links with spaces
    logger.info(f"User {user_id} provided Mega link: {mega_link}")
    
    if not (mega_link.startswith("https://mega.nz/") or mega_link.startswith("https://mega.io/")):
        await update.message.reply_text(
            "❌ <b>Invalid Mega link!</b>\n\n"
            "Must start with <code>https://mega.nz/</code> or <code>https://mega.io/</code>",
            parse_mode=constants.ParseMode.HTML
        )
        logger.warning(f"User {user_id} provided invalid Mega link format")
        return

    try:
        # Initial status message
        status_msg = await update.message.reply_text(
            "📥 <b>Starting download from Mega...</b>\n"
            "▰▰▰▰▰▰▰▰▰▰ 0%",
            parse_mode=constants.ParseMode.HTML
        )
        logger.info(f"Started processing for user {user_id}")
        
        # Download from Mega with progress
        mega = Mega()
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Get file info to show progress
            logger.info("Fetching file info from Mega...")
            file_info = mega.get_public_file(mega_link)
            total_size = file_info['s']
            file_name = file_info['at']['n']
            logger.info(f"File info - Name: {file_name}, Size: {total_size} bytes")
            
            # Start download in background thread
            downloaded = 0
            download_complete = asyncio.Event()
            lock = asyncio.Lock()
            
            def download_thread():
                nonlocal downloaded
                try:
                    # Download file and track progress
                    logger.info("Starting download from Mega...")
                    mega.download_url(mega_link, dest_path=temp_dir)
                    logger.info("Download completed successfully")
                    download_complete.set()
                except Exception as e:
                    logger.error(f"Download failed: {str(e)}")
                    with lock:
                        downloaded = -1  # Error state
                    download_complete.set()
            
            # Start download thread
            download_task = threading.Thread(target=download_thread)
            download_task.daemon = True
            download_task.start()
            logger.info("Download thread started")
            
            # Track download progress
            last_update = 0
            while not download_complete.is_set():
                await asyncio.sleep(1)
                current_size = sum(os.path.getsize(os.path.join(temp_dir, f)) 
                                  for f in os.listdir(temp_dir) 
                                  if os.path.isfile(os.path.join(temp_dir, f)))
                
                async with lock:
                    downloaded = current_size
                
                if total_size > 0:
                    progress = min(100, int(downloaded / total_size * 100))
                    
                    # Update only when progress changes significantly
                    if progress != last_update and progress % 5 == 0:
                        progress_bar = create_progress_bar(progress)
                        await status_msg.edit_text(
                            f"📥 <b>Downloading from Mega:</b> {file_name}\n"
                            f"{progress_bar}",
                            parse_mode=constants.ParseMode.HTML
                        )
                        logger.info(f"Download progress: {progress}%")
                        last_update = progress
            
            # Final download status
            if downloaded == -1:
                logger.error("Download failed with error state")
                raise Exception("Download failed")
                
            downloaded_path = os.path.join(temp_dir, file_name)
            logger.info(f"File downloaded to: {downloaded_path}")
            
            # Upload to Gofile with progress
            await status_msg.edit_text(
                "⏫ <b>Starting upload to Gofile...</b>\n"
                "▰▰▰▰▰▰▰▰▰▰ 0%",
                parse_mode=constants.ParseMode.HTML
            )
            logger.info("Starting upload to Gofile...")
            
            # Get upload server
            logger.info("Fetching Gofile server info...")
            server_resp = requests.get("https://api.gofile.io/servers", timeout=10)
            server_resp.raise_for_status()
            server = server_resp.json()["data"]["servers"][0]["name"]
            logger.info(f"Using Gofile server: {server}")
            
            # Prepare upload with progress tracking
            upload_url = f"https://{server}.gofile.io/uploadFile"
            file_size = os.path.getsize(downloaded_path)
            uploaded = 0
            upload_complete = asyncio.Event()
            
            # Custom file-like object to track upload progress
            class ProgressFile:
                def __init__(self, file):
                    self.file = file
                    self.uploaded = 0
                
                def read(self, size=-1):
                    nonlocal uploaded
                    chunk = self.file.read(size)
                    if chunk:
                        self.uploaded += len(chunk)
                        uploaded = self.uploaded
                    return chunk
            
            # Start upload in background thread
            def upload_thread():
                try:
                    with open(downloaded_path, 'rb') as f:
                        logger.info("Starting file upload...")
                        progress_file = ProgressFile(f)
                        files = {'file': (file_name, progress_file)}
                        response = requests.post(
                            upload_url,
                            files=files,
                            timeout=300
                        )
                        response.raise_for_status()
                        logger.info("Upload completed successfully")
                        return response.json()
                except Exception as e:
                    logger.error(f"Upload failed: {str(e)}")
                    with lock:
                        uploaded = -1  # Error state
                    upload_complete.set()
                    raise e
            
            # Start upload thread
            upload_task = threading.Thread(target=upload_thread)
            upload_task.daemon = True
            upload_task.start()
            logger.info("Upload thread started")
            
            # Track upload progress
            last_update = 0
            while not upload_complete.is_set():
                await asyncio.sleep(1)
                async with lock:
                    current_uploaded = uploaded
                
                if file_size > 0:
                    progress = min(100, int(current_uploaded / file_size * 100))
                    
                    # Update only when progress changes significantly
                    if progress != last_update and progress % 5 == 0:
                        progress_bar = create_progress_bar(progress)
                        await status_msg.edit_text(
                            f"⏫ <b>Uploading to Gofile:</b> {file_name}\n"
                            f"{progress_bar}",
                            parse_mode=constants.ParseMode.HTML
                        )
                        logger.info(f"Upload progress: {progress}%")
                        last_update = progress
            
            # Get upload result
            logger.info("Fetching upload result...")
            upload_resp = upload_task.result()
            if upload_resp["status"] != "ok":
                logger.error(f"Gofile API error: {upload_resp.get('data', {}).get('message', 'Unknown error')}")
                raise Exception(f"Gofile error: {upload_resp.get('data', {}).get('message', 'Unknown error')}")
            
            # Send success message
            download_url = upload_resp["data"]["downloadPage"]
            await status_msg.edit_text(
                f"✅ <b>Upload successful!</b>\n\n"
                f"📁 <b>File:</b> <code>{file_name}</code>\n"
                f"🔗 <b>Download:</b> <a href='{download_url}'>Link</a>\n\n"
                f"⭐ <b>Thank you for using Arsynox Bot!</b>",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=False
            )
            logger.info(f"Upload completed successfully. Download URL: {download_url}")
    
    except Exception as e:
        logger.exception(f"Error processing request: {str(e)}")
        try:
            await status_msg.edit_text(
                f"❌ <b>Error:</b> <code>{str(e)}</code>",
                parse_mode=constants.ParseMode.HTML
            )
        except:
            await update.message.reply_text(
                f"❌ <b>Error:</b> <code>{str(e)}</code>",
                parse_mode=constants.ParseMode.HTML
            )

def main():
    """Initialize and run the bot"""
    logger.info("Starting bot initialization...")
    
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN environment variable not set!")
        raise RuntimeError("BOT_TOKEN environment variable not set!")
    
    if MAIN_ADMIN_ID == 0:
        logger.critical("MAIN_ADMIN_ID environment variable not set or invalid!")
        raise RuntimeError("MAIN_ADMIN_ID environment variable not set or invalid!")
    
    logger.info(f"Main Admin ID: {MAIN_ADMIN_ID}")
    logger.info(f"Welcome Animation URL: {WELCOME_ANIMATION_URL}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", add_admin))
    app.add_handler(CommandHandler("remove", remove_admin))
    app.add_handler(CommandHandler("gofile", handle_gofile))
    app.add_handler(MessageHandler(filters.COMMAND, start))
    
    # Send alive notification to admins
    logger.info("Bot is starting up...")
    app.post_init = lambda app: send_alive_notification(app)
    
    logger.info("Starting bot polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
