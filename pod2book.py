import os
import sys
import argparse
import feedparser
import requests
from datetime import datetime
from ebooklib import epub
import whisper
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def transcribe_audio(audio_file):
    try:
        model = whisper.load_model("medium.en")
        result = model.transcribe(audio_file)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing audio: {audio_file}: {e}")
        return ""

def create_ebook(podcast_title, podcast_author, chapter_texts, cover_img_path, output_directory):
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title(podcast_title)
    book.set_language('en')
    book.add_author(podcast_author)

    if os.path.exists(cover_img_path):
        book.set_cover("cover.jpg", open(cover_img_path, 'rb').read())

    # Create the intro chapter with clickable link
    intro_chapter = epub.EpubHtml(
        title="About pod2book",
        file_name="about_pod2book.xhtml",
        lang="en"
    )

    intro_chapter.content = (
        f"<h1>{podcast_title}</h1>"
        f"<h3>by {podcast_author}</h3>"
        '<p>This eBook was created using pod2book. '
        'Find out more at <a href="https://pod2book.com">pod2book.com</a>.</p>'
    )

#    for i, (chapter_title, _) in enumerate(chapter_texts):
#        intro_content += f'<li><a href="chapter_{i+1}.xhtml">{chapter_title}</a></li>'
#    intro_content += "</ul>"
#    intro_chapter.content = intro_content
    book.add_item(intro_chapter)

    # Add each episode as a chapter
    chapters = []
    for i, (chapter_title, chapter_content) in enumerate(chapter_texts):
        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter_{i+1}.xhtml',
            lang='en'
        )
        chapter.content = (
            f'<h1>{chapter_title}</h1>'
            f'<p>{chapter_content}</p>'
        )
        book.add_item(chapter)
        chapters.append(chapter)

    # Add final page with the same message from the introduction
    final_page = epub.EpubHtml(
        title="About pod2book",
        file_name="about.xhtml",
        lang="en"
    )
    final_page.content = (
        '<p>This eBook was created using pod2book. '
        'Find out more at <a href="https://pod2book.com">pod2book.com</a>.</p>'
    )
    book.add_item(final_page)
    chapters.append(final_page)

    # Add cover image as the last page
    cover_page = epub.EpubHtml(
        title="Back Cover",
        file_name="cover.xhtml",
        lang="en"
    )
    cover_page.content = (
        '<img src="cover.jpg" alt="Cover Image" style="width:100%; height:auto;"/>'
    )
    book.add_item(cover_page)
    chapters.append(cover_page)

    # Define Table of Contents
    book.toc = (
        epub.Link(intro_chapter.file_name, intro_chapter.title, 'intro'),
        (epub.Section('Episodes'), chapters),
    )

    # Add default NCX and Nav files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define CSS style
    style = 'BODY {color: black;}'
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(nav_css)

    # Set the order of the chapters
    book.spine = ['nav', intro_chapter] + chapters

    # Write the EPUB file to the output directory
    epub_filename = os.path.join(output_directory, f"{podcast_title}.epub")
    epub.write_epub(epub_filename, book, {})

def download_podcast(rss_url, start, end):
    # Parse the RSS feed
    feed = feedparser.parse(rss_url)

     # Debugging statement to check if feed is parsed correctly
    print(f"Feed Title: {feed.feed.title}")
    print(f"Number of entries in feed: {len(feed.entries)}")
    

    podcast_title = feed.feed.title
    podcast_author = feed.feed.author if 'author' in feed.feed else 'Unknown Author'
    episodes = feed.entries

    # Sort episodes in chronological order
    episodes = sorted(episodes, key=lambda e: e.published_parsed)

    # Slice the episodes list to get the specified range
    episodes = episodes[start:end]
    print(f"Number of episodes to download: {len(episodes)}")

    # Create a directory named after the podcast title
    download_directory = podcast_title
    os.makedirs(download_directory, exist_ok=True)

    # Download cover image if available
    cover_img_path = os.path.join(download_directory, 'cover.jpg')
    if 'image' in feed.feed and 'href' in feed.feed.image:
        cover_url = feed.feed.image.href
        if not os.path.exists(cover_img_path):
            response = requests.get(cover_url)
            with open(cover_img_path, 'wb') as f:
                f.write(response.content)

    # Set up retry strategy
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    # Collect chapter texts
    chapter_texts = []
    for episode in episodes:
        try:
            print(f"Processing episode: {episode.title}")
            # Download the episode audio
            audio_url = episode.enclosures[0].href
            audio_filename = os.path.join(download_directory, os.path.basename(audio_url))
            if not os.path.exists(audio_filename):
                response = http.get(audio_url, stream=True)
                with open(audio_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # Transcribe the audio
            transcription = transcribe_audio(audio_filename)

            chapter_title = episode.title
            chapter_content = transcription
            chapter_texts.append((chapter_title, chapter_content))

            # Remove the MP3 file after processing
            os.remove(audio_filename)
        except Exception as e:
            print(f"Error processing episode: {episode.title}")
            print(e)
        print(f"Total chapters collected: {len(chapter_texts)}")
    create_ebook(podcast_title, podcast_author, chapter_texts, cover_img_path, download_directory)

def main():
    parser = argparse.ArgumentParser(description='Download podcast episodes, convert audio to text, and create an ebook.')
    parser.add_argument('rss_url', type=str, help='The RSS feed URL of the podcast')
    parser.add_argument('--start', type=int, default=0, help='The starting index of episodes to download (inclusive)')
    parser.add_argument('--end', type=int, default=None, help='The ending index of episodes to download (exclusive)')

    args = parser.parse_args()

    # Call the podcast download function with the specified range
    download_podcast(args.rss_url, args.start, args.end)

if __name__ == '__main__':
    main()