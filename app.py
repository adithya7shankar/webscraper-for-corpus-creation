import os
from flask import Flask, render_template, request, send_from_directory, flash
import scraper  # Import the modified scraper module

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Needed for flashing messages

# Configuration for uploaded files
UPLOAD_FOLDER = 'scraped_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        urls_string = request.form.get('urls')
        output_base_name = request.form.get('output_filename')

        if not urls_string:
            flash('Please enter at least one URL.', 'error')
            return render_template('index.html')

        urls = [url.strip() for url in urls_string.splitlines() if url.strip()]
        if not urls:
            flash('No valid URLs provided after stripping whitespace.', 'error')
            return render_template('index.html')

        try:
            markdown_content, errors = scraper.scrape_urls(urls)

            if errors:
                for error in errors:
                    flash(f"Scraping error: {error}", 'warning')

            if not markdown_content.strip() and not errors:
                flash('No content could be scraped from the provided URLs.', 'info')
                return render_template('index.html')
            elif not markdown_content.strip() and errors:  # Only errors, no content
                return render_template('index.html')

            if output_base_name:
                # Remove .md if user added it, as generate_unique_filename will add it
                base_name = output_base_name.replace(".md", "")
                output_filename = scraper.generate_unique_filename(base_name)
            else:
                output_filename = scraper.generate_unique_filename()

            saved_filepath = scraper.save_content_to_file(markdown_content, output_filename)

            if saved_filepath:
                flash(f"Content successfully scraped and saved!", 'success')
                # Pass only the filename for the download link
                return render_template('index.html', filename=output_filename, scraped_content=markdown_content)
            else:
                flash('Failed to save the scraped content.', 'error')
                return render_template('index.html')

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", 'error')
            return render_template('index.html')

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found.', 'error')
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
