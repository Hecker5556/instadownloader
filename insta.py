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
        allmedia = r'(\{\"require\":\[\[\"ScheduledServerJS\",\"handle\",null,\[\{\"__bbox\":\{\"require\":\[\[\"RelayPrefetchedStreamCache\",\"next\",\[\],\[\"adp_PolarisPostRootQueryRelayPreloader(?:.*?))</script>'
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
            post = 'multiple'
            matches = re.findall(allmedia, rtext, re.MULTILINE)
            if matches:
                def find_key(json_obj, target_key):
                    if isinstance(json_obj, dict):
                        for key, value in json_obj.items():
                            if key == target_key:
                                return value
                            else:
                                result = find_key(value, target_key)
                                if result is not None:
                                    return result
                    elif isinstance(json_obj, list):
                        for item in json_obj:
                            result = find_key(item, target_key)
                            if result is not None:
                                return result
                    return None
                match = find_key(json.loads(matches[0]), 'carousel_media')

                media: dict= {}
                try:
                    for index, i in enumerate(match):
                        if i['media_type'] == 1:
                            media['jpg'+str(index)] = i['image_versions2']['candidates'][0]['url']
                        else:
                            media['mp4'+str(index)] = i['video_versions'][0]['url']
                except Exception as e:
                    print(e)
                    if 'char' in str(e):
                        char = int(str(e).split('(char ')[1].replace(')', ''))
                        print(char)
                        print(match[char-25:char+25])
            else:
                logging.debug('single image post')
                post = 'image'
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
            post = 'reel'
            logging.debug('extracting video')
            pattern = r'\"video_versions\":(.*?\])'
            matches = re.findall(pattern, rtext, re.MULTILINE)
            thejson = json.loads(matches[0])
            media: dict = {}
            for i in thejson:
                media['mp4'] = (i['url'])
                break
        usernamepat = r'\"username\":\"(.*?)\"'
        usernamematches = re.findall(usernamepat, rtext)
        usercounts = {}
        for match in usernamematches:
            if usercounts.get(match):
                usercounts[match] += 1
            else:
                usercounts[match] = 1
        usercounts = sorted(usercounts.items(), key=lambda x: x[1], reverse=True)
        username = usercounts[0][0]
        return media, username, post
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
        media, username, post = await instadownloader.extract(link)
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
        return filenames, filesizes, post

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='download instagram posts and reels')
    parser.add_argument("link", type=str, help='link to instagram post or reel')
    args = parser.parse_args()#https://www.instagram.com/p/Cv7j5DzsDYy/?utm_source=ig_web_copy_link&igshid=MzRlODBiNWFlZA==
    if '?' in args.link:
        args.link = args.link.split('?')[0]
    result = asyncio.run(instadownloader.download(args.link))
    print('\n')
    print(f"{result[0]}\n{result[1].items()}")

            