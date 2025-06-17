from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import smtplib

class ActionGenerateDraft(Action):
    def name(self) -> Text:
        return "action_generate_draft"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: # type: ignore
        # Extract slots (user inputs)
         # Safely get slots with default values
        state = tracker.get_slot("state") or "[state not provided]"
        area = tracker.get_slot("area") or "[area not provided]"
        department = tracker.get_slot("department") or "[department not provided]"
        complaint = tracker.get_slot("complaint_details") or "[complaint not provided]"


          # Generate email draft
        email_body = (
            f"Subject: Urgent Complaint Regarding {department}\n\n"
            f"Dear Sir/Madam,\n\n"
            f"I am writing to bring to your attention an issue related to the {department.lower()} "
            f"in the area of {area}, {state}.\n\n"
            f"Complaint Details:\n{complaint}\n\n"
            f"I kindly request you to take prompt action regarding this matter. "
            f"Looking forward to a swift resolution.\n\n"
            f"Thank you.\n\n"
            f"Regards,\n"
            f"A concerned citizen"
        )

         # Send the draft to the user
        dispatcher.utter_message(text="Here is your draft email:\n\n" + email_body)

        return []
    
STATE_EMAILS = {
    "delhi": "complaints.delhi@gov.in",
    "maharashtra": "complaints.maha@gov.in",
    "telangana": "grievance.telangana@gov.in"
} 

class ActionSubmitComplaint(Action):
    def name(self) -> Text:
        return "action_submit_complaint"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: # type: ignore
        # Generate complaint ID
        import uuid
        complaint_id = str(uuid.uuid4())[:8]

        state = (tracker.get_slot("state") or "").lower()
        area = tracker.get_slot("area") or "N/A"
        department = tracker.get_slot("department") or "N/A"
        complaint = tracker.get_slot("complaint_details") or "N/A"

        email = STATE_EMAILS.get(state)

        if not email:
            dispatcher.utter_message(text=f"Sorry, I don't have the email address for {state}.")
            return []

        subject = f"Urgent Complaint Regarding {department}"
        body = (
            f"Dear Sir/Madam,\n\n"
            f"I am writing to report a {department.lower()} issue in {area}, {state}.\n\n"
            f"Details:\n{complaint}\n\n"
            f"Please address this as soon as possible.\n\n"
            f"Regards,\nA concerned citizen"
        )

        try:
            # Replace with your SMTP setup (you must configure this securely!)
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = "your-email@gmail.com"
            sender_password = "your-app-password"

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, email, f"Subject: {subject}\n\n{body}")

            dispatcher.utter_message(text=f"✅ Email sent to the {department} of {state} at {email}.")
        except Exception as e:
            dispatcher.utter_message(text=f"⚠️ Failed to send email: {str(e)}")

        return []