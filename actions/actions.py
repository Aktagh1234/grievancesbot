from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict
from googletrans import Translator
from pydantic import BaseSettings
import smtplib
import logging
from datetime import datetime
from hashlib import blake2b
import os
import yaml
from pathlib import Path

# --------------------------
# Configuration and Constants
# --------------------------

class Settings(BaseSettings):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")

    class SettingsConfig:
        env_file = ".env"

settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi",
    "or": "Odia", "ml": "Malayalam", "as": "Assamese", "ne": "Nepali"
}

CONFIG_DIR = Path(__file__).parent / "config"
try:
    with open(CONFIG_DIR / "dept_emails.yml") as f:
        DEPT_EMAILS = yaml.safe_load(f)
except Exception as e:
    logger.error(f"Failed to load department emails config: {e}")
    DEPT_EMAILS = {}

# --------------------------
# Core Services
# --------------------------

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        self.cache = {}

    def translate(self, text: str, dest_lang: str, tracker: Optional[Tracker] = None) -> str:
        if dest_lang == "en" or not text:
            return text
        key = f"{dest_lang}:{text}"
        if key in self.cache:
            return self.cache[key]
        try:
            if tracker and "{" in text:
                text = text.format(
                    state=tracker.get_slot("state") or "",
                    area=tracker.get_slot("area") or "",
                    department=tracker.get_slot("department") or "",
                    language=tracker.get_slot("language") or "en"
                )
            result = self.translator.translate(text, dest=dest_lang).text
            self.cache[key] = result
            return result
        except Exception as e:
            logger.error(f"Translation error ({dest_lang}): {e}")
            return text

class EmailService:
    @staticmethod
    def send_email(recipient: str, subject: str, body: str) -> bool:
        try:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_username, recipient, f"Subject: {subject}\n\n{body}")
            return True
        except Exception as e:
            logger.error(f"Email sending failed to {recipient}: {e}")
            return False

# --------------------------
# Utilities
# --------------------------

def generate_complaint_id(state: str, department: str) -> str:
    h = blake2b(digest_size=4)
    h.update(f"{state}{department}{datetime.now()}".encode())
    return f"{state[:3].upper()}-{department[:3].upper()}-{h.hexdigest().upper()}"

def validate_required_slots(tracker: Tracker) -> None:
    for slot in ["state", "area", "department", "complaint_details"]:
        if not tracker.get_slot(slot):
            raise ValueError(f"Missing required slot: {slot}")

def get_localized_examples(lang: str) -> str:
    examples = {
        "en": "Water, Electricity, Land",
        "hi": "\u091c\u0932, \u092c\u093f\u091c\u0932\u0940, \u092d\u0942\u092e\u093f",
        "mr": "\u092a\u093e\u0923\u0940, \u0935\u0940\u091c, \u091c\u092e\u0940\u0928",
    }
    return examples.get(lang, examples["en"])

# --------------------------
# Custom Actions
# --------------------------

class ActionDetectLanguage(Action):
    def name(self) -> Text:
        return "action_detect_language"

    async def run(self, dispatcher, tracker, domain):
        user_text = tracker.latest_message.get("text", "")
        lang = "en"
        try:
            detected = Translator().detect(user_text).lang
            lang = detected if detected in SUPPORTED_LANGUAGES else "en"
        except Exception as e:
            logger.error(f"Language detection error: {e}")
        return [SlotSet("language", lang)]

class ActionGenerateDraft(Action):
    def name(self) -> Text:
        return "action_generate_draft"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        logger.info("ActionGenerateDraft triggered!")  # Debug log
        try:
            logger.info(f"Current slots: state={tracker.get_slot('state')}, area={tracker.get_slot('area')}")  # Debug log
            validate_required_slots(tracker)
            lang = tracker.get_slot("language") or "en"
            ts = TranslationService()
            email_text = (
                "Subject: Complaint about {department}\n\n"
                "Dear Officer,\n\n"
                "I want to report an issue regarding {department} in {area}, {state}.\n\n"
                "Details:\n{complaint}\n\n"
                "Please address this matter promptly.\n\nRegards,\nConcerned Citizen"
            ).format(
                department=tracker.get_slot("department"),
                area=tracker.get_slot("area"),
                state=tracker.get_slot("state"),
                complaint=tracker.get_slot("complaint_details")
            )
            logger.info(f"Generated draft: {email_text}")  # Debug log
            dispatcher.utter_message(text=ts.translate("Here is your draft email:\n\n" + email_text, lang, tracker))
        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            dispatcher.utter_message(text="Sorry, I couldn't generate the draft. Please try again.")
        return []

class ActionSubmitComplaint(Action):
    def name(self) -> Text:
        return "action_submit_complaint"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        try:
            validate_required_slots(tracker)
            state = (tracker.get_slot("state") or "").lower()
            dept = (tracker.get_slot("department") or "").lower()
            area = tracker.get_slot("area")
            complaint = tracker.get_slot("complaint_details")
            sender = tracker.sender_id

            complaint_id = generate_complaint_id(state, dept)
            recipient = DEPT_EMAILS.get(state, {}).get(dept)
            if not recipient:
                raise ValueError(f"No email for {dept} in {state}")

            now = datetime.now().strftime("%d-%m-%Y %H:%M")
            subject = f"Complaint ID: {complaint_id} - {dept} Issue in {area}, {state}"
            body = (
                f"Complaint ID: {complaint_id}\nDate: {now}\nFrom: {sender}\n\n"
                f"Department: {dept}\nLocation: {area}, {state}\n\nDetails:\n{complaint}\n\n"
                "Expected Resolution Time: 3-5 working days\n\n---\nAuto-generated from Central Grievance Portal"
            )

            confirmation_subject = f"Complaint Registered: {complaint_id}"
            confirmation_body = (
                f"Your complaint has been registered.\n\nID: {complaint_id}\nDepartment: {dept}\n"
                f"Location: {area}, {state}\n\nDetails:\n{complaint}\n\nExpected Resolution: 3-5 working days"
            )

            if not EmailService.send_email(recipient, subject, body):
                raise Exception("Failed to send to department")
            if not EmailService.send_email(sender, confirmation_subject, confirmation_body):
                raise Exception("Failed to send confirmation")

            msg = ts.translate(
                f"\u2705 Complaint registered successfully! ID: {complaint_id}\n• Department: {dept}\n"
                f"• Location: {area}, {state}\nA confirmation has been sent to your email.",
                lang
            )
            dispatcher.utter_message(text=msg)
        except Exception as e:
            logger.error(f"Complaint submission failed: {e}")
            error_msg = ts.translate(f"\u26a0\ufe0f Failed to submit complaint: {str(e)}", lang)
            dispatcher.utter_message(text=error_msg)
        return []

class ActionAskDepartment(Action):
    def name(self) -> Text:
        return "action_ask_department"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        examples = get_localized_examples(lang)
        question = TranslationService().translate(
            "Please select department (e.g. {examples}):", lang, tracker
        ).format(examples=examples)
        dispatcher.utter_message(text=question)
        return []