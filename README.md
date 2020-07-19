# VLIVE Subtitles Scraper

A small Python program that downloads subtitles for videos hosted on the V Live platform, made mostly for practice and to learn the basics of web scraping.

## Legal Notice

This project is purely for educational purposes. Please note that use of this program could be against [article 9 of the V Fansubs Terms of Use, ver 1.0](https://subtitle.vlive.tv/terms?lang=en_US) ("Member's Rights and Obligations"). As expressed by the license accompanying this repository, I shall not be held liable for the temporary and/or permanent restriction of your use of the V Fansubs Service arising from use of this program (as stated in article 12 of the terms of use linked above).

Please use web scrapers responsibly.

## Usage

This program requires python 3 and uses the following external libraries:

- [requests](https://pypi.org/project/requests/)
- [BeautifulSoup](https://pypi.org/project/beautifulsoup4/)

Install them using pip:
```sh
$ pip3 install requests beautifulsoup4
```

Then simply run `main.py`. You can pass the video URL as a parameter if you wish (if not, the program will ask you anyway):
```
$ python3 main.py https://www.vlive.tv/video/000001
```

After this the program will send some requests (see below for an explanation), display some of the video metadata, and list the available subtitles. For example:
```
$ python3 main.py https://www.vlive.tv/video/000001

...

Upload date: Jan 01, 2020
Channel: [CHANNEL]
Title: [VIDEO TITLE]
Link: https://www.vlive.tv/video/000001

...

1. English (en), type: fan
2. 한국어 (ko), type: cp 

Choose subtitles to download (type in the number), or type 'exit' to finish: 
```

At this point, simply type in the number corresponding to the subtitles you wish to download, and press enter. If there are no errors, the file will be downloaded to a directory like `subs/000001/` with `.vtt` format (do note that the subtitles are protected by copyright, see the terms of use linked above).

Once you are done, type `exit` to finish the program.

## Explanation

From what I have gathered using the Firefox inspector (Tools -> Web Developer -> Inspector), once loaded, the V Live website uses javascript to download a JSON file containing all the video metadata from a specific static address related to the video we are watching. This address is built using a per-video `video id` with which the javascript is initialized.

The video JSON includes a `captions` element that lists (under `list`) all available subtitles for the given video. Inside each of these items is a `source` element (among other relevant data) that has the URL to the subtitles file in `.vtt` format. Our goal is to scrape the website and perform the necessary requests to get this JSON file and finally retrieve the captions' `source` addresses.

The JSON also contains additional video metadata and video stream URLs.

### Scraping the HTML

The first step, given a valid V Live URL (`https://www.vlive.tv/video/...`), is to send a `GET` request to this address and receive the HTML in turn.

Although additional headers are not necessary in the requests that we will be sending, we will be using headers as sent by Firefox to make our scraper seem more 'human' (see the relevant functions in the source code for the header data). Of note is that in this first request we are using `https://www.google.com/` as `Referer`.

In the HTML, we will look for data both in the HTML tags and in the included javascript.

#### Javascript data

Inside the `<script>` tag, we will search for and look at the contents of the function `$(document).ready(function() { ... });` which initializes a video object with parameters like the video ID and key, which we will need in a moment. The function looks like this (some of the data has been replaced with dummy values; comments mine):

```html
<!-- HTML here -->

<script type="text/javascript">

// ... Javascript here

$(document).ready(function() {
		vlive.tv.common.init(...);
		vlive.video.init("VOD", "000001", "VOD_ON_AIR", "NONE", "EDBF",
			"0123456789ABCDEF0123456789ABCDEF0123", // <-- video ID
			"V0123456789abcdef0123456789abcdef01230123456789abcdef0123456789abcdef01230123456789ab", // <-- key
			[],"", "true", "false", ""); // That's the data we are interested in! It's always in the same order
		vlive.tv.live.thumb.handler.init(...);
		vlive.tv.share.init(...);
		vlive.video.showShoppingBanner(...);
		
		/*  */
		
	});

// ... More Javascript

</script>

<!-- more HTML -->
```

We can get these values using regular expressions.

#### HTML data

We are interested in two tags mainly:

- The `meta` tag with `name="description"` which contains the video upload date, channel, and title inside a `content` attribute. They are separated by a dash and a space (`" - "`), which we can easily split into invidual strings:
```html
<meta name="description" content="DATE - [CHANNEL] - VIDEO TITLE - You can watch videos on V LIVE.">
```
- The `<link>` tag with attribute `rel="canonical"` from which we can get the canonical URL that we will use as `referer` in the next two requests.

### Requesting the JSON with the video data

Using the values we extracted above we can send a `GET` request to the address `https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/{video_id}key?={video_key}`, where the resource and URL parameter are the `video id` and `key` we found earlier, respectively (the browser also sends additional headers, which we will be sending as well). The response is the video JSON with the information about the subtitles under its `captions` element, which itself holds a `list` element.

**Note:** This automated request does not respect the domain's `robots.txt` file (at https://apis.naver.com/robots.txt).

The JSON looks like this (yes, it comes with that ugly formatting):
```json
{
	...

	,"captions":{
		"captionLang": "en_US",
		"list":[
			{
				"language":"en"
				,"country":"US"
				,"locale":"en_US"
				,"label":"English"
				,"source":"https://resources-rmcnmv.pstatic.net/{English subs in VTT format}"
				,"type":"cp"
				,"fanName":""
			}
			,
			{
				"language":"ko"
				,"country":"KR"
				,"locale":"ko_KR"
				,"label":"한국어"
				,"source":"https://resources-rmcnmv.pstatic.net/{Korean subs in VTT format}"
				,"type":"cp"
				,"fanName":""
				
			}

		...

		]
	}

...

}
```

From then on we simply get the `source` element, send another `GET` request to that address (with relevant headers), and download the subtitles.

**Note:** This automated request does not respect the domain's `robots.txt` file (at pstatic.net/robots.txt).

## Useful Links

- [V Fansubs Terms of Use (Ver. 1.0)](https://subtitle.vlive.tv/terms?lang=en_US=)
- [Julia Piaskowski - A beginner's guide to web scraping with Python](https://opensource.com/article/20/5/web-scraping-python)
- [Scrape Hero - How to scrape websites without getting blocked](https://www.scrapehero.com/how-to-prevent-getting-blacklisted-while-scraping/)
- [scraperapi - 5 Tips For Web Scraping Without Getting Blocked or Blacklisted](https://www.scraperapi.com/blog/5-tips-for-web-scraping/)
- [Ben Awad - How to Scrape a Website using Inspect Element and Python](https://www.youtube.com/watch?v=7Uxm5YvXmpE)
- [MDN web docs - Adding captions and subtitles to HTML5 video](https://developer.mozilla.org/en-US/docs/Web/Guide/Audio_and_video_delivery/Adding_captions_and_subtitles_to_HTML5_video)

### Tools

- [Regular Expressions 101](https://regex101.com/)
- [Rubular, a Ruby regular expression editor](https://rubular.com/)
- [Convert curl syntax to Python](https://curl.trillworks.com/)