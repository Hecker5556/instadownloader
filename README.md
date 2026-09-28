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
pip install "git+https://github.com/Hecker5556/instadownloader.git"
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
9. copy the cookies
10. in your script uncomment the 'cookie' header

```python
async def main():
    cookies = {
        'your': 'cookie',
    }
    async with InstagramDownloader(
        cookies = cookies
    ) as id:
        result = await id.download("your url")
```
# Usage:
```
usage: insta.py [-h] [--proxy PROXY] [--no-download] [--verbose] [--no-h264] [--cookies-json COOKIES_JSON] [--cookies-netscape COOKIES_NETSCAPE]
                [--cookies-headerstring COOKIES_HEADERSTRING]
                link

positional arguments:
  link                  Link to post

options:
  -h, --help            show this help message and exit
  --proxy PROXY, -p PROXY
                        proxy to use in all the requests
  --no-download, -n     prints just the post and doesn't download the post's media
  --verbose, -v
  --no-h264, -d         Ignore dash formats and download default h264 format
  --cookies-json COOKIES_JSON
                        Provide cookies in JSON format
  --cookies-netscape COOKIES_NETSCAPE
                        Provide cookies in netscape format
  --cookies-headerstring COOKIES_HEADERSTRING
                        Provide cookies in header-string format
```
# Usage in python
```python
import asyncio
from insta import InstagramDownloader
async def main():
    async with InstagramDownloader() as id:
        result = await id.download("url")
```






