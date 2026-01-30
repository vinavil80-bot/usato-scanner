import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"

def send_test_mail(content):
    user = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    msg = MIMEText(content)
    msg['Subject'] = "TEST SCANNER USATO"
    msg['From'] = user
    msg['To'] = user
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(user, password)
        server.send_message(msg)
        print("Mail di test inviata!")

# Proviamo a leggere solo la prima riga del CSV e cercare su Mercatopoli
try:
    df = pd.read_csv(CSV_URL)
    print(f"CSV letto correttamente. Righe trovate: {len(df)}")
    primo_oggetto = str(df.iloc[0, 0])
    print(f"Provo a cercare il primo oggetto: {primo_oggetto}")
    
    # Se il CSV viene letto, mandami una mail di conferma lettura
    send_test_mail(f"Il bot sta funzionando! Ho letto dal tuo CSV: {primo_oggetto}")
except Exception as e:
    print(f"ERRORE CRITICO: {e}")
