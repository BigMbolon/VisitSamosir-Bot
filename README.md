# Visit Samosir Telegram Bot

Bot Telegram jasa layanan wisata di Pulau Samosir, Danau Toba.

## Fitur
1. Jasa Angkutan
2. Penginapan / Homestay
3. Rental Drone
4. Rental Musik Tradisional Batak
5. Catering
6. Rental Mobil

## Cara Menjalankan Lokal

```bash
git clone https://github.com/USERNAME/visit-samosir-bot.git
cd visit-samosir-bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # lalu isi BOT_TOKEN
python bot.py
