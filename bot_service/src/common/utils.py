## Only put resusable functions here

from common.base import Main

from functools import wraps
import time

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import os
import smtplib

from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())


def timeit(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)  # Await the async function
        end_time = time.time()
        Main.logger().critical('\x1b[6;30;42m' + f"Time taken by {func.__name__}: {end_time - start_time} seconds" + '\x1b[0m')
        return result
    return wrapper


def send_alert(
    message="Message to send",
    subject="Alert",
    file_to_send=None,
    filename="alert_log.txt",
    mail_to="",
    mail_cc="",
):
    """Send an email alert with an attachment if any

    Args:
        message (str): Message to be sent via email
        subject (str): Subject of the email. Defaults to Alert
        file_to_send (str, optional): Path to file to send via email attachment. Defaults to None.
        filename (str, optional): File name of the attachment. Defaults to 'alert_log.txt'.
    """

    SMTP_HOST = os.getenv("SMTP_HOST", None)
    SMTP_TLS_PORT = os.getenv("SMTP_TLS_PORT", 587)
    SMTP_MAIL_FROM = os.getenv("SMTP_MAIL_FROM", None)
    SMTP_MAIL_TO = os.getenv("SMTP_MAIL_TO", None)
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", None)
    SMTP_USER = os.getenv("SMTP_USER", None)

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SMTP_MAIL_FROM

    if mail_to:
        SMTP_MAIL_TO = mail_to
    if mail_cc:
        msg["Cc"] = mail_cc

    # msg['To'] requires SMTP_MAIL_TO to be a string
    msg["To"] = SMTP_MAIL_TO
    msg.attach(MIMEText(message, "html"))

    if file_to_send:
        ctype, encoding = mimetypes.guess_type(file_to_send)
        if ctype is None or encoding is not None:
            ctype = "text/*"

        maintype, subtype = ctype.split("/", 1)

        if not "xlsx" in file_to_send:
            with open(file_to_send, encoding="utf-8") as fp:
                attachment = MIMEText(fp.read(), _subtype="subtype")
                # encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition", "attachment", filename=filename
                )
                msg.attach(attachment)
        else:
            with open(file_to_send, "rb") as fp:
                # attachment = MIMEText(fp.read(), _subtype='xlsx')
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(open(file_to_send, "rb").read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition", "attachment", filename=f"{filename}.xlsx"
                )
                msg.attach(attachment)

    with smtplib.SMTP(SMTP_HOST, SMTP_TLS_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(SMTP_USER, SMTP_PASSWORD)

        # sendmail requires SMTP_MAIL_TO to be a list
        smtp.sendmail(SMTP_MAIL_FROM, SMTP_MAIL_TO.split(","), msg.as_string())