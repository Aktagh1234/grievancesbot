from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Text, Dict, List, Optional, Tuple
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
import uuid

# --------------------------
# Configuration and Constants
# --------------------------

from dotenv import load_dotenv

# Load .env from the same directory as actions.py
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

class Settings(BaseSettings):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")


settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi",
    "or": "Odia", "ml": "Malayalam", "as": "Assamese", "ne": "Nepali"
}

CONFIG_DIR = Path(__file__).parent / "config"
with open(CONFIG_DIR / "dept_emails.yml") as f:
    DEPT_EMAILS = yaml.safe_load(f)

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
    def send_email(recipient: str, subject: str, body: str, reply_to: str = None) -> Tuple[bool, Optional[str]]:
        try:
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["Subject"] = str(subject)
            msg["From"] = str(settings.smtp_username)
            msg["To"] = str(recipient)
            if reply_to:
                msg["Reply-To"] = str(reply_to)
            msg.set_content(str(body))
            with smtplib.SMTP(str(settings.smtp_server), int(settings.smtp_port)) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            return (True, None)
        except Exception as e:
            error_msg = f"Email sending failed to {recipient}: {e}"
            logger.error(error_msg)
            return (False, str(e))

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

def normalize_department(dept: str) -> str:
    if not dept:
        return ""
    dept = dept.lower().strip()
    if "board" in dept:
        dept = dept.replace("board", "").strip()
    if "department" in dept:
        dept = dept.replace("department", "").strip()
    return dept

# --------------------------
# Custom Actions
# --------------------------

class ActionSetEmailSlot(Action):
    def name(self) -> Text:
        return "action_set_email_slot"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        # Get email from sender_id (which should be the email)
        user_email = tracker.sender_id
        logger.info(f"Setting email slot for user: {user_email}")
        
        # Only set if it looks like an email
        if user_email and '@' in user_email:
            return [SlotSet("email", user_email)]
        else:
            logger.warning(f"Invalid email format in sender_id: {user_email}")
            return []

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
        logger.info("✅ action_generate_draft TRIGGERED")

        # Validate required slots
        slots = {slot: tracker.get_slot(slot) for slot in ["state", "area", "department", "complaint_details", "email"]}
        logger.info(f"🎯 Slots received for draft:\n{slots}")

        missing = [s for s in ["state", "area", "department", "complaint_details"] if not slots.get(s)]
        if missing:
            msg = f"⚠️ Cannot generate draft. Missing: {', '.join(missing)}"
            logger.warning(msg)
            dispatcher.utter_message(text=msg)
            return []

        try:
            lang = tracker.get_slot("language") or "en"
            ts = TranslationService()

            email_text = (
                f"Subject: Grievance Submission Regarding the {normalize_department(slots['department'])} Department in {slots['area']}, {slots['state']}\n\n"
                f"Dear Sir/Madam,\n\n"
                f"I am writing to formally raise a concern regarding an issue related to the {normalize_department(slots['department'])} department in {slots['area']}, {slots['state']}.\n\n"
                f"Details of the issue:\n{slots['complaint_details']}\n\n"
                f"I kindly request that this matter be addressed at the earliest convenience.\n\n"
                f"Thank you for your attention to this issue.\n\n"
                f"Sincerely,\nA Concerned Citizen"
            )

            logger.info(f"📧 Draft Email:\n{email_text}")
            dispatcher.utter_message(text=ts.translate("Here is your draft email:\n\n" + email_text, lang, tracker))

        except Exception as e:
            logger.error(f"🚨 Error in draft generation: {e}")
            dispatcher.utter_message(text="Sorry, something went wrong while drafting your complaint.")
        return []

class ActionSubmitComplaint(Action):
    def name(self) -> Text:
        return "action_submit_complaint"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        complaint_id_val = None  # To hold the complaint ID

        try:
            validate_required_slots(tracker)
            state = (tracker.get_slot("state") or "").lower()
            dept = normalize_department(tracker.get_slot("department") or "")
            area = tracker.get_slot("area")
            complaint = tracker.get_slot("complaint_details")
            user_email = tracker.get_slot("email")

            if not user_email:
                error_msg = ts.translate("⚠️ Complaint submission failed!", lang)
                dispatcher.utter_message(text=error_msg)
                return []

            complaint_id = generate_complaint_id(state, dept)
            recipient = (
                DEPT_EMAILS.get(state, {}).get(dept) or
                DEPT_EMAILS.get("default", {}).get("default")
            )
            if not recipient:
                raise ValueError(f"No email for department '{dept}' in state '{state}'")

            now = datetime.now().strftime("%d-%m-%Y %H:%M")
            subject = f"Complaint ID: {complaint_id} - {dept} Issue in {area}, {state}"
            body = (
                f"Subject: Grievance Submission – {dept.capitalize()} Department\n\n"
                f"Dear Officer,\n\n"
                f"This is to inform you that a grievance has been submitted via the Central Grievance Portal.\n\n"
                f"🆔 Complaint ID: {complaint_id}\n📅 Date: {now}\n📍 Location: {area}, {state}\n👤 From: {user_email}\n\n"
                f"📝 Department Concerned: {dept.capitalize()}\n\n"
                f"📄 Complaint Details:\n{complaint}\n\n"
                f"---\nThis is an automated email from the Central Grievance Portal.\nPlease do not reply directly to this message."
            )

            # Send to department and capture the actual error
            sent_to_dept, error_dept = EmailService.send_email(recipient, subject, body, reply_to=user_email)
            if not sent_to_dept:
                # Display the real error in chat
                error_msg = ts.translate(f"⚠️ Failed to send email to the department. **Reason:** {error_dept}", lang)
                dispatcher.utter_message(text=error_msg)
                return [SlotSet("complaint_id", None)]

            confirmation_subject = f"Complaint Registered: {complaint_id}"
            confirmation_body = (
                f"Dear Citizen,\n\n"
                f"✅ Your complaint has been successfully registered with the Central Grievance Portal.\n\n"
                f"🆔 Complaint ID: {complaint_id}\n"
                f"📅 Date: {now}\n"
                f"📍 Location: {area}, {state}\n"
                f"🏢 Department: {dept.capitalize()}\n\n"
                f"📝 Complaint Details:\n{complaint}\n\n"
                f"⏳ Expected Resolution: Within 3–5 working days\n\n"
                f"Thank you for helping us improve public services.\n"
                f"For queries or updates, please keep this complaint ID handy.\n\n"
                f"Regards,\nCentral Grievance Cell"
            )

            # Send confirmation to user and capture the actual error
            sent_to_user, error_user = EmailService.send_email(user_email, confirmation_subject, confirmation_body)
            if not sent_to_user:
                # Display the real error in chat
                error_msg = ts.translate(f"⚠️ Complaint submitted, but failed to send confirmation to your email. **Reason:** {error_user}", lang)
                dispatcher.utter_message(text=error_msg)
                return [SlotSet("complaint_id", complaint_id)]

            # If both succeeded
            success_msg = ts.translate(
                f"✅ Complaint registered successfully! Your Complaint ID is **{complaint_id}**.", lang
            )
            dispatcher.utter_message(text=success_msg)
            return [SlotSet("complaint_id", complaint_id)]

        except Exception as e:
            logger.error(f"Error in ActionSubmitComplaint: {e}")
            error_msg = ts.translate(f"Sorry, a critical error occurred: {e}", lang)
            dispatcher.utter_message(text=error_msg)
            return [SlotSet("complaint_id", None)]

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

class ActionUtterGreet(Action):
    def name(self) -> Text:
        return "action_utter_greet"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        msg = ts.translate("Hello! I'm Upaay, your grievance assistant. How can I help you today?", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterAskState(Action):
    def name(self) -> Text:
        return "action_utter_ask_state"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        msg = ts.translate("Please tell me your state:", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterAskArea(Action):
    def name(self) -> Text:
        return "action_utter_ask_area"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        state = tracker.get_slot("state") or ""
        msg = ts.translate(f"Which area/city in {state} are you facing the issue?", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterAskDepartment(Action):
    def name(self) -> Text:
        return "action_utter_ask_department"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        msg = ts.translate("Select department of relevance (e.g. Water, Electricity, Land):", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterAskComplaintDetails(Action):
    def name(self) -> Text:
        return "action_utter_ask_complaint_details"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        msg = ts.translate("Describe your complaint in detail (location, duration, and any relevant details):", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterAskConfirmation(Action):
    def name(self) -> Text:
        return "action_utter_ask_confirmation"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        msg = ts.translate("Would you like me to send this complaint to the respective department?", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterThankYou(Action):
    def name(self) -> Text:
        return "action_utter_thank_you"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        complaint_id = tracker.get_slot("complaint_id") or ""
        msg = ts.translate(f"Thank you! Your complaint has been registered with ID {complaint_id}.", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]


class ActionUtterGoodbye(Action):
    def name(self) -> Text:
        return "action_utter_goodbye"

    async def run(self, dispatcher, tracker, domain):
        lang = tracker.get_slot("language") or "en"
        ts = TranslationService()
        msg = ts.translate("Goodbye! Feel free to reach out again if you need help.", lang, tracker)
        dispatcher.utter_message(text=msg)
        return [SlotSet("requested_slot", None)]
