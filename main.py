import json
import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


with open('input_data.json', 'r') as file:
    journal_data = json.load(file)

options = Options()
options.headless = False 
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def scrape_ieee(journal):
    print("IEEE scraping start")
    
    # Extract details from the journal dictionary
    base_url = journal["link"]
    volume = journal["volume"]
    issues_from = journal["issuesFrom"]
    issues_to = journal["issuesTo"]
    
    # Open the CSV file to store results
    with open('ieee_journals.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Journal", "Volume", "Issue", "Title of Research Paper", "First Author (Name)", 
                         "First Author Affiliation (Uni/Org name)", "First Author Affiliation (Country Name)", 
                         "Is this a collaborative work?", "Collaborating uni/org 1", "Collaborating uni/org 2"])
        
        # Navigate to the journal's page
        search_url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={journal['title']}"
        driver.get(search_url)
        time.sleep(3)  # Allow the page to load

        try:
            # Find and click on the journal publication
            print(f"Looking for publication: {journal['title']}")
            journal_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f'div[data-tealium_data*="{journal["title"]}"]'))
            )
            journal_element.click()
            time.sleep(2)

            # Click on "All Issues" link
            all_issues_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[title="All Issues"]'))
            )
            all_issues_link.click()
            time.sleep(5)
            
            # Navigate through decade categories to find our volume
            decade_found = False
            decade_categories = driver.find_elements(By.CSS_SELECTOR, '.issue-details-past-tabs li a')

            time.sleep(4)
            
            print('decade cat len: ', len(decade_categories))
            
            for decade in decade_categories:
                if decade_found:
                    break
                    
                decade_text = decade.text.strip()
                print(f"Checking decade category: {decade_text}")
                
                # Click on the decade tab
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(decade))
                ActionChains(driver).move_to_element(decade).click().perform()
                time.sleep(2)
                
                # Now look at the years available in this decade
                year_links = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.issue-details-past-tabs.year li a'))
                )
                
                time.sleep(2)
                
                print("year links len: ", len(year_links))
                
                # Check each year
                for year_link in year_links:
                    year_text = year_link.text.strip()
                    print(f"  Checking year: {year_text}")
                    
                    # Click on the year
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(year_link))
                    ActionChains(driver).move_to_element(year_link).click().perform()
                    time.sleep(2)
                    
                    # Look for our volume in the volumes list
                    volume_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.issue-container div strong'))
                    )
                    
                    time.sleep(2)
                    
                    for vol_elem in volume_elements:
                        vol_text = vol_elem.text.strip()
                        if vol_text == f"Volume {volume}":
                            print(f"Found Volume {volume} in {year_text}")
                            decade_found = True
                            
                            # Now get all issues for this volume
                            issue_links = WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located(
                                    (By.XPATH, f"//strong[contains(text(), 'Volume {volume}')]/../../div/div[@class='issue-details']/a")
                                )
                            )
                            
                            print(f"Found {len(issue_links)} issues for Volume {volume}")
                            
                            # Process each issue within our range
                            for issue_link in issue_links:
                                issue_text = issue_link.text.strip()
                                issue_num = int(issue_text.replace("Issue ", "").strip())
                                
                                if issues_from <= issue_num <= issues_to:
                                    print(f"Processing Volume {volume}, {issue_text}")
                                    
                                    # Store current window handle to return to later
                                    main_window = driver.current_window_handle
                                    
                                    # Click on the issue - opening in new tab to preserve navigation
                                    ActionChains(driver).key_down(Keys.CONTROL).click(issue_link).key_up(Keys.CONTROL).perform()
                                    time.sleep(2)
                                    
                                    # Switch to the new tab
                                    new_window = [handle for handle in driver.window_handles if handle != main_window][0]
                                    driver.switch_to.window(new_window)
                                    time.sleep(3)
                                    
                                    # Extract articles on this issue page
                                    article_containers = WebDriverWait(driver, 10).until(
                                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.hide-mobile'))
                                    )
                                    
                                    # Find all articles using the structure from the example
                                    time.sleep(3)
                                    
                                    articles = driver.find_elements(By.CSS_SELECTOR, 'div.result-item')
                                    print(f"Found {len(articles)} articles in {issue_text}")
                                    
                                    for article in articles:
                                        try:
                                            # Extract article title
                                            title_element = article.find_element(By.CSS_SELECTOR, 'h2 a')
                                            title = title_element.text.strip()
                                            print(f"Processing article: {title}")
                                            
                                            # Extract author information
                                            authors_section = article.find_element(By.CSS_SELECTOR, 'xpl-authors-name-list p.author')
                                            author_links = authors_section.find_elements(By.CSS_SELECTOR, 'a')
                                            
                                            if len(author_links) > 0:
                                                first_author = author_links[0].text.strip()
                                                is_collaborative = "Yes" if len(author_links) > 1 else "No"
                                                
                                                # Click on first author to get affiliation
                                                ActionChains(driver).move_to_element(author_links[0]).click().perform()
                                                time.sleep(2)
                                                
                                                try:
                                                    # Try to extract affiliation from popup
                                                    affiliation_element = WebDriverWait(driver, 5).until(
                                                        EC.presence_of_element_located((By.CSS_SELECTOR, '.author-card-container .author-card-affiliation'))
                                                    )
                                                    affiliation = affiliation_element.text.strip()
                                                    
                                                    # Parse affiliation to get org and country
                                                    affiliation_parts = affiliation.split(',')
                                                    org = affiliation_parts[0].strip() if len(affiliation_parts) > 0 else "N/A"
                                                    country = affiliation_parts[-1].strip() if len(affiliation_parts) > 1 else "N/A"
                                                    
                                                    # Close the popup
                                                    close_button = WebDriverWait(driver, 5).until(
                                                        EC.element_to_be_clickable((By.CSS_SELECTOR, '.popup-close-button'))
                                                    )
                                                    close_button.click()
                                                    time.sleep(2)
                                                except:
                                                    org = "N/A"
                                                    country = "N/A"
                                                
                                                # Get collaborating organizations if applicable
                                                collab_org1 = "N/A"
                                                collab_org2 = "N/A"
                                                
                                                if is_collaborative == "Yes":
                                                    # Process second author if exists
                                                    if len(author_links) > 1:
                                                        try:
                                                            ActionChains(driver).move_to_element(author_links[1]).click().perform()
                                                            time.sleep(2)
                                                            
                                                            affiliation_element = WebDriverWait(driver, 5).until(
                                                                EC.presence_of_element_located((By.CSS_SELECTOR, '.author-card-container .author-card-affiliation'))
                                                            )
                                                            collab_affiliation = affiliation_element.text.strip()
                                                            collab_org1 = collab_affiliation.split(',')[0].strip() if len(collab_affiliation.split(',')) > 0 else "N/A"
                                                            
                                                            # Close the popup
                                                            close_button = WebDriverWait(driver, 5).until(
                                                                EC.element_to_be_clickable((By.CSS_SELECTOR, '.popup-close-button'))
                                                            )
                                                            close_button.click()
                                                            time.sleep(2)
                                                        except:
                                                            collab_org1 = "N/A"
                                                    
                                                    # Process third author if exists
                                                    if len(author_links) > 2:
                                                        try:
                                                            ActionChains(driver).move_to_element(author_links[2]).click().perform()
                                                            time.sleep(2)
                                                            
                                                            affiliation_element = WebDriverWait(driver, 5).until(
                                                                EC.presence_of_element_located((By.CSS_SELECTOR, '.author-card-container .author-card-affiliation'))
                                                            )
                                                            collab_affiliation = affiliation_element.text.strip()
                                                            collab_org2 = collab_affiliation.split(',')[0].strip() if len(collab_affiliation.split(',')) > 0 else "N/A"
                                                            
                                                            # Close the popup
                                                            close_button = WebDriverWait(driver, 5).until(
                                                                EC.element_to_be_clickable((By.CSS_SELECTOR, '.popup-close-button'))
                                                            )
                                                            close_button.click()
                                                            time.sleep(2)
                                                        except:
                                                            collab_org2 = "N/A"
                                            else:
                                                first_author = "N/A"
                                                org = "N/A"
                                                country = "N/A"
                                                is_collaborative = "No"
                                                collab_org1 = "N/A"
                                                collab_org2 = "N/A"
                                            
                                            # Write the data to CSV
                                            writer.writerow([
                                                journal['title'], 
                                                volume,
                                                issue_num,
                                                title,
                                                first_author,
                                                org,
                                                country,
                                                is_collaborative,
                                                collab_org1,
                                                collab_org2
                                            ])
                                            
                                        except Exception as article_error:
                                            print(f"Error processing article: {article_error}")
                                    
                                    # Close current tab and switch back to main window
                                    driver.close()
                                    driver.switch_to.window(main_window)
                                    time.sleep(1)
                            
                            break  # Break the volume loop once we've found our volume
                    
                    if decade_found:
                        break  # Break the year loop if our volume is found
                
                if decade_found:
                    break  # Break the decade loop if we've found our volume
                    
            if not decade_found:
                print(f"Could not find Volume {volume} in any of the decades/years")
                
        except Exception as e:
            print(f"Error during scraping: {e}")
            traceback.print_exc()  # Print the full traceback for debugging
    
    print("IEEE scraping finished.")
                       

def scrape_sagepub(journal):
    pass


def main():
    print('main')
    for journal in journal_data:
        if journal["source"].lower() == "ieee":
            scrape_ieee(journal)
        elif journal["source"].lower() == "sagepub":
            scrape_sagepub(journal)
        break

if __name__ == "__main__":
    main()

    driver.quit()
