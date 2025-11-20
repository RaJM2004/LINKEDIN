import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def start_messaging_bot(username: str, password: str, gemini_api_key: str | None = None):
    model = None
    if gemini_api_key:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

    def generate_reply(message_text: str) -> str:
        if not model:
            return "Thanks for your message! I'll get back to you soon."
        try:
            prompt = (
                f"You are replying on LinkedIn.\nMessage: \"{message_text}\"\n"
                "Rules:\n- Reply in under 40 words\n- Be professional, natural, friendly\n- No emojis, no switching platforms\n- If greeting, greet back and ask how to help"
            )
            response = model.generate_content(prompt)
            reply = (response.text or "").strip()
            return reply or "Thanks for your message! I'll get back to you soon."
        except Exception:
            return "Thanks for your message! I'll get back to you soon."

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15)

    def find_messages():
        selectors = [
            "div.msg-s-event-listitem",
            "div.msg-s-message-list__event",
            "li.msg-s-message-list__event",
        ]
        for selector in selectors:
            try:
                messages = driver.find_elements(By.CSS_SELECTOR, selector)
                if messages:
                    return messages
            except:
                continue
        return []

    def send_message_safe(message_text: str) -> bool:
        try:
            msg_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.msg-form__contenteditable")))
            msg_box.click()
            time.sleep(1)
            msg_box.send_keys(Keys.CONTROL + "a")
            msg_box.send_keys(Keys.DELETE)
            msg_box.send_keys(message_text)
            time.sleep(1)
            send_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.msg-form__send-button")))
            driver.execute_script("arguments[0].click();", send_button)
            return True
        except Exception:
            return False

    try:
        driver.get("https://www.linkedin.com/login")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)
        if "feed" not in driver.current_url and "messaging" not in driver.current_url:
            return False
        processed_messages = set()
        while True:
            try:
                driver.get("https://www.linkedin.com/messaging/")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.msg-conversation-listitem")))
                chats = driver.find_elements(By.CSS_SELECTOR, "li.msg-conversation-listitem")
                for chat in chats[:5]:
                    chat.click()
                    time.sleep(3)
                    messages = find_messages()
                    if not messages:
                        continue
                    last_message = messages[-1].find_element(By.CSS_SELECTOR, "p").text.strip() if messages[-1].find_elements(By.CSS_SELECTOR, "p") else messages[-1].text.strip()
                    last_message_id = messages[-1].get_attribute("id") or last_message
                    if last_message_id in processed_messages:
                        continue
                    if "You" in messages[-1].text:
                        continue
                    reply = generate_reply(last_message)
                    if send_message_safe(reply):
                        processed_messages.add(last_message_id)
                    time.sleep(2)
                time.sleep(15)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(10)
    except Exception:
        return False
    finally:
        driver.quit()
    return True

if __name__ == "__main__":
    import os
    u = os.environ.get("LINKEDIN_EMAIL") or ""
    p = os.environ.get("LINKEDIN_PASSWORD") or ""
    k = os.environ.get("GEMINI_API_KEY")
    start_messaging_bot(u, p, k)
