from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import smtplib
from googletrans import Translator
from rasa_sdk.types import DomainDict
from langdetect import detect
from rasa_sdk.events import SlotSet
from datetime import datetime
import os

translator = Translator()

class ActionDetectLanguage(Action):
    def name(self) -> Text:
        return "action_detect_language"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        user_text = tracker.latest_message.get("text", "")
        try:
            lang = detect(user_text)
            # Map to supported languages
            lang_map = {
                "hi": "hi",  # Hindi
                "mr": "mr",  # Marathi
                "ta": "ta",  # Tamil
                "te": "te",  # Telugu
                "kn": "kn",  # Kannada
                "bn": "bn",  # Bengali
                "gu": "gu",  # Gujarati
                "pa": "pa",  # Punjabi
                "or": "or",  # Odia
                "ml": "ml",  # Malayalam
            }
            return [SlotSet("language", lang_map.get(lang, "en"))]
        except:
            return [SlotSet("language", "en")]

class ActionTranslateAndRespond(Action):
    def name(self) -> Text:
        return "action_translate_and_respond"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        lang = tracker.get_slot("language") or "en"
        response = domain.get("responses", {}).get("utter_greet", [{}])[0].get("text", "Hello")
        
        try:
            translated = translator.translate(response, dest=lang).text
            dispatcher.utter_message(text=translated)
        except Exception as e:
            dispatcher.utter_message(text=response)
        
        return []

def translate_text(text, dest_lang):
    if dest_lang and dest_lang != "en":
        try:
            return translator.translate(text, dest=dest_lang).text
        except Exception as e:
            print(f"Translation failed: {e}")
            return text
    return text


class ActionGenerateDraft(Action):
    def name(self) -> Text:
        return "action_generate_draft"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        state = tracker.get_slot("state") or "[state not provided]"
        area = tracker.get_slot("area") or "[area not provided]"
        department = tracker.get_slot("department") or "[department not provided]"
        complaint = tracker.get_slot("complaint_details") or "[complaint not provided]"
        lang = tracker.get_slot("language") or "en"

        # English template (will be translated if needed)
        email_template = (
            "Subject: {subject}\n\n"
            "Dear Sir/Madam,\n\n"
            "I am writing to bring to your attention an issue related to the {department} "
            "in the area of {area}, {state}.\n\n"
            "Complaint Details:\n{complaint}\n\n"
            "I kindly request you to take prompt action regarding this matter. "
            "Looking forward to a swift resolution.\n\n"
            "Thank you.\n\n"
            "Regards,\n"
            "A concerned citizen"
        )

        # Prepare the email in English (for authorities)
        english_email = email_template.format(
            subject=f"Urgent Complaint Regarding {department}",
            department=department.lower(),
            area=area,
            state=state,
            complaint=complaint
        )

        # Prepare a localized version for the user
        localized_subject = translate_text(f"Urgent Complaint Regarding {department}", lang)
        localized_body = translate_text(
            f"I am writing to report a {department.lower()} issue in {area}, {state}.\n\n"
            f"Complaint Details:\n{complaint}\n\n"
            f"Please address this as soon as possible.",
            lang
        )

        # Show user both versions
        dispatcher.utter_message(text=translate_text(
            "Here is your draft email that will be sent to authorities in English:\n\n" +
            english_email, lang))
        
        dispatcher.utter_message(text=translate_text(
            "\n\nHere's how it reads in your language:\n\n" +
            f"{localized_subject}\n\n{localized_body}", lang))

        return []


class ActionSubmitComplaint(Action):
    def name(self) -> Text:
        return "action_submit_complaint"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        import uuid
        from datetime import datetime

        # Get all required slots
        state = (tracker.get_slot("state") or "").lower()
        area = tracker.get_slot("area") or "N/A"
        department = tracker.get_slot("department") or "N/A"
        complaint = tracker.get_slot("complaint_details") or "N/A"
        lang = tracker.get_slot("language") or "en"
        user_email = tracker.sender_id  # Assuming sender_id contains user's email

        # Generate complaint ID with timestamp
        now = datetime.now()
        complaint_id = f"{state[:3].upper()}-{department[:3].upper()}-{now.strftime('%Y%m%d-%H%M')}"

        # Get department email (expanded list)
        dept_emails = {
            "delhi": {
                "water": "water-complaints.delhi@gov.in",
                "electricity": "power-complaints.delhi@gov.in",
                "transport": "transport.delhi@gov.in"
            },
            "maharashtra": {
                "water": "water-complaints.maha@gov.in",
                "electricity": "energy.maha@gov.in",
                "land": "revenue.maha@gov.in"
            },
            # Add more states and departments as needed
        }

        # Find the appropriate email
        email = dept_emails.get(state, {}).get(department.lower())
        
        if not email:
            msg = translate_text(
                f"Sorry, we don't have contact information for {department} department in {state}. "
                "Please visit the official state website for contact details.",
                lang
            )
            dispatcher.utter_message(text=msg)
            return []

        # Prepare email content
        subject = f"Complaint ID: {complaint_id} - {department} Issue in {area}, {state}"
        body = (
            f"Complaint ID: {complaint_id}\n"
            f"Date: {now.strftime('%d-%m-%Y %H:%M')}\n"
            f"From: {user_email}\n\n"
            f"Department: {department}\n"
            f"Location: {area}, {state}\n\n"
            f"Complaint Details:\n{complaint}\n\n"
            f"Expected Resolution Time: 3-5 working days\n\n"
            "---\n"
            "This is an auto-generated complaint from the Central Grievance Portal"
        )

        try:
            # Send email (configure these in your environment variables)
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            sender_email = os.getenv("SMTP_USERNAME")
            sender_password = os.getenv("SMTP_PASSWORD")

            if not sender_email or not sender_password:
                error_msg = translate_text(
                    "⚠️ Email configuration error: SMTP_USERNAME or SMTP_PASSWORD is not set. Please contact support.",
                    lang
                )
                dispatcher.utter_message(text=error_msg)
                print("SMTP credentials missing: SMTP_USERNAME or SMTP_PASSWORD not set.")
                return []

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                
                # Email to department
                server.sendmail(
                    sender_email, 
                    email, 
                    f"Subject: {subject}\n\n{body}"
                )
                
                # Confirmation email to user
                confirmation_subject = f"Complaint Registered: {complaint_id}"
                confirmation_body = (
                    f"Your complaint has been successfully registered.\n\n"
                    f"Complaint ID: {complaint_id}\n"
                    f"Department: {department}\n"
                    f"Location: {area}, {state}\n\n"
                    f"Details:\n{complaint}\n\n"
                    f"Expected Resolution Time: 3-5 working days\n\n"
                    "Thank you for using our grievance portal."
                )
                
                server.sendmail(
                    sender_email,
                    user_email,
                    f"Subject: {confirmation_subject}\n\n{confirmation_body}"
                )

            # Prepare localized success message
            success_msg = translate_text(
                f"✅ Complaint registered successfully! ID: {complaint_id}\n"
                f"• Department: {department}\n"
                f"• Location: {area}, {state}\n"
                "A confirmation has been sent to your email.\n"
                "You'll receive updates within 3-5 working days.",
                lang
            )
            dispatcher.utter_message(text=success_msg)

        except Exception as e:
            error_msg = translate_text(
                f"⚠️ Failed to submit complaint. Error: {str(e)}\n"
                "Please try again later or contact support.",
                lang
            )
            dispatcher.utter_message(text=error_msg)
            # Log the error for debugging
            print(f"Failed to send email: {str(e)}")

        return []