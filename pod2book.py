import feedparser
import requests
import os
import argparse
import shutil
import whisper
from ebooklib import epub

# Function to download the podcast episodes and cover photo
def download_podcast(rss_url):
    # Parse the RSS feed
    feed = feedparser.parse(rss_url)
    
    # Get podcast metadata and set the download directory based on the podcast title
    podcast_title = feed['feed']['title']
    podcast_author = feed['feed'].get('author', 'Unknown Author')
    sanitized_title = "".join(x for x in podcast_title if x.isalnum() or x.isspace()).replace(" ", "_")
    download_directory = os.path.join(os.getcwd(), sanitized_title)
    
    # Create download directory if it doesn't exist
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    
    print(f"Podcast Title: {podcast_title}")
    print(f"Podcast Author: {podcast_author}")
    print(f"Download Directory: {download_directory}")
    
    # Download the cover image if available
    podcast_cover_url = feed['feed'].get('image', {}).get('href')
    if podcast_cover_url:
        cover_img_path = os.path.join(download_directory, 'cover.jpg')
        print(f"Downloading cover image from {podcast_cover_url}...")
        download_file(podcast_cover_url, cover_img_path)
    else:
        print("No cover image found.")
    
    # Load Whisper model
    model = whisper.load_model("base")
    
    # Store chapter texts for the ebook
    chapter_texts = []
    
    # Iterate through all episodes in the RSS feed
    for i, entry in enumerate(feed.entries):
        episode_title = entry.title
        audio_url = entry.enclosures[0]['href'] if entry.enclosures else None
        
        if audio_url:
            # Format the filename
            sanitized_episode_title = "".join(x for x in episode_title if x.isalnum())
            audio_filename = f"{sanitized_episode_title}.mp3"
            audio_path = os.path.join(download_directory, audio_filename)
            
            print(f"Downloading episode: {episode_title}")
            download_file(audio_url, audio_path)
            
            # Convert audio to text using Whisper
            text = convert_audio_to_text_whisper(audio_path, model)
            chapter_texts.append((episode_title, text))
        else:
            print(f"No audio file found for episode: {episode_title}")
    
    # Ensure chronological order by reversing the list
    chapter_texts.reverse()
    
    # Generate the ebook with author info and a TOC page at the beginning
    create_epub(podcast_title, podcast_author, chapter_texts, download_directory)

    # Clean up temporary files
    cleanup_files(download_directory)

# Helper function to download a file from a URL
def download_file(url, dest_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        print(f"Downloaded {dest_path}")
    else:
        print(f"Failed to download {url}")

# Convert audio file to text using Whisper
def convert_audio_to_text_whisper(audio_path, model):
    print(f"Converting audio to text with Whisper: {audio_path}")
    # Transcribe audio using Whisper
    result = model.transcribe(audio_path)
    print(f"Transcription complete for {audio_path}")
    return result["text"]

# Create an EPUB file with author info, TOC page, and chapter texts
def create_epub(podcast_title, podcast_author, chapter_texts, download_directory):
    print(f"Creating EPUB for {podcast_title}")
    
    book = epub.EpubBook()
    
    # Set metadata
    book.set_identifier('id123456')
    book.set_title(podcast_title)
    book.set_language('en')
    book.add_author(podcast_author)
    
    # Add cover image if available
    cover_img_path = os.path.join(download_directory, 'cover.jpg')
    if os.path.exists(cover_img_path):
        book.set_cover("cover.jpg", open(cover_img_path, 'rb').read())
    
    # Add an introductory TOC page
    intro_chapter = epub.EpubHtml(title="Table of Contents", file_name="toc.xhtml", lang="en")
    intro_content = f"<h1>{podcast_title}</h1><h3>by {podcast_author}</h3><h2>Table of Contents</h2><ul>"
    for i, (chapter_title, _) in enumerate(chapter_texts):
        intro_content += f'<li><a href="chapter_{i+1}.xhtml">{chapter_title}</a></li>'
    intro_content += "</ul>"
    intro_chapter.content = intro_content
    book.add_item(intro_chapter)
    
    # Add each episode as a chapter
    chapters = []
    for i, (chapter_title, chapter_content) in enumerate(chapter_texts):
        chapter = epub.EpubHtml(title=chapter_title, file_name=f'chapter_{i+1}.xhtml', lang='en')
        chapter.content = f'<h1>{chapter_title}</h1><p>{chapter_content}</p>'
        book.add_item(chapter)
        chapters.append(chapter)
    
    # Define Table Of Contents with clickable links to chapters
    #book.toc = [epub.Link(ch.file_name, ch.title, f"toc_{i}") for i, ch in chapters]
    #book.toc = [epub.Link(ch.file_name, ch.title, f"toc_{i}") for i, ch in enumerate(chapters)]

    
    # Add default NCX and Nav files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define CSS style
    style = 'BODY {color: black;}'
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)
    
    # Create spine in reading order with TOC at the beginning
    book.spine = ['nav', intro_chapter] + chapters
    
    # Write to the file
    epub_path = os.path.join(download_directory, f'{podcast_title}.epub')
    epub.write_epub(epub_path, book, {})
    print(f"EPUB created: {epub_path}")

# Clean up downloaded and temporary files
def cleanup_files(download_directory):
    print(f"Cleaning up files in {download_directory}...")
    # Remove all files except the EPUB and cover image
    for item in os.listdir(download_directory):
        item_path = os.path.join(download_directory, item)
        if item_path.endswith(".epub") or item == "cover.jpg":
            continue
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
    print("Cleanup complete.")

# Command-line interface
def main():
    parser = argparse.ArgumentParser(description='Download podcast episodes, convert audio to text, and create an ebook.')
    parser.add_argument('rss_url', type=str, help='The RSS feed URL of the podcast')

    args = parser.parse_args()

    # Call the podcast download function
    download_podcast(args.rss_url)

if __name__ == '__main__':
    main()
