# Grievances Bot

This project is a multi-part grievance registration system that includes a user-friendly chatbot interface. It's built with a Flask backend for user authentication, a Rasa server for the chatbot, a custom Rasa action server for tasks like sending emails, and a static frontend for the user interface.

## Prerequisites

- **Python 3.8+** and `pip`
- **Git** for cloning the repository.

## Setup Instructions

### 1. Clone the Repository

Clone this repository to your local machine:

```bash
git clone <repository-url>
cd grievancesbot
```

### 2. Create a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
python -m venv venv
```

Activate the virtual environment:

- **On Windows:**
  ```bash
  .\venv\Scripts\activate
  ```
- **On macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 4. Configure Email Credentials

The chatbot's action server sends emails using SMTP. You need to provide your Gmail credentials in a `.env` file.

1.  **Navigate to the actions directory:**
    ```bash
    cd chatbot/actions
    ```
2.  **Create a `.env` file** with the following content:
    ```
    SMTP_USERNAME="your-email@gmail.com"
    SMTP_PASSWORD="your-gmail-app-password"
    ```
    - **Important:** For the `SMTP_PASSWORD`, you must use a **Gmail App Password**. You can generate one by going to your Google Account settings, under "Security," and then "App passwords."

3.  **Return to the root directory:**
    ```bash
    cd ../..
    ```

## How to Run the Project

A single script handles the startup of all necessary services (Flask backend, Rasa server, Rasa action server, and the frontend static server).

Simply run the `start_project.bat` script from the root directory of the project:

```bash
.\start_project.bat
```

This script will:
- Activate the virtual environment.
- Start all four servers in separate terminal windows.
- Automatically open the project's landing page in your default web browser.

Once the script has run, you can start by registering a new user and then logging in to use the chatbot.