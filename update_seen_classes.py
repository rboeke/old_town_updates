import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from pathlib import Path
import smtplib
import os
from email.mime.text import MIMEText

url = "https://www.oldtownschool.org/classes/adults/ensemble/"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; ClassesListed/1.0)"
}

response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

rows = []

# each class block
class_blocks = soup.find_all("div", class_="content")

for block in class_blocks:

    # ---------- TITLE ----------
    h4 = block.find("h4")

    if h4:
        full_title = h4.get_text(" ", strip=True)

        if " with " in full_title:
            class_name = full_title.split(" with ")[0]
            teacher = full_title.split(" with ")[1]
        else:
            class_name = full_title
            teacher = None
    else:
        class_name = None
        teacher = None

    # ---------- PRICE ----------
    price_div = block.find("div", class_="price")

    price = (
        price_div.get_text(" ", strip=True)
        if price_div else None
    )

    # ---------- DATES ----------
    dates_div = block.find("div", class_="dates")

    dates = (
        dates_div.get_text(" ", strip=True)
        if dates_div else None
    )

    # ---------- TIMES ----------
    times_div = block.find("div", class_="times")

    times = (
        times_div.get_text(" ", strip=True)
        if times_div else None
    )

    # ---------- DESCRIPTION ----------
    panel_body = block.find("div", class_="panel-body")

    description = (
        panel_body.get_text(" ", strip=True)
        if panel_body else None
    )

    # ---------- INSTRUMENTS ----------
    panel_footer = block.find("div", class_="panel-footer")

    instruments = None

    if panel_footer:
        footer_text = panel_footer.get_text(" ", strip=True)

        if "Instruments:" in footer_text:
            instruments = footer_text.replace(
                "Instruments:",
                ""
            ).strip()

    # ---------- REGISTER LINK ----------
    register_btn = block.find("a", class_="courselink")

    register_link = (
        register_btn["href"]
        if register_btn else None
    )

    # ---------- SAVE ROW ----------
    rows.append({
        "class_name": class_name,
        "teacher": teacher,
        "price": price,
        "dates": dates,
        "times": times,
        "description": description,
        "instruments": instruments,
        "register_link": register_link
    })

# ---------- DATAFRAME ----------
df = pd.DataFrame(rows).dropna().drop_duplicates()

def get_classes():
    classes = df[["class_name", "dates"]].drop_duplicates()
    return classes

SEEN_FILE = "seen_classes.json"

def load_seen():

    if not Path(SEEN_FILE).exists():
        return set()

    try:
        with open(SEEN_FILE, "r") as f:
            data = json.load(f)

        return set(tuple(x) for x in data)

    except (json.JSONDecodeError, ValueError):

        # corrupted or empty file → reset
        return set()

def save_seen(seen):

    with open(SEEN_FILE, "w") as f:
        json.dump([list(x) for x in seen], f)

def send_email(new_classes):

    if not new_classes:
        return

    body = "New classes found:\n\n"

    for name, dates in new_classes:
        body += f"{name}\n{dates}\n\n"

    msg = MIMEText(body)
    msg["Subject"] = "New Class Alert"
    msg["From"] = os.environ["EMAIL_USER"]
    msg["To"] = os.environ["EMAIL_USER"]

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    server.login(
        os.environ["EMAIL_USER"],
        os.environ["EMAIL_PASS"]
    )

    server.send_message(msg)
    server.quit()

classes = get_classes()

seen = load_seen()

new_classes = []

for _, row in classes.iterrows():

    key = (row["class_name"], row["dates"])

    if key not in seen:
        new_classes.append(key)

if new_classes:

    print("NEW CLASS FOUND:")

    for class_name, dates in new_classes:
        print("-", class_name)
        print(" ", dates)

    send_email(new_classes)

    seen.update(new_classes)
    save_seen(seen)

else:
    print("No new classes.")

