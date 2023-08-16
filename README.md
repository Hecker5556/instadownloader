# Simple Instagram post and reels downloader

## First time setup
### in command prompt:
    git clone https://github.com/Hecker5556/instadownloader.git
#
    cd instadownloader
### If you haven't already, download [python.](https://python.org)
### Optional: build to exe (windows) and add to path, linux users, this wont build to exe but it will add to path, chmod it and write into a file what command to use to execute it
    python setup.py build
### if you dont want to do that, just do:
    pip install -r requirements.txt

## Get sessionid
### Before you start running the code, you will need to add a sessionid to a .env file, which you can get by either checking network traffic on instagram or using a cookie viewing extension
## Video tutorial why not 
https://github.com/Hecker5556/instadownloader/assets/96238375/ecb26c67-24f7-4331-80ab-69ef560a45cc

# Usage:
## double quote the link because sometimes the link may have &
## unbuilt:
    python insta.py "link"
## built:
    insta "link"
## linux:
    path/to/insta.py "link"

# Usage in python
```python
import sys, asyncio
#do this to add to sys path
if 'instadownloader' not in sys.path:
    sys.path.append('instadownloader')
from instadownloader.insta import instadownloader
filenames, fileinfo = asyncio.run(instadownloader.download(link))

#in async function
async def main():
    filenames, fileinfo = await instadownloader.download(link)
```






