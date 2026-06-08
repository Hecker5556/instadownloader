# Simple Instagram post and reels downloader python 3.10.9
## Features
* Fetches posts asynchronously
* Returns post information and links to download the media
* Downloads the media (and combines video + audio stream with ffmpeg if needed)
* Fetches url to download the music used on post (if available)
* Ability to put your own headers (cookies) to download private posts
## Setup
terminal:
```bash
git clone https://github.com/Hecker5556/instadownloader
```
```bash
cd instdownloader 
```
```bash
pip install -r requirements.txt
```
## Fetching private posts
Most important cookie for getting private posts is the "sessionid" cookie, which if you provide in the headers, will successfully fetch a private post.

There is an important caveat, since the program doesn't send telemetry, instagram will eventually flag accounts that have activity without telemetry. To avoid this use the account frequently so the requests blend in.
## How to get sessionid/headers
1. open instagram.com on a browser of choice (make sure youre logged in)
2. open dev tab (ctrl shift i, or right click and inpsect element)
3. go to network tab
4. refresh page
5. click "Doc" Filter
6. right click the request and copy as curl (bash)

![alt text](image.png)

7. open [curl converter](https://curlconverter.com)
8. paste the request
9. copy the headers
10. in your script uncomment the 'cookie' header

```python
async def main():
    async with InstagramDownloader(
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Brave";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Brave";v="149.0.0.0", "Chromium";v="149.0.0.0", "Not)A;Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
            'cookie': 'yourcookies',
        }
    ) as id:
        result = await id.download("your url")
```
# Usage:
```
usage: insta.py [-h] [--proxy PROXY] [--no-download] [--verbose] link

positional arguments:
  link                  Link to post

options:
  -h, --help            show this help message and exit
  --proxy PROXY, -p PROXY
                        proxy to use in all the requests
  --no-download, -n     prints just the post and doesn't download the post's media
  --verbose, -v
```
# Usage in python
```python
import asyncio
from insta import InstagramDownloader
async def main():
    async with InstagramDownloader() as id:
        result = await id.download("url")
```






