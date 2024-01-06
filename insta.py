import json, re, os
from tqdm.asyncio import tqdm
from datetime import datetime, timedelta
import argparse
import env
import asyncio, aiohttp, aiofiles, traceback
from yarl import URL
from typing import Literal
from aiohttp_socks import ProxyConnector


class instadownloader:
    def __init__(self) -> None:
        pass
    class no_media_id(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class badsessionid(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    def giveconnector(proxy):
        connector = aiohttp.TCPConnector()
        if proxy:
            if "socks" in proxy:
                connector = ProxyConnector.from_url(proxy)
            else:
                connector = aiohttp.TCPConnector(proxy=proxy)
        return connector
    async def public_media(link: str, csrftoken: str, proxy : str = None) -> (dict | Literal['False']):
        patternshortcode = r"https://(?:www)?\.instagram\.com/(?:reels||p||stories||reel||story)/(.*?)/?$"
        shortcode = re.findall(patternshortcode, link)[0]
        cookies = {
            'csrftoken': csrftoken,
        }
        headers = {
            'authority': 'www.instagram.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.6',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'referer': link,
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-csrftoken': csrftoken,
            'x-ig-app-id': '936619743392459',
        }
        async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
            data = {'variables': '{"shortcode":"%s"}' % shortcode,
                    'doc_id': '10015901848480474'}
            async with session.post("https://www.instagram.com/api/graphql", data=data, headers=headers, cookies=cookies) as r:
                rtext = await r.text(encoding="utf-8")
                try:
                    return json.loads(rtext)
                except:
                    return False
    def public_media_extractor(publicmedia: dict, isnode: bool = False):
        media = {}
        username = None
        if not isnode:
            if publicmedia["data"]["xdt_shortcode_media"].get("edge_sidecar_to_children"):
                post = "multiple"
                for index, slide in enumerate(publicmedia["data"]["xdt_shortcode_media"].get("edge_sidecar_to_children").get("edges")):
                    md, _, pst = instadownloader.public_media_extractor(slide["node"], True)
                    if pst == "reel":
                        media["mp4" + str(index)] = md.get("mp4")
                    elif pst == "single":
                        media["jpg" + str(index)] = md.get("jpg")
            elif publicmedia["data"]["xdt_shortcode_media"].get("video_url"):
                post = "reel"
                media["mp4"] = publicmedia["data"]["xdt_shortcode_media"]["video_url"]
            elif publicmedia["data"]["xdt_shortcode_media"]['is_video'] == False:
                post = "single"
                media["jpg"] = publicmedia["data"]["xdt_shortcode_media"]["display_resources"][-1]['src']
            username = publicmedia["data"]["xdt_shortcode_media"]["owner"]["username"]
        else:
            if publicmedia.get("video_url"):
                post = "reel"
                media["mp4"] = publicmedia.get("video_url")
            elif publicmedia["is_video"] == False:
                post = "single"
                media["jpg"] = publicmedia["display_resources"][-1]['src']
        return media, username, post
    async def apiresponse(link: str, headers: dict, cookies: dict, params: dict = None, proxy: str = None):
        async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
            async with session.get(link, headers=headers, cookies=cookies, params=params) as r:
                response = await r.text(encoding="utf-8")
                return json.loads(response)
    async def api_media(headers: dict, cookies: dict, mediaid: int, proxy: str = None):
        async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
            async with session.get(f"https://www.instagram.com/api/v1/media/{mediaid}/info", headers = headers, cookies=cookies) as r:
                r = await r.text(encoding="utf-8")
                return json.loads(r)
    async def api_stories(headers: dict, cookies: dict, reel_ids: int, mediaid: int, proxy: str = None):
        async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
            params = {
                'media_id': mediaid,
                'reel_ids': reel_ids,
            }
            async with session.get('https://www.instagram.com/api/v1/feed/reels_media/', cookies=cookies, params=params, headers=headers) as r:
                r = await r.text(encoding="utf-8")
                return json.loads(r)
    def app_and_user_id(text: str, appidpattern, useridpattern):
        appid = re.findall(appidpattern, text)
        useridpattern = re.findall(useridpattern, text)
        return appid[0], useridpattern[0]
    async def extract(link: str, sessionid: str  = None, csrftoken: str = None, public_only: bool = False, proxy: str = None):
        """
        link (str) - link to post/story/reel
        sessionid (str, optional) - what sessionid to use (if needed)
        csrftoken (str, optional) - what csrftoken to use (if needed)
        public_only (bool, False) - whether to only use the public graphql api (no music to single image posts and no private posts)
        
        ## Which post type requires credentials?

        -Stories
        
        -Single image posts with music
        
        -Private posts

        ## Which do not?

        -Single images with no music
        
        -Reels
        
        -Posts

        ## Why does it matter?
        
        Instagram tends to detect this activity and puts a captcha if used too often :(
        
        So for any public downloader youre doing, use public_only
        """
        if not sessionid:
            sessionid = env.sessionid
        if not csrftoken:
            csrftoken = env.csrftoken
        print(link)
        allmedia = r'(\{\"require\":\[\[\"ScheduledServerJS\",\"handle\",null,\[\{\"__bbox\":\{\"require\":\[\[\"RelayPrefetchedStreamCache\",\"next\",\[\],\[\"adp_PolarisPostRootQueryRelayPreloader(?:.*?))</script>'
        cookies = {
            'sessionid': sessionid,
            'csrftoken': csrftoken
        }

        headers = {
            'authority': 'www.instagram.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.7',
            'sec-fetch-mode': 'navigate',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        media = {}


        patterncsrf = r"{\"csrf_token\":\"(.*?)\"}"
        if not os.path.exists("tempcsrf.json"):
            async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
                async with session.get(link, headers=headers, cookies=None) as r:
                    rtext = ""
                    while True:
                        chunk = await r.content.read(1024)
                        if not chunk:
                            break
                        rtext += chunk.decode('utf-8')
            csrftoken2 = re.findall(patterncsrf, rtext)[0]
            async with aiofiles.open("tempcsrf.json", "w") as f1:
                await f1.write(json.dumps({"csrf": csrftoken2, "expire": (datetime.now() + timedelta(days=7)).isoformat()}))
        else:
            async with aiofiles.open("tempcsrf.json", "r") as f1:
                the = json.loads(await f1.read())
                if datetime.now() > datetime.fromisoformat(the["expire"]):
                    async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
                        async with session.get(link, headers=headers, cookies=None) as r:
                            rtext = ""
                            while True:
                                chunk = await r.content.read(1024)
                                if not chunk:
                                    break
                                rtext += chunk.decode('utf-8')
                    csrftoken2 = re.findall(patterncsrf, rtext)[0]
                    async with aiofiles.open("tempcsrf.json", "w") as f1:
                        await f1.write(json.dumps({"csrf": csrftoken2, "expire": (datetime.now() + timedelta(days=7)).isoformat()}))
                else:
                    csrftoken2 = the.get('csrf')

        if 'stories' not in link:
            if public_only:
                
                publicmedia = await instadownloader.public_media(link, csrftoken2, proxy)
                if publicmedia:
                    media, username, post = instadownloader.public_media_extractor(publicmedia)
                    return media, username, post
                else:
                    return {"status": 1, "message": "couldnt fetch using graphql public api"}
            else:

                try:
                    
                    patternmediaid = r"content=\"instagram://media\?id=(.*?)\""
                    async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
                                    async with session.get(link, headers=headers, cookies=None) as r:
                                        rtext = ""
                                        while True:
                                            chunk = await r.content.read(1024)
                                            if not chunk:
                                                break
                                            rtext += chunk.decode('utf-8')
                    mediaid = re.findall(patternmediaid, rtext)
                    if not mediaid:
                        print("private post, have to scrape")
                        async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
                            try:
                                async with session.get(link, headers=headers, cookies=cookies) as r:
                                    rtext = ""
                                    while True:
                                        chunk = await r.content.read(1024)
                                        if not chunk:
                                            break
                                        rtext += chunk.decode('utf-8')
                            except aiohttp.TooManyRedirects:
                                print('change your session ID! too many redirects')
                                raise instadownloader.badsessionid('change your session ID! too many redirects')
                        patternmediaid = r"content=\"instagram://media\?id=(.*?)\""
                        mediaid = re.findall(patternmediaid, rtext)
                    if not mediaid:
                        with open("response.txt", "w", encoding="utf-8") as f1:
                            f1.write(rtext)
                        raise instadownloader.no_media_id(f"couldnt find media id, response in response.txt")
                    newheaders = headers.copy()
                    newheaders['x-csrftoken'] = csrftoken
                    newheaders['x-ig-app-id'] = "936619743392459"
                    apiresp = await instadownloader.api_media(headers=newheaders, cookies=cookies, mediaid = mediaid[0], proxy=proxy)
                    media = {}
                    musicinfo= None
                    username = None
                    if apiresp["items"][0].get('carousel_media'):
                        post = "multiple"
                        for index, value in enumerate(apiresp["items"][0]["carousel_media"]):
                            if value.get("video_versions"):
                                for i in value["video_versions"]:
                                    media["mp4" + str(index)] = i["url"]
                                    break
                            elif value.get("image_versions2"):
                                media["jpg" + str(index)] = value["image_versions2"]["candidates"][0]['url']
                    else:
                        value = apiresp["items"][0]
                        if value.get("video_versions"):
                            for i in value["video_versions"]:
                                media["mp4"] = i["url"]
                                post = 'reel'
                                break
                        elif value.get("image_versions2"):
                            media["jpg"] = value["image_versions2"]["candidates"][0]['url']
                            if value.get('music_metadata'):
                                if value["music_metadata"].get('music_info'):
                                    downloadurl = value['music_metadata']["music_info"]["music_asset_info"]["fast_start_progressive_download_url"]
                                    durationms = value['music_metadata']["music_info"]["music_consumption_info"]["overlap_duration_in_ms"]
                                    startms = value['music_metadata']["music_info"]["music_consumption_info"]["audio_asset_start_time_in_ms"]
                                    endms = startms + durationms
                                    start = f"{int((startms/1000)//3600):02}:{int((startms/1000)//60 % 60):02}:{int((startms/1000) % 60):02}"
                                    end = f"{int((endms/1000)//3600):02}:{int((endms/1000)//60 % 60):02}:{int((endms/1000) % 60):02}"
                                    print(start, end)
                                    musicinfo = {"url": downloadurl, "start": start, "end": end, "duration": durationms/1000}
                                    media["music"] = musicinfo
                            post = 'image'
                    if not username:
                        username = apiresp["items"][0]["user"].get("username")
                    return media, username, post
                except Exception as e:
                    print(f"couldnt fetch using api, will try manual:\n{e}")
        else:
            if public_only:
                return {"status": 1, "message": "cant use public API with stories"}
            patternusername = r"https://(?:www\.)?instagram\.com/stories/(.*?)/(?:.*?)/?$"
            patternuserid = r"\"props\":{\"id\":\"(.*?)\""
            patternmediaid = r"https://(?:www\.)?instagram\.com/stories/(?:.*?)/(.*?)/?$"
            userid = None
            username = re.findall(patternusername, link)[0]
            mediaid = re.findall(patternmediaid, link)
            headers2 = headers.copy()
            headers2["cookie"] = f'csrftoken={csrftoken2[0]}'
            async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
                async with session.get(f"https://www.instagram.com/{username}/", headers=headers2) as r:
                    respo = await r.text("utf-8")
                    userid = re.findall(patternuserid, respo)
            newheaders = headers.copy()
            newheaders['x-csrftoken'] = csrftoken
            newheaders['x-ig-app-id'] = "936619743392459"
            realresp = await instadownloader.api_stories(headers=newheaders, cookies=cookies, reel_ids=userid[0], mediaid=mediaid[0], proxy=proxy)
            media = {}
            try:
                for index, item in enumerate(realresp["reels"][userid[0]]["items"]):
                    if item["pk"] == mediaid[0]:
                        if item.get("video_versions"):
                            media['mp4' + str(index)] = item["video_versions"][0]["url"]
                        else:
                            media['jpg' + str(index)] = item["image_versions2"]["candidates"][0]['url']
                post = 'story'
                return media, username, post
            except Exception as e:
                print(f"couldnt fetch using api, will try manual:\n{e}")

        async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
            try:
                async with session.get(link, headers=headers, cookies=cookies) as r:
                    rtext = ""
                    while True:
                        chunk = await r.content.read(1024)
                        if not chunk:
                            break
                        rtext += chunk.decode('utf-8')
            except aiohttp.TooManyRedirects:
                print('change your session ID! too many redirects')
                raise instadownloader.badsessionid('change your session ID! too many redirects')
        if 'reel' not in link and 'stories' not in link:
            print('multiple')
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
                if not match:
                    patternapp = r"\"X-IG-App-ID\":\"(.*?)\""
                    patternid = r"\"user_id\":\"(.*?)\""
                    patternmedia = r"\"media_id\":\"(.*?)\""
                    mediaid = re.findall(patternmedia, rtext)
                    appid, userid = instadownloader.app_and_user_id(rtext, patternapp, patternid)
                    newheaders = headers.copy()
                    newheaders['x-csrftoken'] = csrftoken
                    newheaders['x-ig-app-id'] = appid
                    apiresp = await instadownloader.api_media(headers=newheaders, cookies=cookies, mediaid = mediaid[0], proxy=proxy)
                    # with open('response.json', 'w') as f1:
                    #     json.dump(apiresp, f1, indent=4)
                    print('actually single image')
                    post = 'image'
                    match = find_key(apiresp, 'image_versions2')
                    musicmetadata = find_key(apiresp, 'music_metadata')
                    musicinfo = None
                    if musicmetadata and musicmetadata.get("music_info"):
                        downloadurl = musicmetadata["music_info"]["music_asset_info"]["fast_start_progressive_download_url"]
                        durationms = musicmetadata["music_info"]["music_consumption_info"]["overlap_duration_in_ms"]
                        startms = musicmetadata["music_info"]["music_consumption_info"]["audio_asset_start_time_in_ms"]
                        endms = startms + durationms
                        start = f"{int((startms/1000)//3600):02}:{int((startms/1000)//60 % 60):02}:{int((startms/1000) % 60):02}"
                        end = f"{int((endms/1000)//3600):02}:{int((endms/1000)//60 % 60):02}:{int((endms/1000) % 60):02}"
                        print(start, end)
                        musicinfo = {"url": downloadurl, "start": start, "end": end, "duration": durationms/1000}
                media: dict= {}
                if post != 'image':
                    try:
                        for index, i in enumerate(match):
                            if i['media_type'] == 1:
                                media['jpg'+str(index)] = i['image_versions2']['candidates'][0]['url']
                            else:
                                media['mp4'+str(index)] = i['video_versions'][0]['url']
                    except Exception as e:
                        traceback.print_exc()
                        if 'char' in str(e):
                            char = int(str(e).split('(char ')[1].replace(')', ''))
                            print(char)
                            print(match[char-25:char+25])
                else:
                    media = {'jpg': match['candidates'][0].get('url')}
                    media["music"] = musicinfo

        elif 'reel' in link:
            post = 'reel'
            pattern = r'\"video_versions\":(.*?\])'
            matches = re.findall(pattern, rtext, re.MULTILINE)
            thejson = json.loads(matches[0])
            media: dict = {}
            for i in thejson:
                media['mp4'] = (i['url'])
                break
        elif 'stories' in link:
            post = 'story'
            patternapp = r"\"X-IG-App-ID\":\"(.*?)\""
            patternreelid = r"\"props\":{\"user\":{\"id\":\"(.*?)\""
            patternmediaid = r"https://(?:www\.)?instagram\.com/stories/(?:.*?)/(.*?)/?$"
            appid = re.findall(patternapp, rtext)
            reelsid = re.findall(patternreelid, rtext)
            if not reelsid:
                reelsid = re.findall(r"\"user_id\":\"(.*?)\"", rtext)
            mediaid = re.findall(patternmediaid, link)
            newheaders = headers.copy()
            newheaders['x-csrftoken'] = csrftoken
            newheaders['x-ig-app-id'] = appid[0]
            realresp = await instadownloader.api_stories(headers=newheaders, cookies=cookies, reel_ids=reelsid[0], mediaid=mediaid[0], proxy=proxy)
            media = {}
            for index, item in enumerate(realresp["reels"][reelsid[0]]["items"]):
                if item["pk"] == mediaid[0]:
                    if item.get("video_versions"):
                        media['mp4' + str(index)] = item["video_versions"][0]["url"]
                    else:
                        media['jpg' + str(index)] = item["image_versions2"]["candidates"][0]['url']
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
    async def downloadworker(link: str, filename: str, proxy: str = None):
        async with aiofiles.open(filename, 'wb') as f1:
            async with aiohttp.ClientSession(connector=instadownloader.giveconnector(proxy)) as session:
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
    async def download(link: str, sessionid: str = None, csrftoken: str = None, handle_merge: bool = True, public_only: bool = False, proxy: str = None):
        """link: str - instagram link to a post, reel, story"""
        a = await instadownloader.extract(link.split("?")[0], sessionid, csrftoken, public_only, proxy)
        if not a:
            print("error!")
            return False
        if isinstance(a, dict) and a.get('status'):
            if a['status'] != 0:
                print(a)
                return a
        media, username, post = a[0], a[1], a[2]
        if not media:
            print('some error occured')
            return False
        filenames = []
        musicinfo = None
        if post == 'image':
            files2 = {}
        for index, (key, value) in enumerate(media.items()):
            if key != "music":
                filename = f'{username}-{round(datetime.now().timestamp())}-{index}.{"jpg" if "jpg" in key else "mp4"}'
                filenames.append(filename)
                if post == 'image':
                    files2["image"] = filename
                filesizes = {}
                await instadownloader.downloadworker(link = value, filename=filename)
            else:
                 if not value:
                     continue
                 filename = f'{username}-{round(datetime.now().timestamp())}.m4a'
                 await instadownloader.downloadworker(link=value.get('url'), filename=filename)
                 files2["audio"] = filename
                 musicinfo = value
        if post == 'image'and musicinfo and handle_merge:
            import subprocess
            filename = f"trimmed-{round(datetime.now().timestamp())}.m4a"
            command = f"ffmpeg -i {files2['audio']} -ss {musicinfo['start']} -v error -to {musicinfo['end']} -c copy {filename}".split()
            subprocess.run(command)
            outputfile = files2['image'].replace('jpg', 'mp4')
            command = f"ffmpeg -r 2 -loop 1 -i {files2['image']} -i {filename} -vf crop=trunc(iw/2)*2:trunc(ih/2)*2 -v error -c:a copy -rc-lookahead 6 -t {musicinfo['duration']} {outputfile}".split()
            subprocess.run(command)
            for key, value in files2.items():
                os.remove(value)
            os.remove(filename)
            filenames = [outputfile]

            return {"files": filenames, "sizes": round(os.path.getsize(outputfile)/(1024*1024), 2), "postType": post, "musicInfo": musicinfo}
        elif post == 'image' and musicinfo and not handle_merge:
            for i in files2.values():
                filesizes[i] = str(round(os.path.getsize(i)/(1024*1024),2)) + ' mb'
            return {"files": files2, "sizes": filesizes, "postType": post, "musicInfo": musicinfo}

        for i in filenames:
            filesizes[i] = str(round(os.path.getsize(i)/(1024*1024),2)) + ' mb'
        return {"files": filenames, "sizes": filesizes, "postType": post, "musicInfo": musicinfo}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='download instagram posts and reels')
    parser.add_argument("link", type=str, help='link to instagram post or reel')
    parser.add_argument("--handle-merge", "-m", action="store_true", help="whether to not merge and let you do it")
    parser.add_argument("--public-only", "-api", action="store_true", help="whether to use public api for posts")
    parser.add_argument("--proxy", "-p", type=str, help="proxy to use")
    args = parser.parse_args()
    if '?' in args.link:
        args.link = args.link.split('?')[0]
    result = asyncio.run(instadownloader.download(args.link, handle_merge=not args.handle_merge, public_only=args.public_only, proxy=args.proxy))
    if not result:
        print('error occured')
    else:
        print('\n')
        print(result)

            