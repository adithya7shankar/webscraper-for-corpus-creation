import ollama
import os
import glob

# Configuration
MODEL_NAME = 'llama3'
SCRAPED_FILES_DIR = 'scraped_files'
PROMPT_TEMPLATE = """
Please clean up the following markdown content.
Focus on:
- Fixing any formatting inconsistencies (e.g., extra newlines, improper heading levels).
- Removing any clearly redundant or boilerplate text that might have been picked up during scraping.
- Ensuring the markdown is well-structured and readable.
- Correcting any obvious grammatical errors or typos if possible, but prioritize structure and formatting.
- Do not add any new content or commentary. Only refine the existing text.
- Preserve code blocks and their original formatting as much as possible.

Markdown content to clean:
---
{markdown_content}
---
Cleaned markdown:
"""

def clean_markdown_content(markdown_text):
    """
    Uses Ollama to clean the provided markdown text.
    """
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    'role': 'user',
                    'content': PROMPT_TEMPLATE.format(markdown_content=markdown_text),
                }
            ]
        )
        return response['message']['content'].strip()
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        return None

def process_markdown_files():
    """
    Processes all markdown files in the SCRAPED_FILES_DIR.
    """
    if not os.path.exists(SCRAPED_FILES_DIR):
        print(f"Directory not found: {SCRAPED_FILES_DIR}")
        return

    markdown_files = glob.glob(os.path.join(SCRAPED_FILES_DIR, '*.md'))

    if not markdown_files:
        print(f"No markdown files found in {SCRAPED_FILES_DIR}")
        return

    print(f"Found {len(markdown_files)} markdown files to process.")

    for filepath in markdown_files:
        print(f"\nProcessing file: {filepath}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()

            if not original_content.strip():
                print(f"File {filepath} is empty. Skipping.")
                continue

            print("Sending to Llama3 for cleanup...")
            cleaned_content = clean_markdown_content(original_content)

            if cleaned_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                print(f"Successfully cleaned and updated: {filepath}")
            else:
                print(f"Failed to clean (or Ollama error): {filepath}. File not modified.")

        except Exception as e:
            print(f"Error processing file {filepath}: {e}")

if __name__ == '__main__':
    # Make sure Ollama server is running.
    # You might need to start it by running `ollama serve` in your terminal
    # or by opening the Ollama desktop application.
    print("Starting markdown cleanup process...")
    print(f"Using model: {MODEL_NAME}")
    print("Ensure the Ollama application is running or `ollama serve` has been executed.")
    process_markdown_files()
    print("\nMarkdown cleanup process finished.")
