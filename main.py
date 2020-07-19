import re  # Regexes
import sys  # To create the directory to save the subs in, and for sys.exit()
from pathlib import Path

import requests  # For HTTP requests
from bs4 import BeautifulSoup

# Constants

VIDEO_JSON_BASE_URL: str = "https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/"
USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
DOWNLOAD_DIR = "subs/"

# Start with main() near the bottom of the file

def save_file(data: str, filename: str):
    """Saves text data to a file. Does NOT check if file or directory exists
    beforehand."""
    f = open(filename, "w")

    f.write(data)

    f.close()


def get_vlive_html(url: str) -> str:
    """Sends a GET request to the vlive video URL and returns its HTML content."""

    if not is_valid_vlive_url(url):
        print(f"URL '{url}' is not a valid vlive.tv/video address.")
        sys.exit(1)

    # We don't actually need the headers for the request, but it will help the scraper
    # look more like a real human
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    print("Sending GET request to " + url)

    response = requests.get(url, headers=headers)

    # Check status code for 200 OK ?
    print(f"Received response, status code {response.status_code}\n")

    return response.text


def is_valid_vlive_url(url: str) -> bool:
    """Uses a regex to check if the given url is a valid 'vlive.tv./video/' address."""

    # VLIVE videos are only identified by numbers in the url (unlike Youtube IDs,
    # for example)
    vlive_url_regex = r"(vlive\.tv\/video\/[0-9]*)"

    if not re.search(vlive_url_regex, url):
        return False

    return True


def get_video_metadata(html: str) -> (str, str, str, str):
    """Extracts the video metadata from the the HTML.
    
    This data includes:
    - Upload date
    - Channel
    - Video title
    - Canonical link (we can also get this one from the url)"""
    soup = BeautifulSoup(html, features="html.parser")

    # Finds a <meta> element that looks like this:
    # <meta name="description" content="{date} - [{channel}] - {video title} - You can watch videos on V LIVE.">
    meta_description = soup.find("meta", attrs={"name": "description"})

    if meta_description is None:
        print('Could not find <meta> element with attribute name="description"')
        sys.exit(1)

    elements = meta_description["content"].split(" - ")

    # Hard coded, but we know the expected amount and the order of the elements
    upload_date = elements[0]

    # Get everything between the 1st index and the second-to-last, to eliminate the square brackets
    channel = elements[1][1:-1]

    video_title = elements[2]

    # Finds a <link> element that looks like this:
    # <link rel="canonical" href="https://www.vlive.tv/video/12345678"/>
    # We need this link to populate a referrer header that we will use later
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})

    if canonical_tag is None:
        print('Could not find <link> element with attribute rel="canonical"')
        sys.exit(1)

    # Get the actual link
    canonical_link = canonical_tag["href"]

    return upload_date, channel, video_title, canonical_link


def get_video_id_and_key(html: str) -> (str, str):
    """Extracts the video ID and key from the script attached to the HTML.
    
    These are used to send a request to an address in a Naver domain that contains a
    JSON file with all the data for the video, including captions."""

    # Define regexes globally / in another file ?
    # Captures everything inside the function $(document).ready(function() { ... });
    document_ready_regex = r"\$\(document\).*\{([\s\S]*?)(?=\})"

    # Captures everything inside the function video.init(...)
    vlive_video_init_regex = r"video\.init\(([\s\S]*?)\)"

    # Captures anything between quotation marks
    args_regex = r'"(.*?)"'

    video_id_index = 5
    video_key_index = 6

    # Get everything inside the function in case we need it later
    # But for the moment, we only need a specific string inside it, so we could actually
    # skip this step
    match = re.search(document_ready_regex, html)
    document_function = match.group(1)

    # TODO: handle error

    # Search for the vlive.video.init() function
    match = re.search(vlive_video_init_regex, document_function)
    vlive_video_init_args = match.group(1)

    # TODO: handle error

    # Get all the arguments inside the function above, ready to go
    # This doesn't get the "[]" argument, however
    args_search = re.findall(args_regex, vlive_video_init_args)

    # TODO: handle error

    video_id = args_search[video_id_index]
    video_key = args_search[video_key_index]

    return video_id, video_key


def get_video_json(canonical_url: str, video_id: str, video_key: str) -> dict:
    """Sends a GET request to a url constructed with the video ID which responds with a
    JSON file containing all the data for the video.
    
    Might be a Video.js-related JSON ?"""

    # Headers as used by a Mozilla browser
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": canonical_url,
        "Origin": "https://www.vlive.tv",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    # Parameters used by a Mozilla browser
    # See especially key and video ID
    params = (
        ("key", video_key),
        # NOTE:
        # This value is generated by the javascript, so there's no way to get it from the HTML
        # It is different per video. However, I have tested that the headers are
        # optional, so it's not particularly critical
        ("pid", "rmcPlayer_15950858086901360"),
        ("sid", "2024"),
        ("ver", "2.0"),
        ("devt", "html5_mo"),
        ("doct", "json"),
        ("ptc", "https"),
        ("sptc", "https"),
        ("cpt", "vtt"),
        (
            "ctls",
            '{"visible":{"fullscreen":true,"logo":false,"playbackRate":false,"scrap":false,"playCount":true,"commentCount":true,"title":true,"writer":true,"expand":true,"subtitles":true,"thumbnails":true,"quality":true,"setting":true,"script":false,"logoDimmed":true,"badge":true,"seekingTime":true,"muted":true,"muteButton":false,"viewerNotice":false,"linkCount":false,"createTime":false,"thumbnail":true},"clicked":{"expand":false,"subtitles":false}}',
        ),
        ("pv", "4.18.40"),
        ("dr", "1920x1080"),
        ("cpl", "en_US"),
        ("lc", "en_US"),
        ("videoId", video_id),
        ("cc", "CO"),  # Your country here
    )

    # Concatenating the Naver URL with the video ID gives us the URL we need
    video_json_url = VIDEO_JSON_BASE_URL + video_id

    print(f"Requesting JSON to {video_json_url}")

    response = requests.get(video_json_url, headers=headers, params=params)

    # Check status code for 200 OK ?

    print(f"Received response, status code {response.status_code}\n")

    # It could also return an error JSON, but we are assuming it is the correct one

    return response.json()


def get_subtitle_options(video_json: str):
    """Gets a list of available captions from the JSON.
    
    If it can't find the list, it means the video has no subtitles yet."""
    try:
        captions_dict: list = video_json["captions"]["list"]

        return captions_dict
    except KeyError:
        # We could raise the exception, but we will just exit the program
        print("An error occurred.")
        print("This video does not have captions available.")
        sys.exit(1)


def download_subs(source_url: str, canonical_link: str, video_title: str):
    """Sends a request to the URL in the 'source' element of the item in the captions
    list, which contains the subtitles in .VTT format."""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": canonical_link,
        "Origin": "https://www.vlive.tv",
        "DNT": "1",
        "Connection": "keep-alive",
        "TE": "Trailers",
    }

    print("Sending request to download subs...")

    response = requests.get(source_url, headers=headers)

    # Check status code for 200 OK ?
    print("Received response, status code {}".format(response.status_code))

    if response.status_code == 200:
        return response.text
    else:
        print("An error occurred in the request.")


def get_last_url_item(url: str):
    """Returns everything after the last slash ("/") of a URL."""
    last_slash_index = url.rindex("/")

    return url[last_slash_index + 1 :]


def save_subs_to_file(source_url: str, canonical_link: str, video_title: str, text: str):
    """Saves the VTT text data to a folder named after the video sequence number, which
    is inside a subs/ folder in the upper directory relative to our current one.
    
    If the directories don't exist yet, the program will create them."""

    filename = get_last_url_item(source_url)
    directory = DOWNLOAD_DIR + get_last_url_item(canonical_link)

    filepath = directory + "/" + filename

    Path(directory).mkdir(parents=True, exist_ok=True)

    save_file(text, filepath)

    print(f"File {filename} saved to {directory}")


def list_subs(subs: list):
    """Prints all the captions in subs, and some of their data like language or type."""
    index = 1
    for s in subs:
        print(f"{index}. {s['label']} ({s['language']}), type: {s['type']} {s['fanName']}")
        index += 1

    print()


def main():
    """Main loop: performs the requests, displays the available subs and offers a prompt
    to download them."""

    print("--- VLIVE Subtitle Scraper ---\n")
    print("WARNING! Use of this program could be a violation of the VLIVE Terms of Use.")
    print("This program is only meant for educational purposes.")
    print()

    if len(sys.argv) < 2:
        print("Usage: main.py vlive-url\n")
        url = input("Enter video URL: ")
    else:
        url = sys.argv[1]
    
    # Get the HTML from the vlive url
    html = get_vlive_html(url)

    # Extract the metadata from the HTML
    video_id, video_key = get_video_id_and_key(html)
    upload_date, channel, video_title, canonical_link = get_video_metadata(html)

    print(f"Upload date: {upload_date}")
    print(f"Channel: {channel}")
    print(f"Title: {video_title}")
    print(f"Link: {canonical_link}")
    print()

    # Get the json with the video data using the metadata we just extracted
    video_json = get_video_json(canonical_link, video_id, video_key)

    # Get the subs (a simple dict access)
    subs = get_subtitle_options(video_json)

    print("Available subs:")
    list_subs(subs)
    index: int = 1

    # Show the user simple prompts to download the subs
    while True:
        sub_index = input("Choose subtitles to download (type in the number), or type 'exit' to finish: ")

        if sub_index == "exit":
            break
        else:
            try:
                index = int(sub_index) - 1

                if index >= len(subs) or index < 0:
                    print("The number you entered does not match any subs entry.")
                else:
                    print(f"You selected {subs[index]['label']}.")

                    selected_sub = subs[index]
                    source = selected_sub["source"]

                    # Send a request to the source URL for that particular language
                    # and get the .VTT data back
                    vtt_data = download_subs(source, canonical_link, video_title)

                    save_subs_to_file(source, canonical_link, video_title, vtt_data)

                    print()
                    list_subs(subs)

            except ValueError:
                print("Please enter a valid number.")

    print()
    print("Program finished.")


if __name__ == "__main__":
    main()
