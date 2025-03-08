# pod2book
Convert podcasts to eBooks.

Find out the story at [pod2book.com/about](pod2book.com/about)

"Stop, collaborate and don’t listen–Read instead. Easily convert your podcast to an eBook using AI. Help the neurodivergent, deaf, hard of hearing, or people who just like to read." 

Yes, I said "AI"...It's all the rage these days.

The conversion happens using the [open.ai Whisper](https://openai.com/index/whisper/) general model.
You can change the language and model size on this line `whisper.load_model("medium.en")`. It may run faster or slower with more (or less) accuracy using other models. All's I can say is to test it out and see what happens.

It doesn't currently do diarization (speaker identification). I've started working on this in the `diarization` branch, but haven't gotten too far. PR's are welcome.

# Current Features
* AI Speech-to-text
* Podcast thumbnail image becomes the eBook cover
* Each podcast episode becomes an eBook chapter
* Customizable "Copyright" page

## Local Installation

```sh
git clone https://github.com/EISMGard/pod2book
cd pod2book
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the program

### Configuration
First, get the *real* podcast RSS feed URL using a tool like https://getrssfeed.com/. Please note for example that it won't work with an Apple or Spotify Podcast URL. So, go get the correct podcast URL to save yourself some time.

### Command Line Arguments
`usage: pod2book.py [-h] [--start START] [--end END] [--license LICENSE] rss_url`

#### No Arguments

`python pod2book.py https://podcastrss.feed`
* If no options are provided, the program will attempt to convert all podcast episodes available from the source URL. The conversion happens in realtime + some change, which can vary significantly with the model used, so are you sure you want all 1000 of Roe Jogan's episodes that are 5 hours each?

#### Range of Episodes

`python pod2book.py https://podcastrss.feed --start 100 --end 150`
* Adding a range of episodes

#### Custom License

`python pod2book.py https://podcastrss.feed --start 100 --end 150 --license 'Ben Francom Custom License: This Pocast is copyrighted© and licensed to MY MOM!!!'`
