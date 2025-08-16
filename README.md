# Arsynox Mega to Gofile Uploader Bot

A Telegram bot that allows you to upload files from Mega.nz to Gofile.io with a user-friendly interface, admin management, and progress visualization.

## Features

- 🚀 Upload Mega.nz files to Gofile.io without login
- 👑 Strict admin hierarchy (only main admin can manage other admins)
- ⭐ Star-based progress bars for download and upload
- 🎥 Animated welcome message on `/start`
- 📱 Mobile-friendly interface with HTML formatting
- 🤖 Automatic "Bot is Alive" notification to admins
- 📝 Comprehensive logging for troubleshooting

## Setup Instructions

### 1. Create a Telegram Bot

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save the bot token you receive

### 2. Get Your Telegram User ID

1. Talk to [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your User ID (a number like 123456789)
3. Save this ID as it's your MAIN_ADMIN_ID

### 3. Deployment on Render.com

1. **Create a new Web Service** on [Render.com](https://render.com)
2. **Connect your GitHub repository** with the bot code
3. **Set environment variables**:
