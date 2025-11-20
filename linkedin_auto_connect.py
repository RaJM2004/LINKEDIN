import os
import time
import random
import logging
from logging import FileHandler, StreamHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

class LinkedInAutoConnector:
    def __init__(self):
        self.setup_logging()
        self.driver = None
        self.wait = None
        
    def setup_logging(self):
        self.logger = logging.getLogger("linkedin_connect")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
            fh = FileHandler('linkedin_connect.log', encoding='utf-8')
            fh.setFormatter(fmt)
            sh = StreamHandler()
            sh.setFormatter(fmt)
            self.logger.addHandler(fh)
            self.logger.addHandler(sh)

    def setup_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 20)
            self.logger.info("✅ Chrome driver setup successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to setup driver: {e}")
            return False

    def login(self, email, password):
        """Login to LinkedIn"""
        try:
            self.logger.info("🔐 Logging into LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)

            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.clear()
            email_field.send_keys(email)
            self.logger.info("✅ Email entered")

            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            self.logger.info("✅ Password entered")

            # Click sign in
            sign_in_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            sign_in_btn.click()
            self.logger.info("✅ Login button clicked")

            # Wait for login
            time.sleep(8)

            # Check login success
            if any(x in self.driver.current_url for x in ['feed', 'dashboard', 'mynetwork']):
                self.logger.info("✅ Login successful!")
                return True
            elif "checkpoint" in self.driver.current_url:
                self.logger.warning("⚠️ Verification required.")
                input("Complete verification and press Enter to continue...")
                return True
            else:
                self.logger.info("✅ Assuming login successful (on main page)")
                return True

        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False

    def search_diverse_connections(self, max_connections=50):
        """Search for diverse connections across different categories"""
        
        connection_categories = {
            "startup": ["startup founder", "entrepreneur", "startup CEO", "startup CTO"],
            "enterprise": ["enterprise architect", "VP engineering", "director technology", "chief technology officer"],
            "ai_ml": ["machine learning engineer", "AI researcher", "data scientist", "ML engineer"],
            "gen_ai": ["generative AI", "ChatGPT", "LLM engineer", "AI product manager"],
            "anthropic_ai": ["Anthropic", "Claude AI", "AI safety researcher", "responsible AI"],
            "tech_general": ["software engineer", "full stack developer", "DevOps engineer", "cloud architect"],
            "product": ["product manager", "product owner", "UX designer", "product designer"],
            "leadership": ["tech lead", "engineering manager", "CTO", "VP product"],
            "venture": ["venture capital", "angel investor", "startup advisor", "VC partner"],
            "innovation": ["innovation manager", "digital transformation", "technology consultant"]
        }
        
        total_connections = 0
        connections_per_category = max(2, max_connections // len(connection_categories))
        
        self.logger.info(f"🎯 Target: {max_connections} connections across {len(connection_categories)} categories")
        self.logger.info(f"📊 ~{connections_per_category} connections per category")
        
        for category, keywords_list in connection_categories.items():
            if total_connections >= max_connections:
                break
                
            self.logger.info(f"\n🔍 Searching category: {category.upper()}")
            
            # Try each keyword in the category
            for keyword in keywords_list:
                if total_connections >= max_connections:
                    break
                    
                remaining_connections = min(
                    connections_per_category, 
                    max_connections - total_connections
                )
                
                if remaining_connections <= 0:
                    continue
                
                self.logger.info(f"🔎 Keyword: '{keyword}' (targeting {remaining_connections} connections)")
                
                sent = self.search_and_connect_by_keyword(keyword, remaining_connections)
                total_connections += sent
                
                # Brief pause between different searches
                if sent > 0:
                    pause_time = random.uniform(10, 20)
                    self.logger.info(f"⏸️ Pausing {pause_time:.1f}s before next search...")
                    time.sleep(pause_time)
                
                # Break after successful connections to move to next category
                if sent > 0:
                    break
        
        self.logger.info(f"\n🎉 Total connections sent: {total_connections}/{max_connections}")
        self.logger.info(f"📈 Success rate: {(total_connections/max_connections)*100:.1f}%")
        
        return total_connections

    def search_and_connect_by_keyword(self, keyword, max_connections):
        """Search and connect for a specific keyword"""
        try:
            # Go to LinkedIn people search
            search_url = (
                f"https://www.linkedin.com/search/results/people/?keywords={keyword.replace(' ', '%20')}"
                f"&origin=SWITCH_SEARCH_VERTICAL&network=%5B%22S%22,%22O%22%5D"
            )
            self.driver.get(search_url)
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.reusable-search__entity-result-list")))
            except:
                time.sleep(5)
            
            connections_sent = 0
            page_attempts = 0
            max_pages = 2
            
            while connections_sent < max_connections and page_attempts < max_pages:
                # Scroll to load more results
                self.scroll_page()
                
                # Find ALL interactive buttons (Connect, Follow, Message, etc.)
                all_action_buttons = self.find_all_action_buttons()
                
                if not all_action_buttons:
                    self.logger.warning(f"No action buttons found for '{keyword}' on page {page_attempts + 1}")
                    break
                
                self.logger.info(f"Found {len(all_action_buttons)} action buttons for '{keyword}'")
                
                for i, (button, action_type) in enumerate(all_action_buttons):
                    if connections_sent >= max_connections:
                        break
                        
                    try:
                        # Scroll to button
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(2)
                        
                        # Get person's name and title for logging
                        person_name, person_title = self.get_person_info_from_button(button)
                        
                        self.dismiss_overlays()
                        # Perform action based on button type
                        if action_type == "connect":
                            success = self.click_connect_button(button, person_name)
                        elif action_type == "follow":
                            success = self.click_follow_button(button, person_name)
                        else:
                            self.logger.info(f"ℹ️ Skipping {action_type} button for {person_name}")
                            continue
                        
                        if success:
                            connections_sent += 1
                            self.logger.info(f"✅ {action_type.capitalize()} with {person_name} | {person_title} ({connections_sent}/{max_connections})")
                        else:
                            self.logger.warning(f"⚠️ Could not {action_type} with {person_name}")
                        
                        # Random delay between actions
                        delay = random.uniform(6, 12)
                        time.sleep(delay)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error processing button {i+1}: {str(e)}")
                        continue
                
                # Try next page if needed
                if connections_sent < max_connections and page_attempts < max_pages - 1:
                    if self.go_to_next_page():
                        page_attempts += 1
                        time.sleep(4)
                    else:
                        break
                else:
                    break
            
            return connections_sent
            
        except Exception as e:
            self.logger.error(f"❌ Keyword search failed for '{keyword}': {str(e)}")
            return 0

    def scroll_page(self):
        """Scroll the page to load more content"""
        try:
            self.driver.execute_script("window.scrollTo(0, 400);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 1200);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 1600);")
            time.sleep(1)
        except:
            pass

    def find_all_action_buttons(self):
        """Find ALL action buttons (Connect, Follow, Message, etc.)"""
        action_buttons = []
        
        # Find Connect buttons
        connect_selectors = [
            "//button[.//span[text()='Connect']]",
            "//button[contains(@aria-label, 'Connect')]",
            "//button[contains(@data-control-name, 'connect')]",
            "//button[starts-with(@aria-label,'Invite')]",
            "//button[contains(@class,'artdeco-button')][contains(.,'Connect')]"
        ]
        
        for selector in connect_selectors:
            try:
                buttons = self.driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled() and (btn, "connect") not in action_buttons:
                        action_buttons.append((btn, "connect"))
            except:
                continue
        
        # Find Follow buttons (if no Connect buttons found)
        if not action_buttons:
            follow_selectors = [
                "//button[.//span[text()='Follow']]",
                "//button[contains(@aria-label, 'Follow')]",
                "//button[contains(@data-control-name, 'follow')]"
            ]
            
            for selector in follow_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled() and (btn, "follow") not in action_buttons:
                            action_buttons.append((btn, "follow"))
                except:
                    continue
        
        # If still no buttons, look for any action buttons in result cards
        if not action_buttons:
            try:
                # Find all profile cards first
                profile_cards = self.driver.find_elements(By.CSS_SELECTOR, "li.reusable-search__result-container, div.entity-result")
                for card in profile_cards:
                    try:
                        # Look for any buttons in the card
                        buttons = card.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            if btn.is_displayed() and btn.is_enabled():
                                btn_text = btn.text.strip().lower()
                                if 'connect' in btn_text:
                                    action_buttons.append((btn, "connect"))
                                elif 'follow' in btn_text:
                                    action_buttons.append((btn, "follow"))
                                elif 'message' in btn_text:
                                    action_buttons.append((btn, "message"))
                    except:
                        continue
            except:
                pass
        
        return action_buttons

    def get_person_info_from_button(self, button):
        """Extract person info from the button's context"""
        try:
            # Find the parent result card
            person_card = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'entity-result') or contains(@class, 'reusable-search__result')][1]")
            
            # Get name
            try:
                name_element = person_card.find_element(By.XPATH, ".//span[contains(@class, 'entity-result__title')]//span[@aria-hidden='true']")
                person_name = name_element.text.strip()
            except:
                person_name = "Unknown"
            
            # Get title
            try:
                title_element = person_card.find_element(By.XPATH, ".//div[contains(@class, 'entity-result__primary-subtitle')]")
                person_title = title_element.text.strip()
            except:
                person_title = "Unknown title"
            
            return person_name, person_title
            
        except:
            return "Unknown", "Unknown title"

    def click_connect_button(self, button, person_name):
        """Click connect button and handle modal"""
        try:
            self.driver.execute_script("arguments[0].click();", button)
            time.sleep(3)
            
            # Handle connection modal
            return self.handle_connection_modal()
            
        except Exception as e:
            self.logger.error(f"❌ Connect click failed for {person_name}: {e}")
            return False

    def click_follow_button(self, button, person_name):
        """Click follow button"""
        try:
            self.driver.execute_script("arguments[0].click();", button)
            time.sleep(3)
            self.logger.info(f"✅ Followed {person_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Follow click failed for {person_name}: {e}")
            return False

    def handle_connection_modal(self):
        """Handle connection confirmation modal"""
        try:
            # Look for send button
            send_selectors = [
                "button[aria-label='Send without a note']",
                "button[data-test-dialog-primary-btn]",
                "button[aria-label='Send invitation']",
                "//button[.//span[text()='Send']]"
            ]
            
            for selector in send_selectors:
                try:
                    if selector.startswith("//"):
                        send_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        send_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if send_btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", send_btn)
                        time.sleep(2)
                        return True
                except:
                    continue
            
            # Check if already connected or pending
            status_elements = self.driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Pending') or contains(text(), 'Invitation sent')]")
            if status_elements:
                self.close_modal()
                return True
            
            # If no modal found, connection might be sent directly
            self.close_modal()
            return True
            
        except Exception as e:
            self.logger.warning(f"Modal handling error: {e}")
            self.close_modal()
            return False

    def close_modal(self):
        """Close any open modal"""
        try:
            close_buttons = self.driver.find_elements(By.XPATH, 
                "//button[@aria-label='Dismiss' or contains(@class, 'artdeco-modal__dismiss')]")
            for btn in close_buttons:
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                    break
        except:
            pass

    def dismiss_overlays(self):
        try:
            selectors = [
                "//button[@aria-label='Dismiss']",
                "//button[@aria-label='Close']",
                "//button[contains(@class,'artdeco-modal__dismiss')]",
                "//button[contains(@class,'consent')]",
            ]
            for xp in selectors:
                try:
                    btns = self.driver.find_elements(By.XPATH, xp)
                    if btns:
                        self.driver.execute_script("arguments[0].click();", btns[0])
                        time.sleep(1)
                except:
                    continue
        except:
            pass

    def go_to_next_page(self):
        """Navigate to next page of results"""
        try:
            next_buttons = self.driver.find_elements(By.XPATH, "//button[@aria-label='Next' and not(@disabled)]")
            for btn in next_buttons:
                if btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
            return False
        except:
            return False

    def run_auto_connection_campaign(self, total_connections=20):
        """Run the complete auto-connection campaign"""
        self.logger.info("🚀 Starting LinkedIn Auto-Connection Campaign...")
        self.logger.info("🔍 This will search across multiple professional categories")
        self.logger.info("🤝 Will CONNECT when possible, FOLLOW when Connect not available")
        
        # Run the diverse connections search
        connections_sent = self.search_diverse_connections(total_connections)
        
        # Final results
        self.logger.info(f"\n🎊 CAMPAIGN COMPLETE!")
        self.logger.info(f"📊 Total actions performed: {connections_sent}")
        if connections_sent > 0:
            self.logger.info("🌟 Your professional network is growing! 🚀")
        else:
            self.logger.info("❌ No actions were performed. LinkedIn may be restricting buttons.")

        return connections_sent

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.logger.info("🔚 Browser closed")

def main():
    # Your credentials
    LINKEDIN_EMAIL = "rajmange94@gmail.com"
    LINKEDIN_PASSWORD = "RAJM@2004"
    
    # Create bot instance
    bot = LinkedInAutoConnector()
    
    try:
        # Setup driver and login
        if bot.setup_driver() and bot.login(LINKEDIN_EMAIL, LINKEDIN_PASSWORD):
            # Run auto-connection campaign
            bot.run_auto_connection_campaign(total_connections=15)
        else:
            bot.logger.error("❌ Setup or login failed")
            
    except Exception as e:
        bot.logger.error(f"❌ Main execution failed: {e}")
        
    finally:
        bot.close()

if __name__ == "__main__":
    print("🤖 LinkedIn Auto-Connector (Connect + Follow)")
    print("=" * 50)
    print("This bot will automatically:")
    print("✅ Login to your LinkedIn account")
    print("✅ Search across 10 professional categories") 
    print("✅ CONNECT when Connect buttons are available")
    print("✅ FOLLOW when Connect buttons are not available")
    print("✅ Handle all modals automatically")
    print("=" * 50)
    
    main()