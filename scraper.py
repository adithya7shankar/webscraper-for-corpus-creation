import argparse
import requests
from bs4 import BeautifulSoup
import html2text
import os
import datetime
import time
from playwright.sync_api import sync_playwright

def generate_unique_filename(base_filename="scraped_content"):
    """Generates a unique filename by appending a timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_filename}_{timestamp}.md"

def scrape_urls(urls):
    """
    Scrapes content from a list of URLs and returns the combined Markdown content.

    Args:
        urls (list): A list of URLs to scrape.

    Returns:
        str: Combined Markdown content from all URLs.
    """
    all_markdown_content = ""
    errors = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True) # Consider headless=False for debugging
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
        except Exception as e:
            errors.append(f"Failed to launch Playwright browser: {e}. Make sure browser binaries are installed by running 'playwright install'.")
            print(f"Failed to launch Playwright browser: {e}. Make sure browser binaries are installed by running 'playwright install'.")
            # If browser fails to launch, we can't process any URLs that need it.
            # We could try to fall back to requests for all, or just error out.
            # For now, let's add errors for all URLs if playwright is needed and failed.
            for u in urls:
                 all_markdown_content += f"# Error processing {u}\n\nPlaywright browser launch failed. Ensure 'playwright install' has been run.\n\n---\n\n"
            return all_markdown_content, errors


        for url in urls:
            page_content_html = None
            try:
                print(f"Scraping {url}...")
                
                if "reddit.com" in url:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=60000) # Increased timeout

                    # Scroll to load dynamic content (especially comments)
                    # This is a common strategy for infinite scroll pages or lazy-loaded comments
                    scroll_attempts = 5 # Number of times to scroll
                    scroll_delay = 3  # Seconds to wait between scrolls for content to load
                    
                    print(f"Scrolling page for {url} to load comments...")
                    for i in range(scroll_attempts):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        print(f"Scroll attempt {i+1}/{scroll_attempts}, waiting {scroll_delay}s...")
                        time.sleep(scroll_delay)
                        # Optional: Check if a "load more comments" button is visible and click it
                        # load_more_button = page.query_selector('button:has-text("load more comments")') # Example selector
                        # if load_more_button and load_more_button.is_visible():
                        #     load_more_button.click()
                        #     time.sleep(scroll_delay) # Wait after click

                    page_content_html = page.content()
                    page.close()

                else: # For non-Reddit URLs, use requests (faster for static sites)
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    page_content_html = response.text

                if not page_content_html:
                    raise ValueError("Failed to retrieve page content.")

                soup = BeautifulSoup(page_content_html, 'html.parser')
                h = html2text.HTML2Text()
                h.ignore_links = False # Set to True if you want to remove links
                h.ignore_images = True
                
                extracted_html_for_markdown = ""

                if "reddit.com" in url:
                    # Using the selectors identified previously, now on Playwright-loaded content
                    post_content_area = soup.find('shreddit-post')
                    if post_content_area:
                        extracted_html_for_markdown += str(post_content_area)
                    else: # Fallback if shreddit-post not found
                        article_tag = soup.find('article') # A common tag for main content
                        if article_tag:
                            extracted_html_for_markdown += str(article_tag)
                        # else: # Avoid adding whole body if specific tags are expected for Reddit
                        #    print(f"Warning: Could not find <shreddit-post> or <article> for Reddit URL {url}")


                    comments_area = soup.find_all('shreddit-comment')
                    if comments_area:
                        for comment_element in comments_area:
                            extracted_html_for_markdown += str(comment_element)
                    # else:
                    #    print(f"Warning: Could not find <shreddit-comment> elements for Reddit URL {url}")
                    
                    if not extracted_html_for_markdown: # If no specific elements found even after Playwright
                        print(f"No specific Reddit content (post/comments) found for {url} even with Playwright. Using full page.")
                        # Fallback to a broader extraction if specific tags fail
                        # This could be the body, or a main content div if identifiable
                        main_div = soup.find("div", id="main-content") # Example, Reddit's main content div ID might vary
                        if main_div:
                             extracted_html_for_markdown = str(main_div)
                        else:
                             extracted_html_for_markdown = soup.prettify() # Whole page as last resort

                else: # For non-Reddit URLs
                    main_content = soup.find('main')
                    if not main_content:
                        main_content = soup.find('article')
                    if not main_content:
                        main_content = soup.find('div', role='main')
                    
                    if main_content:
                        extracted_html_for_markdown = str(main_content)
                    else:
                        extracted_html_for_markdown = page_content_html # Full HTML

                markdown_content = h.handle(extracted_html_for_markdown)
                all_markdown_content += f"# Content from {url}\n\n"
                all_markdown_content += markdown_content.strip()
                all_markdown_content += "\n\n---\n\n"

            except requests.exceptions.RequestException as e: # For non-Reddit URLs using requests
                error_message = f"Error scraping {url} with requests: {e}"
                print(error_message)
                errors.append(error_message)
                all_markdown_content += f"# Error scraping {url}\n\n{str(e)}\n\n---\n\n"
            except Exception as e: # Catch Playwright errors or other general errors
                error_message = f"An unexpected error occurred while processing {url}: {e}"
                print(error_message)
                errors.append(error_message)
                all_markdown_content += f"# Unexpected error processing {url}\n\n{str(e)}\n\n---\n\n"
        
        try:
            browser.close()
        except Exception as e:
            print(f"Error closing Playwright browser: {e}")
            errors.append(f"Error closing Playwright browser: {e}")
            error_message = f"Error scraping {url}: {e}"
            print(error_message)
            errors.append(error_message)
            all_markdown_content += f"# Error scraping {url}\n\n{str(e)}\n\n---\n\n"
        except Exception as e:
            error_message = f"An unexpected error occurred while processing {url}: {e}"
            print(error_message)
            errors.append(error_message)
            all_markdown_content += f"# Unexpected error processing {url}\n\n{str(e)}\n\n---\n\n"
    
    return all_markdown_content, errors

def save_content_to_file(content, output_filename="scraped_content.md"):
    """
    Saves the given content to a Markdown file.

    Args:
        content (str): The content to save.
        output_filename (str): The name of the Markdown file.

    Returns:
        str: The output filename if successful, None otherwise.
    """
    try:
        # Ensure the 'scraped_files' directory exists
        output_dir = "scraped_files"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        filepath = os.path.join(output_dir, output_filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content successfully saved to {filepath}")
        return filepath
    except IOError as e:
        print(f"Error writing to file {filepath}: {e}")
        return None

# This part is for command-line usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape websites and save content to a Markdown file.")
    parser.add_argument('urls', metavar='URL', type=str, nargs='+',
                        help='One or more URLs to scrape.')
    parser.add_argument('-o', '--output', type=str,
                        help='Output Markdown file name (e.g., my_output.md). A timestamp will be added automatically.')

    args = parser.parse_args()
    
    markdown_data, scrape_errors = scrape_urls(args.urls)
    
    if markdown_data:
        if args.output:
            # Remove .md if user added it, as generate_unique_filename will add it
            base_name = args.output.replace(".md", "")
            output_file = generate_unique_filename(base_name)
        else:
            output_file = generate_unique_filename()
            
        saved_path = save_content_to_file(markdown_data, output_file)
        if saved_path:
            print(f"Scraped content saved to: {saved_path}")
        else:
            print("Failed to save scraped content.")
    else:
        print("No content was scraped.")

    if scrape_errors:
        print("\nEncountered errors during scraping:")
        for err in scrape_errors:
            print(f"- {err}")
