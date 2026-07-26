FROM python:3.12-bookworm

WORKDIR /app

# התקנת Zint וכלי מערכת בסיסיים
RUN apt-get update && apt-get install -y \
    zint \
    && rm -rf /var/lib/apt/lists/*

# התקנת ספריות Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# התקנת Chromium והתלויות שלו
RUN playwright install --with-deps chromium

# העתקת כל קבצי השרת
COPY . .

# הפעלת FastAPI
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]