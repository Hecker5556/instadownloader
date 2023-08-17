import requests, json, re, os
from tqdm.asyncio import tqdm
from datetime import datetime
import argparse
import env
import logging
import asyncio, aiohttp, aiofiles
from yarl import URL
sessionid = env.sessionid


class instadownloader:
    def __init__(self) -> None:
        pass
    async def extract(link: str):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.debug(link)
        allmedia = r'\"carousel_media\":(.*?\"location\")'
        cookies = {
            'sessionid': sessionid,
        }

        headers = {
            'authority': 'www.instagram.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(link, headers=headers, cookies=cookies) as r:
                rtext = await r.text()
        if 'reel' not in link:
            matches = re.findall(allmedia, rtext, re.MULTILINE)
            if matches and matches != ['null,"location"']:
                for match in matches:
                    logging.debug('extracting posts')
                    mpddash = r'(\"video_dash_manifest\":(?!null)(.*?\"\,))'
                    match = match.replace('\/', '/').encode('utf-8').decode('unicode_escape').replace('\n', '')[:-11]
                    #for some reason the dash manifest would bug out the json decoder
                    manifests = re.findall(mpddash, match)
                    for i in manifests:
                        match = match.replace(i[1], 'null,')
                    accessibilitycaption = r'(\"accessibility_caption\":(?!null)(.*?\"\,))'
                    #same with this, some text would bug it out
                    captions = re.findall(accessibilitycaption, match)
                    for i in captions:
                        match = match.replace(i[1], 'null,')
                    media: dict= {}
                    try:
                        for index, i in enumerate(json.loads(match)):
                            if i['media_type'] == 1:
                                media['jpg'+str(index)] = i['image_versions2']['candidates'][0]['url']
                            else:
                                media['mp4'+str(index)] = i['video_versions'][0]['url']
                    except Exception as e:
                        print(e)
                        if 'char' in str(e):
                            char = int(str(e).split('(char ')[1].replace(')', ''))
                            print(char)
                            print(match[char])
                            print(match[char-50:char+50])
            else:
                logging.debug('single image post')
                #prolly a single post image
                for i in range(3):
                    patternimage = r'\"image_versions2\":{\"candidates\":(.*?\])'
                    matches = re.findall(patternimage, rtext)
                    if matches:
                        break
                    else:
                        logging.debug('trying again')
                        r = requests.get(link, cookies=cookies, headers=headers)
                        rtext = r.text
                        continue
                if matches:
                    pass
                else:
                    logging.debug('couldnt find')
                    with open('instaresponse.txt', 'w', encoding='utf=8') as f1:
                        f1.write(rtext)
                matches = matches[0]
                matches = json.loads(matches)
                media = {'jpg': matches[0].get('url')}

        else:
            logging.debug('extracting video')
            pattern = r'\"video_versions\":(.*?\])'
            matches = re.findall(pattern, rtext, re.MULTILINE)
            thejson = json.loads(matches[0])
            media: dict = {}
            for i in thejson:
                media['mp4'] = (i['url'])
                break
        usernamepat = r'\"username\":\"[\w\d\-\_\.]{1,}\"'
        username = re.findall(usernamepat, rtext)[0].split(':')[1].replace('"', '')
        return media, username
    async def downloadworker(link: str, filename: str):
        async with aiofiles.open(filename, 'wb') as f1:
            async with aiohttp.ClientSession() as session:
                async with session.get(URL(link, encoded=True)) as response:
                    totalsize = int(response.headers.get('content-length'))
                    progress = tqdm(total=totalsize, unit='iB', unit_scale=True)
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await f1.write(chunk)
                        progress.update(len(chunk))
                    progress.close()
    async def download(link: str):
        """link: str - instagram link to a post or a reel (cant download stories yet)"""
        media, username = await instadownloader.extract(link)
        filenames = []
        tasks = []
        for index, (key, value) in enumerate(media.items()):
            filename = f'{username}-{round(datetime.now().timestamp())}-{index}.{"jpg" if "jpg" in key else "mp4"}'
            filenames.append(filename)
            filesizes = {}
            tasks.append(instadownloader.downloadworker(link = value, filename=filename))
        await asyncio.gather(*tasks)
        for i in filenames:
            filesizes[i] = str(round(os.path.getsize(i)/(1024*1024),2)) + ' mb'
        return filenames, filesizes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='download instagram posts and reels')
    parser.add_argument("link", type=str, help='link to instagram post or reel')
    args = parser.parse_args()#https://www.instagram.com/p/Cv7j5DzsDYy/?utm_source=ig_web_copy_link&igshid=MzRlODBiNWFlZA==
    if '?' in args.link:
        args.link = args.link.split('?')[0]
    result = asyncio.run(instadownloader.download(args.link))
    print('\n')
    print(f"{result[0]}\n{result[1].items()}")

            