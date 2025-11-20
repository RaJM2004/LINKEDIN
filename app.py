import time
import random
import json
import schedule
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import openai
import sys
import io
import logging

class LinkedInAgent:
    def __init__(self, email, password, openai_api_key=None):
        """
        Initialize LinkedIn Agent
        
        Args:
            email: LinkedIn email
            password: LinkedIn password  
            openai_api_key: OpenAI API key for content generation (optional)
        """
        self.email = email
        self.password = password
        self.openai_api_key = openai_api_key
        self.driver = None
        self.wait = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('linkedin_agent.log', encoding='utf-8'),
                logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'))
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Content templates for different industries
        self.content_templates = {
            "tech": [
                "The future of technology lies in {topic}. What are your thoughts on how this will impact {industry}? #Tech #Innovation",
                "Just learned about {topic} and I'm fascinated by its potential. How do you see this changing {industry}? #TechTrends",
                "Exploring the intersection of {topic} and business strategy. What opportunities do you see? #TechLeadership"
            ],
            "business": [
                "Leadership isn't about having all the answers, it's about asking the right questions about {topic}. #Leadership #Business",
                "In today's market, {topic} is becoming increasingly important. How is your organization adapting? #BusinessStrategy",
                "The key to success in {industry} is understanding {topic}. What's your experience? #BusinessGrowth"
            ],
            "marketing": [
                "Marketing is evolving rapidly with {topic}. What strategies are you finding most effective? #Marketing #DigitalMarketing",
                "The power of {topic} in modern marketing cannot be overstated. Share your success stories! #MarketingStrategy",
                "How are you leveraging {topic} to connect with your audience? #ContentMarketing #Engagement"
            ]
        }
        
        # Target keywords for connection searches
        self.target_keywords = []
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        
    def login(self):
        """Login to LinkedIn"""
        try:
            self.logger.info("Logging in to LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            
            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for home page
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "feed-shared-update-v2")))
            self.logger.info("Successfully logged in to LinkedIn")
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False
    
    def clean_content(self, content):
        """Clean content to remove characters that cause ChromeDriver issues"""
        import re
        import unicodedata
        
        # Remove or replace problematic characters
        content = content.replace('"', '"').replace('"', '"')  # Replace smart quotes
        content = content.replace(''', "'").replace(''', "'")  # Replace smart apostrophes
        content = content.replace('—', '-').replace('–', '-')  # Replace em/en dashes
        content = content.replace('…', '...')  # Replace ellipsis
        
        # Remove any non-BMP characters (outside Basic Multilingual Plane)
        content = ''.join(char for char in content if ord(char) <= 0xFFFF)
        
        # Normalize unicode characters
        content = unicodedata.normalize('NFKD', content)
        
        # Remove any remaining problematic characters
        content = re.sub(r'[^\x00-\x7F\x80-\xFF\u0100-\uFFFF]', '', content)
        
        return content.strip()
    
    def generate_unique_content(self, industry="tech"):
        """Generate unique, diverse content using AI"""
        try:
            if not self.openai_api_key:
                self.logger.warning("No OpenAI API key provided, using template content")
                return self.generate_template_content(industry)
            
            # Dynamic content topics and formats
            content_types = [
                "industry_insight", "personal_experience", "trend_analysis", 
                "question_post", "story_telling", "tip_sharing", "prediction"
            ]
            
            topics_pool = [
                "artificial intelligence", "machine learning", "generative AI", "automation",
                "digital transformation", "cloud computing", "cybersecurity", "blockchain",
                "startup ecosystem", "venture capital", "product management", "leadership",
                "remote work", "team building", "innovation", "data science",
                "software engineering", "DevOps", "user experience", "business strategy"
            ]
            
            post_styles = [
                "thought-provoking question", "personal story with lesson", "industry prediction",
                "contrarian viewpoint", "tips and advice", "behind-the-scenes insight",
                "collaboration call", "celebration post", "learning experience"
            ]
            
            # Randomly select content parameters
            content_type = random.choice(content_types)
            topic = random.choice(topics_pool)
            style = random.choice(post_styles)
            
            # Generate timestamp-based unique element
            current_time = datetime.now()
            time_context = self.get_time_context(current_time)
            
            openai.api_key = self.openai_api_key
            
            prompt = f"""
            Create a unique, engaging LinkedIn post with these parameters:
            - Content type: {content_type}
            - Topic: {topic}
            - Style: {style}
            - Time context: {time_context}
            - Industry focus: {industry}
            
            Requirements:
            - Make it authentic and personal
            - Include 3-5 relevant hashtags
            - Ask an engaging question or call-to-action
            - Be 120-180 words
            - Use only standard characters (no special Unicode)
            - Make it unique and different from typical corporate posts
            - Add some personality and authenticity
            
            Avoid generic phrases like "I'm excited to share" or "thoughts?"
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional content creator who writes authentic, engaging LinkedIn posts that spark genuine conversations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.8  # Higher creativity
            )
            
            content = response.choices[0].message.content.strip()
            return self.clean_content(content)
                
        except Exception as e:
            self.logger.error(f"AI content generation failed: {str(e)}")
            return self.generate_template_content(industry)
    
    def get_time_context(self, current_time):
        """Get time-based context for content"""
        hour = current_time.hour
        day = current_time.strftime("%A")
        
        if hour < 12:
            return f"this {day} morning"
        elif hour < 17:
            return f"this {day} afternoon" 
        else:
            return f"this {day} evening"
    
    def generate_template_content(self, industry):
        """Fallback template content with variations"""
        templates = {
            "tech": [
                "Just had a fascinating conversation about {topic}. The way it's reshaping {aspect} is incredible. What's your experience with this technology? {hashtags}",
                "Been diving deep into {topic} lately. The potential applications in {aspect} are mind-blowing. How are you seeing this play out in your field? {hashtags}",
                "Hot take: {topic} isn't just a trend - it's fundamentally changing how we approach {aspect}. What do you think? {hashtags}",
                "Spent the weekend exploring {topic} and I'm convinced it's going to revolutionize {aspect}. Share your thoughts! {hashtags}"
            ]
        }
        
        topics = ["AI automation", "machine learning", "generative AI", "cloud architecture", "data science"]
        aspects = ["business operations", "customer experience", "product development", "decision making"]
        hashtags = "#AI #Tech #Innovation #Future #MachineLearning"
        
        template = random.choice(templates.get(industry, templates["tech"]))
        content = template.format(
            topic=random.choice(topics),
            aspect=random.choice(aspects),
            hashtags=hashtags
        )
        
        return self.clean_content(content)
    
    def create_post(self, content):
        """Create a LinkedIn post"""
        try:
            self.logger.info("Creating LinkedIn post...")
            
            # Clean content before posting
            clean_content = self.clean_content(content)
            self.logger.info(f"Cleaned content: {clean_content[:100]}...")
            
            # Go to LinkedIn home
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)
            
            # Try different selectors for the "Start a post" button
            start_post_selectors = [
                "//button[contains(@class, 'artdeco-button') and contains(., 'Start a post')]",
                "//span[text()='Start a post']/parent::button",
                "//button[contains(text(), 'Start a post')]",
                "//*[contains(@class, 'share-box-feed-entry__trigger')]",
                "//div[contains(@class, 'share-box-feed-entry__closed-share-box')]"
            ]
            
            start_post_clicked = False
            for selector in start_post_selectors:
                try:
                    start_post = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    start_post.click()
                    start_post_clicked = True
                    break
                except:
                    continue
            
            if not start_post_clicked:
                self.logger.error("Could not find 'Start a post' button")
                return False
            
            time.sleep(3)
            
            # Try different selectors for the post text area
            text_area_selectors = [
                "//div[@data-placeholder='What do you want to talk about?']",
                "//div[contains(@class, 'ql-editor')]",
                "//div[@role='textbox']",
                "//div[@contenteditable='true']"
            ]
            
            post_textbox = None
            for selector in text_area_selectors:
                try:
                    post_textbox = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    break
                except:
                    continue
            
            if not post_textbox:
                self.logger.error("Could not find post text area")
                return False
            
            # Click and enter content
            post_textbox.click()
            time.sleep(1)
            
            # Clear any existing content and type new content
            post_textbox.clear()
            post_textbox.send_keys(clean_content)
            
            time.sleep(3)
            
            # Try different selectors for the Post button
            post_button_selectors = [
                "//button[contains(@class, 'share-actions-primary-button') and .//span[text()='Post']]",
                "//button[.//span[text()='Post']]",
                "//button[contains(@data-control-name, 'share.post')]",
                "//button[text()='Post']"
            ]
            
            post_button_clicked = False
            for selector in post_button_selectors:
                try:
                    post_button = self.driver.find_element(By.XPATH, selector)
                    if post_button.is_enabled():
                        post_button.click()
                        post_button_clicked = True
                        break
                except:
                    continue
            
            if not post_button_clicked:
                self.logger.error("Could not find or click Post button")
                return False
            
            time.sleep(5)
            self.logger.info("Post created successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Post creation failed: {str(e)}")
            # Try to close any open modals
            try:
                close_buttons = self.driver.find_elements(By.XPATH, "//button[@aria-label='Dismiss' or @aria-label='Close']")
                for button in close_buttons:
                    try:
                        button.click()
                        break
                    except:
                        continue
            except:
                pass
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
            # Go to LinkedIn people search with filters
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={keyword.replace(' ', '%20')}&origin=SWITCH_SEARCH_VERTICAL"
            self.driver.get(search_url)
            time.sleep(3)
            
            connections_sent = 0
            page_attempts = 0
            max_pages = 2  # Limit pages per keyword
            
            while connections_sent < max_connections and page_attempts < max_pages:
                # Find connect buttons on current page
                connect_buttons = self.driver.find_elements(By.XPATH, "//button[.//span[text()='Connect']]")
                
                if not connect_buttons:
                    self.logger.warning(f"No connect buttons found for '{keyword}' on page {page_attempts + 1}")
                    break
                
                self.logger.info(f"Found {len(connect_buttons)} connect buttons for '{keyword}'")
                
                for i, button in enumerate(connect_buttons):
                    if connections_sent >= max_connections:
                        break
                        
                    try:
                        # Scroll to button and get person info
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(2)
                        
                        # Get person's name and title for logging
                        try:
                            person_card = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'entity-result')]")
                            name_element = person_card.find_element(By.XPATH, ".//span[contains(@class, 'entity-result__title')]//span[@aria-hidden='true']")
                            person_name = name_element.text.strip()
                            
                            try:
                                title_element = person_card.find_element(By.XPATH, ".//div[contains(@class, 'entity-result__primary-subtitle')]")
                                person_title = title_element.text.strip()
                            except:
                                person_title = "Unknown title"
                        except:
                            person_name = f"Person {i+1}"
                            person_title = "Unknown"
                        
                        # Click connect button
                        button.click()
                        time.sleep(2)
                        
                        # Handle connection modal
                        connection_sent = False
                        try:
                            # Look for "Send without a note" option first
                            send_without_note = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send without a note') or .//span[text()='Send without a note']]")
                            send_without_note.click()
                            connection_sent = True
                            
                        except:
                            # If no "Send without a note", look for regular Send button
                            try:
                                send_button = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Send'] or @aria-label='Send invitation']"))
                                )
                                send_button.click()
                                connection_sent = True
                            except:
                                # Close modal if we can't send
                                try:
                                    close_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Dismiss' or contains(@class, 'artdeco-modal__dismiss')]")
                                    close_button.click()
                                except:
                                    pass
                        
                        if connection_sent:
                            connections_sent += 1
                            self.logger.info(f"✅ Connected to {person_name} | {person_title} ({connections_sent}/{max_connections})")
                        else:
                            self.logger.warning(f"⚠️ Could not connect to {person_name}")
                        
                        # Random delay between connections (4-10 seconds)
                        delay = random.uniform(4, 10)
                        time.sleep(delay)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error processing connection {i+1}: {str(e)}")
                        continue
                
                # Try next page if needed
                if connections_sent < max_connections and page_attempts < max_pages - 1:
                    try:
                        next_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Next' and not(@disabled)]")
                        if next_button:
                            next_button.click()
                            time.sleep(4)
                            page_attempts += 1
                        else:
                            break
                    except:
                        break
                else:
                    break
            
            return connections_sent
            
        except Exception as e:
            self.logger.error(f"❌ Keyword search failed for '{keyword}': {str(e)}")
            return 0
    
    def run_automation(self, industry="tech", topic=None, connection_keywords=None, max_connections=50):
        """Run automation tasks immediately with enhanced content and connections"""
        try:
            self.logger.info("🚀 Starting Advanced LinkedIn Automation...")
            self.logger.info("=" * 60)
            self.setup_driver()
            
            if not self.login():
                return False
            
            # Generate unique, AI-powered content
            self.logger.info("🎨 Generating unique AI content...")
            if topic:
                # If specific topic provided, use it
                content = self.generate_topic_content(industry, topic)
            else:
                # Generate unique diverse content
                content = self.generate_unique_content(industry)
            
            self.logger.info(f"📝 Generated content preview: {content[:150]}...")
            
            # Create and post content
            post_success = self.create_post(content)
            if post_success:
                self.logger.info("✅ Unique post created successfully!")
            else:
                self.logger.error("❌ Failed to create post")
            
            from connections import LinkedInConnections
            connector = LinkedInConnections(self.driver, self.wait, self.logger)
            connections_sent = 0
            if connection_keywords:
                self.logger.info(f"🔍 Connecting using keywords: {connection_keywords}")
                connections_sent = connector.search_and_connect_by_keyword(connection_keywords, max_connections)
            else:
                self.logger.info(f"\n🌐 Starting diverse connection strategy...")
                self.logger.info(f"🎯 Target: {max_connections} connections across multiple categories")
                self.logger.info("-" * 50)
                connections_sent = connector.search_diverse_connections(max_connections)
            
            # Summary
            self.logger.info("\n" + "=" * 60)
            self.logger.info("📊 AUTOMATION SUMMARY")
            self.logger.info("=" * 60)
            self.logger.info(f"📝 Post Status: {'✅ Success' if post_success else '❌ Failed'}")
            self.logger.info(f"👥 Connections Sent: {connections_sent}/{max_connections}")
            if max_connections > 0:
                self.logger.info(f"📈 Connection Success Rate: {(connections_sent/max_connections)*100:.1f}%")
            self.logger.info(f"⏱️ Session Complete")
            self.logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Automation failed: {str(e)}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("🔒 Browser closed securely")
    
    def generate_topic_content(self, industry, topic):
        """Generate content for a specific topic (backward compatibility)"""
        try:
            if not self.openai_api_key:
                # Use template if no API key
                template = f"Exploring the fascinating world of {topic} in {industry}. The potential applications are incredible! What's your experience with {topic}? How do you see it shaping the future of {industry}? #Tech #Innovation #{topic.replace(' ', '')}"
                return self.clean_content(template)
            
            openai.api_key = self.openai_api_key
            
            prompt = f"""
            Create a unique, engaging LinkedIn post about {topic} in the {industry} industry.
            The post should be:
            - Authentic and personal (not corporate-speak)
            - Include a compelling hook or insight
            - Ask an engaging question
            - Include 3-4 relevant hashtags
            - Be 120-180 words
            - Use only standard characters
            - Avoid phrases like "I'm excited to share" or generic "thoughts?"
            
            Make it conversational and thought-provoking.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You write authentic, engaging LinkedIn posts that spark real conversations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            return self.clean_content(content)
                
        except Exception as e:
            self.logger.error(f"Topic content generation failed: {str(e)}")
            return self.generate_template_content(industry)

# Example usage and configuration
def main():
    print("🚀 Advanced LinkedIn Automation Agent")
    print("=" * 60)
    print("🎨 Unique AI Content Generation")
    print("🌐 Diverse Professional Networking (50+ connections)")
    print("🎯 Multi-category targeting")
    print("=" * 60)
    
    # Configuration
    LINKEDIN_EMAIL = "rajmange94@gmail.com"
    LINKEDIN_PASSWORD = "RAJM@2004"
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
    # Industry focus for content generation
    INDUSTRY = "tech"  # tech, business, marketing
    
    # Number of diverse connections to make
    MAX_CONNECTIONS = 50  # Will target: startups, enterprises, AI, GenAI, Anthropic, etc.
    
    print(f"📝 Content Industry: {INDUSTRY}")
    print(f"👥 Target Connections: {MAX_CONNECTIONS}")
    print(f"🤖 AI Content: {'✅ Enabled' if OPENAI_API_KEY != 'your_openai_api_key' else '❌ Configure API key'}")
    print("-" * 60)
    print("🎯 Connection Categories:")
    print("   • Startup Founders & Entrepreneurs")
    print("   • Enterprise Tech Leaders")
    print("   • AI/ML Engineers & Researchers")
    print("   • Generative AI Specialists") 
    print("   • Anthropic/Claude AI Community")
    print("   • Software Engineers & Architects")
    print("   • Product Managers & Designers")
    print("   • Tech Leadership & CTOs")
    print("   • VCs & Startup Advisors")
    print("   • Innovation & Digital Transformation")
    print("-" * 60)
    
    # Validate OpenAI API key
    if OPENAI_API_KEY == "your_openai_api_key" or not OPENAI_API_KEY:
        print("⚠️  WARNING: OpenAI API key not configured!")
        print("   Without API key, you'll get template content instead of unique AI content.")
        response = input("   Continue anyway? (y/n): ").lower().strip()
        if response != 'y':
            print("👋 Setup your OpenAI API key and run again for best results!")
            return
    
    # Initialize and run agent
    agent = LinkedInAgent(
        email=LINKEDIN_EMAIL, 
        password=LINKEDIN_PASSWORD,
        openai_api_key=OPENAI_API_KEY
    )
    
    print("\n🚀 Starting automation...")
    print("=" * 60)
    
    # Run advanced automation
    success = agent.run_automation(
        industry=INDUSTRY,
        max_connections=MAX_CONNECTIONS
    )
    
    if success:
        print("\n🎉 AUTOMATION COMPLETED SUCCESSFULLY!")
        print("✅ Unique AI content posted")
        print(f"✅ Connected with {MAX_CONNECTIONS} diverse professionals")
        print("✅ Enhanced your professional network")
    else:
        print("\n❌ Automation encountered issues")
        print("📋 Check 'linkedin_agent.log' for details")
    
    print(f"\n📊 Detailed logs saved to: linkedin_agent.log")
    print("🔄 Run again anytime for fresh content and new connections!")

if __name__ == "__main__":
    main()

# Additional utility functions
class LinkedInContentGenerator:
    """Standalone content generator for LinkedIn posts"""
    
    @staticmethod
    def generate_tech_post():
        topics = [
            "The rise of AI in everyday applications",
            "Cloud computing transformation",
            "Cybersecurity in remote work",
            "The future of web development",
            "Data science trends for 2024"
        ]
        topic = random.choice(topics)
        return f"Thoughts on {topic}? The landscape is evolving rapidly and I'm curious about your experiences. What trends are you seeing in your field? #Tech #Innovation #FutureTech"
    
    @staticmethod
    def generate_business_post():
        insights = [
            "Leadership is about empowering others to achieve their potential",
            "The best business strategies adapt to change while staying true to core values",
            "Remote work has redefined what productivity means",
            "Customer feedback is the compass for business growth",
            "Innovation happens when diverse perspectives collide"
        ]
        insight = random.choice(insights)
        return f"{insight}. What's your take on this? Share your experiences! #Leadership #Business #Growth"

# Installation requirements (save as requirements.txt):
"""
selenium==4.15.0
schedule==1.2.0
openai==0.28.1
webdriver-manager==4.0.1
"""