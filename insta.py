import requests, json, re, os
from tqdm import tqdm
from datetime import datetime
import argparse
from dotenv import load_dotenv
from pprint import pprint
load_dotenv()
class instadownloader:
    def __init__(self) -> None:
        pass
    
    def extract(link: str):
        allmedia = r'\"carousel_media\":(.*?\"location\")'
        cookies = {
            'sessionid': os.getenv('sessionid'),
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
        r = requests.get(link, headers=headers, cookies=cookies)
        if 'reel' not in link:
            matches = re.findall(allmedia, r.text, re.MULTILINE)
            if matches and matches != ['null,"location"']:
                for match in matches:
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
                #prolly a single post image
                patternimage = r'\"image_versions2\":{\"candidates\":(.*?\])'
                matches = re.findall(patternimage, r.text, re.MULTILINE)
                matches = matches[0]
                matches = json.loads(matches)
                media = {'jpg': matches[0].get('url')}

        else:
            pattern = r'\"video_versions\":(.*?\])'
            matches = re.findall(pattern, r.text, re.MULTILINE)
            thejson = json.loads(matches[0])
            media: dict = {}
            for i in thejson:
                media['mp4'] = (i['url'])
                break
        usernamepat = r'\"username\":\"[\w\d\-\_\.]{1,}\"'
        username = re.findall(usernamepat, r.text)[0].split(':')[1].replace('"', '')
        return media, username
    
    def download(link: str):
        media, username = instadownloader.extract(link)
        filenames = []
        for key, value in media.items():
            r = requests.get(value, stream=True)
            progress = tqdm(total=int(r.headers.get('content-length')), unit='iB', unit_scale=True)
            filename = f'{username}-{round(datetime.now().timestamp())}.{"jpg" if "jpg" in key else "mp4"}' if not os.path.exists(f'{username}-{round(datetime.now().timestamp())}.{"jpg" if "jpg" in key else "mp4"}') else f'{username}-{round(datetime.now().timestamp())+1}.{"jpg" if "jpg" in key else "mp4"}'
            with open(filename, 'wb') as f1:
                for data in r.iter_content(1024):
                    progress.update(len(data))
                    f1.write(data)
            progress.close()
            filenames.append(filename)
            filesizes = {}
            for i in filenames:
                filesizes[i] = str(round(os.path.getsize(i)/(1024*1024),2)) + ' mb'
        return filenames, filesizes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='download instagram posts and reels')
    parser.add_argument("link", help='link to instagram post or reel')
    args = parser.parse_args()
    result = instadownloader.download(args.link)

            