import json, re, os, logging, traceback, cv2
from tqdm.asyncio import tqdm
from datetime import datetime, timedelta
import argparse
import asyncio, aiohttp, aiofiles, traceback
from aiohttp_socks import ProxyConnector
from colorama import Fore
from yarl import URL
from html import unescape
class instadownloader:
    class no_media_id(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class badsessionid(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class no_media(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class get_info_fail(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class no_credentials(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    def __init__(self):
        self.sessionid = None
    def giveconnector(self, proxy):
        self.proxy = proxy if proxy and proxy.startswith("https") else None
        return ProxyConnector.from_url(proxy) if proxy and proxy.startswith("socks") else aiohttp.TCPConnector()
    def get_credentials(self):
        try:
            import env
            self.sessionid = env.sessionid
            self.cookies = {"sessionid": self.sessionid}
            self.logger.debug(f"{Fore.GREEN}found credentials in env.py{Fore.RESET}")
        except ModuleNotFoundError:
            if not hasattr(self, "sessionid"):
                raise self.no_credentials(f"{Fore.RED}couldnt find credentials (sessionid), make sure to make an env.py file and write\n{Fore.RESET}sessionid = \"YOURSESSIONID\"")
    def _format_request_info(self, request: aiohttp.RequestInfo, other_info = None):
        method = request.method
        headers = {}
        for key, value in request.headers.items():
            headers[key] = value
        headers = json.dumps(headers, indent=4)
        url = request.url
        return f"sending {Fore.BLUE}{method}{Fore.RESET} request to {Fore.CYAN}{url}{Fore.RESET} using headers:\n{headers}\nother info:\n{other_info}"
    async def _graphql_api(self, link: str):
        patternshortcode = r"https://(?:www)?\.instagram\.com/(?:reels||p||stories||reel||story)/(.*?)/?$"
        shortcode = re.findall(patternshortcode, link.split("?")[0])[0]
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
            'x-csrftoken': self.csrf,
            'x-ig-app-id': '936619743392459',
        }

        data = {'variables': '{"shortcode":"%s"}' % shortcode,
                'doc_id': '24852649951017035'}
        async with self.session.post("https://www.instagram.com/graphql/query", data=data, headers=headers, cookies=self.cookies, proxy=self.proxy) as r:
            self.logger.debug(self._format_request_info(r.request_info, f"data:\n{data}"))
            response = await r.text("utf-8")
            try:
                thejson = json.loads(response)
                with open("graphql.json", "w") as f1:
                    json.dump(thejson, f1, indent=4)
                if not thejson['data'].get("xdt_shortcode_media"):
                    self.logger.debug(f"couldnt find data in graphql, response written in graphql.json")
                    return None
                return thejson
            except Exception as e:
                self.logger.debug(f"Error in getting graphql response:\n{traceback.format_exc()}")
                return None
    def _find_key(self, obj, searching_for: str, not_null: bool = True):
        path = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == searching_for:
                    if not_null and value:
                        path.append(key)
                        return path
                    elif not not_null:
                        path.append(key)
                        return path

                result = self._find_key(value, searching_for, not_null)
                if result:
                    path.append(key)
                    path += result
                    return path
        elif isinstance(obj, list):
            for index, i in enumerate(obj):
                result = self._find_key(i, searching_for, not_null)
                if result:
                    path.append(index)
                    path += result
                    return path

        return path
    def _path_parser(self, path):
        templist = []
        for i in path:
            if isinstance(i, str):
                templist.append(f"['{i}']")
            elif isinstance(i, int):
                templist.append(f"[{i}]")
        return ''.join(templist)
    def _node_parser(self, node: dict, idx: int):
        if node.get("video_url"):
            self.media[f"mp4{idx}"] = node.get("video_url")
        elif node["is_video"] == False:
            self.media[f"jpg{idx}"] = node["display_resources"][-1]['src']
            
    def public_media_extractor(self, publicmedia: dict):
        self.media = {}
        username = None
        caption = None
        date_posted = None
        profile_pic = None
        likes = None
        comments = None
        if sidecar := self._find_key(publicmedia, "edge_sidecar_to_children"):
            sidecar = eval(f"publicmedia{self._path_parser(sidecar)}")
            post = "multiple"
            for index, slide in enumerate(sidecar.get("edges")):
                self._node_parser(slide["node"], index)
        elif video := self._find_key(publicmedia, "video_url"):
            post = "reel"
            self.media["mp4"] = eval(f'publicmedia{self._path_parser(video)}')
        else:
            post = "image"
            self.media["jpg"] = eval(f"publicmedia{self._path_parser(self._find_key(publicmedia, 'display_resources'))}")[-1]['src']
        username = eval(f"publicmedia{self._path_parser(self._find_key(publicmedia, 'username'))}")
        caption_attempt = self._find_key(publicmedia, "text")
        if caption_attempt:
            caption = eval(f"publicmedia{self._path_parser(caption_attempt)}")
        if date_posted_attempt := self._find_key(publicmedia, "taken_at_timestamp"):
            date_posted = eval(f"publicmedia{self._path_parser(date_posted_attempt)}")
        if profile_pic_attempt := self._find_key(publicmedia, "profile_pic_url"):
            profile_pic = eval(f"publicmedia{self._path_parser(profile_pic_attempt)}")
        if likes_attempt := self._find_key(publicmedia, "edge_liked_by"):
            likes = eval(f"publicmedia{self._path_parser(likes_attempt)}").get('count')
        elif likes_attempt := self._find_key(publicmedia, "edge_media_preview_like"):
            likes = eval(f"publicmedia{self._path_parser(likes_attempt)}").get('count')
        if comments_attempt := self._find_key(publicmedia, "edge_media_to_comment"):
            comments = eval(f"publicmedia{self._path_parser(comments_attempt)}").get('count')
        self.result = {"media": self.media, "username": username, "post": post, "caption": caption, 
                       "posted": date_posted, "profile_pic": profile_pic, "likes": likes, "comments": comments}
    async def _get_csrf_token(self, link: str):
        patterncsrf = re.compile(r"{\"csrf_token\":\"(.*?)\"}")
        matches = None
        async with self.session.get(link, headers=self.headers, cookies=self.cookies, proxy=self.proxy) as r:
            self.logger.debug(self._format_request_info(r.request_info))
            while True:
                chunk = await r.content.read(1024)
                if not chunk:
                    break
                chunk = chunk.decode("utf-8")
                if matches := re.findall(patterncsrf, chunk):
                    break
        if not matches:
            raise self.get_info_fail(f"couldnt get a csrf token")
        self.csrf = matches[0]
        with open("csrf.txt", 'w') as f1:
            f1.write(f"{self.csrf} EXPIRY {(datetime.now()+timedelta(hours=6)).isoformat()}")
        self.cookies['csrftoken'] = self.csrf
    async def _embed_captioned(self, link: str):
        patternshortcode = r"https://(?:www)?\.instagram\.com/(?:reels||p||stories||reel||story)/(.*?)/?$"
        shortcode = re.findall(patternshortcode, link.split("?")[0])[0]
        headers = {
            'authority': 'www.instagram.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'max-age=0',
            'referer': f'https://www.instagram.com/p/{shortcode}/embed/captioned/',
            'sec-fetch-mode': 'navigate',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        async with self.session.get(f'https://www.instagram.com/p/{shortcode}/embed/captioned/', headers=headers, proxy=self.proxy) as r:
            self.logger.debug(self._format_request_info(r.request_info))
            rtext = await r.text(encoding="utf-8")
            if matches := re.findall(r"u\d\d\d\d", rtext):
                for match in matches:
                    rtext = rtext.replace(match, f"\\{match}".encode("utf-8").decode("unicode_escape"))
            with open("embed_captioned.txt","w", encoding="utf-8") as f1:
                f1.write(rtext)
            return rtext
    def embed_captioned_extractor(self, response: str):
 
        response = response.replace("\\\\/", "/").replace("\\", "")
        embedpattern = r"\"contextJSON\":\"((?:.*?)})\""
        self.media = {}
        date_posted = None
        username = None
        caption = None
        date_posted = None
        profile_pic = None
        likes = None
        comments = None
        if matches := re.findall(embedpattern, response):
            incasepattern = r"caption_title_linkified\":\"(.*?)\","
            matches = [re.sub(incasepattern, 'caption_title_linkified": "nuh uh",', matches[0])]
            matches = unescape(matches[0])
            thejay = json.loads(matches)
            with open("embed_captioned.json", "w") as f1:
                json.dump(thejay, f1, indent=4)
            if thejay.get("gql_data"):
                self.public_media_extractor(thejay.get("gql_data"))
                return
            ctxmedia: dict = thejay["context"]["media"]
            if not ctxmedia:
                raise self.no_media(f"No media found! Perhaps age restricted?")
            if ctxmedia.get("edge_sidecar_to_children"):
                post = 'multiple'
                for index, node in enumerate(ctxmedia["edge_sidecar_to_children"]["edges"]):
                    if node['is_video'] == True:
                        self.media[f'mp4{index}'] = node['video_url'].replace("u0025", "%")
                    else:
                        self.media[f'jpg{index}'] = node['display_resources'][-1]['src'].replace("u0025", "%")
            else:
                if ctxmedia['is_video'] == True:
                    post='reel'
                    self.media['mp4'] = ctxmedia['video_url'].replace("u0025", "%")
                else:
                    post='single'
                    self.media['jpg'] = ctxmedia['display_resources'][-1]['src'].replace("u0025", "%")
            username = eval(f"thejay{self._path_parser(self._find_key(thejay, 'username'))}")
            caption_attempt = self._find_key(thejay, "caption")
            if caption_attempt:
                caption = eval(f"thejay{self._path_parser(caption_attempt)}")
                caption = caption.replace("<br />" ,"\n").replace("</a>", "")
                caption = re.sub(r'<a href=\\\"(?:.*?)>', '', caption)
            if date_posted_attempt := self._find_key(thejay, "taken_at_timestamp"):
                date_posted = eval(f"thejay{self._path_parser(date_posted_attempt)}")
            if profile_pic_attempt := self._find_key(thejay, "profile_pic_url"):
                profile_pic = eval(f"thejay{self._path_parser(profile_pic_attempt)}")
            if likes_attempt := self._find_key(thejay, "likes_count"):
                likes = eval(f"thejay{self._path_parser(likes_attempt)}")
            if comments_attempt := self._find_key(thejay, "edge_media_to_comment"):
                comments = eval(f"thejay{self._path_parser(comments_attempt)}").get('count')
            self.result = {"media": self.media, "username": username, "post": post, "caption": caption, 
                        "posted": date_posted, "profile_pic": profile_pic, "likes": likes, "comments": comments}
        else:
            imagepattern = r"<img class=\"EmbeddedMediaImage\" alt=\"(?:.*?)\" src=\"(.*?)\""
            image = re.findall(imagepattern, response)
            if not image:
                return None
            self.media['jpg'] = unescape(image[0])
            post = 'image'
            username = re.findall(r"<span class=\"UsernameText\">(.*?)<", response)[0]
            caption_pattern = r"<br />(.*?)<div class=\"CaptionComments\">"
            caption = re.findall(caption_pattern, response)
            if caption:
                caption = caption[0].replace("<br />" ,"\n").replace("</a>", "")
                caption = re.sub(r'<a href=\"(?:.*?)>', '', caption)
            self.result = {"media": self.media, "username": username, "post": post, "caption": caption if caption else None, 
                        "posted": date_posted, "profile_pic": profile_pic, "likes": likes, "comments": comments}
    async def _downloader(self, filename, url):
        async with aiofiles.open(filename, 'wb') as f1:
            async with self.session.get(URL(url, encoded=True)) as r:
                self.logger.debug(self._format_request_info(r.request_info))
                progress = tqdm(total=int(r.headers.get('content-length')), unit='iB', unit_scale=True, colour="green")
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                    progress.update(len(chunk))
                progress.close()
    async def _download_post(self):
        index = 0
        filenames = []
        for key, value in self.result.get('media').items():
            if key.startswith("mp4"):
                filename = f"{self.result['username']}-{int(datetime.now().timestamp())}-{index}.mp4"
            elif key.startswith("jpg"):
                filename = f"{self.result['username']}-{int(datetime.now().timestamp())}-{index}.jpg"
            await self._downloader(filename, value)
            filenames.append(filename)
            index += 1
        return filenames
    async def _get_highlights(self, link: str):
        async with self.session.get(link, headers=self.headers, cookies=self.cookies, proxy=self.proxy) as r:
            self.logger.debug(self._format_request_info(r.request_info))
            response = await r.text("utf-8")
            pattern = r"({\"require\":\[\[\"ScheduledServerJS\",\"handle\",null,\[\{\"__bbox\":{\"require\":\[\[\"RelayPrefetchedStreamCache\",\"next\",\[\],\[\"adp_PolarisStoriesV\dHighlightsPageQueryRelayPreloader_(?:.*?)\",{\"__bbox\"(?:.*?),{\"__bbox\":null}]]]})</script>"
            if not (matches := re.findall(pattern, response)):
                raise self.no_media(f"couldnt find media in highlights")
            jsonized = json.loads(matches[0])
            with open("highlights.json", "w") as f1:
                json.dump(jsonized, f1, indent=4)
            if not (path_to_items := self._find_key(jsonized, "items")):
                raise self.no_media(f"couldnt grab items of highlights")
            items = eval(f"jsonized{self._path_parser(path_to_items)}")
            self.media = {}
            for index, item in enumerate(items):
                if item.get('video_versions'):
                    self.media[f"mp4{index}"] = item.get('video_versions')[0]['url']
                elif item.get('image_versions2'):
                    self.media[f"jpg{index}"] = item['image_versions2']['candidates'][0].get('url')
            username = eval(f"jsonized{self._path_parser(self._find_key(jsonized, 'username'))}")
            profile_pic = eval(f"jsonized{self._path_parser(self._find_key(jsonized, 'profile_pic_url'))}")
            if not (thumbnail := eval(f"jsonized{self._path_parser(self._find_key(jsonized, 'full_image_version'))}")):
                thumbnail = eval(f"jsonized{self._path_parser(self._find_key(jsonized, 'cropped_image_version'))}").get('url')
            date_posted = eval(f"jsonized{self._path_parser(self._find_key(jsonized, 'latest_reel_media'))}")
            self.result = {"media": self.media, "username": username, "post": "highlights", "caption": None, 
                        "posted": date_posted, "profile_pic": profile_pic, "likes": None, "comments": None, "thumbnail": thumbnail}
    async def _get_story(self, link: str):
        story_pattern = r"({\"require\":\[\[\"ScheduledServerJS\",\"handle\",null,\[\{\"__bbox\":{\"require\":\[\[\"RelayPrefetchedStreamCache\",\"next\",\[\],\[\"adp_PolarisStoriesV3ReelPageStandalone(?:.*?))</script>"
        async with self.session.get(link, headers=self.headers, cookies=self.cookies, proxy=self.proxy) as r:
            self.logger.debug(self._format_request_info(r.request_info))
            response = await r.text("utf-8")
            if not (matches := re.findall(story_pattern, response)):
                raise self.get_info_fail(f"couldnt grab info from story")
        jsoner = json.loads(matches[0])
        with open("story.json", "w") as f1:
            json.dump(jsoner, f1, indent=4)
        patternmediaid = r"https://(?:www\.)?instagram\.com/stories/(?:.*?)/(.*?)/?$"
        mediaid = re.findall(patternmediaid, link)[0]
        items = eval(f"jsoner{self._path_parser(self._find_key(jsoner, 'items'))}")
        self.media = {}
        for index, item in enumerate(items):
            if item['pk'] == mediaid:
                if item.get('video_versions'):
                    self.media[f'mp4{index}'] = item['video_versions'][0]['url']
                elif item.get('image_versions2'):
                    self.media[f"jpg{index}"] = item['image_versions2']['candidates'][0]['url']
        username = eval(f"jsoner{self._path_parser(self._find_key(jsoner, 'reels_media'))}")[0].get('user').get('username')
        profile_pic = eval(f"jsoner{self._path_parser(self._find_key(jsoner, 'profile_pic_url'))}")
        date_posted = eval(f"jsoner{self._path_parser(self._find_key(jsoner, 'latest_reel_media'))}")
        self.result = {"media": self.media, "username": username, "post": "story", "caption": None, 
                                "posted": date_posted, "profile_pic": profile_pic, "likes": None, "comments": None,}
    async def _csrf_check(self, link: str):
        if not hasattr(self, "csrf"):
            if not os.path.exists("csrf.txt"):
                await self._get_csrf_token(link)
            else:
                with open("csrf.txt", "r") as f1:
                    read = f1.read()
                    csrf, expiry = read.split(" EXPIRY ")[0], read.split(" EXPIRY ")[1]
                    if datetime.now() > datetime.fromisoformat(expiry):
                        await self._get_csrf_token(link)
                    else:
                        self.csrf = csrf
                        self.cookies['csrftoken'] = self.csrf
    async def _get_info_from_source(self, link):
        allmedia =r'(\{\"require\":\[\[\"ScheduledServerJS\",\"handle\",null,\[\{\"__bbox\":\{\"require\":\[\[\"RelayPrefetchedStreamCache\",\"next\",\[\],\[\"adp_PolarisPostRoot(?:.*?))</script>'
        patternmediaid = r"content=\"instagram://media\?id=(.*?)\""
        try:
            async with self.session.get(link, headers=self.headers, cookies=self.cookies, proxy=self.proxy) as r:
                self.logger.debug(self._format_request_info(r.request_info))
                response = await r.text("utf-8")
                with open("response.txt", "w", encoding="utf-8") as f1:
                    f1.write(response)
        except aiohttp.TooManyRedirects:
            self.logger.info(f"{Fore.RED}Too many redirects! get a new sessionid{Fore.RESET}")
            raise self.badsessionid(f"get a new sessionid!")
        if not (mediaid := re.findall(patternmediaid, response)):
            post = json.loads(re.findall(allmedia, response)[0])
        if not (matches := re.findall(allmedia, response)):
            raise self.get_info_fail(f"couldnt grab info from post")
        post = json.loads(matches[0])
        with open("post.json", "w") as f1:
            json.dump(post, f1, indent=4)
        return post
    async def _get_post(self, link: str):

        async with self.session.get(link, headers=self.headers, proxy=self.proxy) as r:
            self.logger.debug(self._format_request_info(r.request_info))
            response = await r.text("utf-8")
            with open("response.txt", "w", encoding="utf-8") as f1:
                f1.write(response)

        patternmediaid = r"content=\"instagram://media\?id=(.*?)\""
        mediaid = re.findall(patternmediaid, response)
        if mediaid:
            if not hasattr(self, "csrf"):
                patterncsrf = re.compile(r"{\"csrf_token\":\"(.*?)\"}")
                csrf = re.findall(patterncsrf, response)
                self.csrf = csrf[0]
            self.headers['x-csrftoken'] = self.csrf
            self.headers['x-ig-app-id'] = "936619743392459"
            async with self.session.get(f"https://www.instagram.com/api/v1/media/{mediaid[0]}/info", headers = self.headers, cookies=self.cookies, proxy=self.proxy) as r:
                self.logger.debug(self._format_request_info(r.request_info))
                response = await r.text(encoding="utf-8")
                post = json.loads(response)
        else:
            post = await self._get_info_from_source(link)
        carous = self._find_key(post, 'carousel_media')
        itms = self._find_key(post, 'items')
        items = eval(f"post{self._path_parser(carous if carous else itms)}")
        with open("post.json", "w") as f1:
            json.dump(post, f1, indent=4)
        self.media = {}
        if isinstance(items, dict) and items.get('message') and "Media not found" in items['message'] and items['status'] == 'fail':
            post = await self._get_info_from_source(link)
            finder = self._path_parser(self._find_key(post, 'items'))
            if not finder:
                raise self.no_media(f"Instagram couldn't return any media")
            items = eval(f"post{finder}")
            if post == items:
                raise self.no_media(f"Instagram couldn't return any media")
        elif isinstance(items, dict) and items.get('message') and 'checkpoint' in items['message']:
            raise self.badsessionid(f"login to ur account and solve captcha\n{items['checkpoint_url']}")
        for index, item in enumerate(items):
            if item.get('video_versions'):
                self.media[f'mp4{index}'] = item['video_versions'][0]['url']
            elif item.get('image_versions2'):
                self.media[f"jpg{index}"] = item['image_versions2']['candidates'][0]['url']
        post_type = 'reel' if len(self.media.keys()) == 1 and list(self.media.keys())[0].startswith("mp4") else "image" if len(self.media.keys()) == 1 and list(self.media.keys())[0].startswith("jpg") else "multiple"
        user = eval(f"post{self._path_parser(self._find_key(post, 'owner'))}")
        username = user.get('username')
        profile_pic = user.get('profile_pic_url')
        likes = eval(f"post{self._path_parser(self._find_key(post, 'like_count'))}")
        comments = eval(f"post{self._path_parser(self._find_key(post, 'comment_count', False))}")
        caption = eval(f"post{self._path_parser(self._find_key(post, 'caption', False))}")
        if caption:
            caption = caption.get("text")
        date_posted = eval(f"post{self._path_parser(self._find_key(post, 'taken_at'))}")
        music = {}
        if (music_attempt := self._find_key(post, "music_metadata")) and (music_data := eval(f"post{self._path_parser(music_attempt)}")):
            if music_data.get('music_info'):
                music['url'] = music_data['music_info']['music_asset_info']['progressive_download_url']
                music['title'] = music_data['music_info']['music_asset_info']['title']
                music['artist'] = music_data['music_info']['music_asset_info']['display_artist']
                music['start_time'] = f"{int((music_data['music_info']['music_consumption_info']['audio_asset_start_time_in_ms']/1000)//60):02}:{int((music_data['music_info']['music_consumption_info']['audio_asset_start_time_in_ms']/1000)%60):02}"
                music['duration'] = music_data['music_info']['music_consumption_info']['overlap_duration_in_ms']/1000
        self.result = {"media": self.media, "username": username, "post": post_type, "caption": caption, 
                        "posted": date_posted, "profile_pic": profile_pic, "likes": likes, "comments": comments, 'music': music}
    async def _download(self, link: str, handle_merge: bool = True, public_only: bool = True, proxy: str = None, dont_download: bool = False):
        if ('stories' in link or 'highlights' in link) and public_only:
            raise ValueError(f"cant grab stories without credentials")
        self.result = None
        if public_only:
            await self._csrf_check(link)
            graphql = await self._graphql_api(link)
            if graphql:
                self.public_media_extractor(graphql)
            else:
                self.logger.debug(f"Grabbing post from embed")
                embed_captioned = await self._embed_captioned(link)
                self.embed_captioned_extractor(embed_captioned)
        else:
            if "highlights" in link:
                await self._get_highlights(link)
            elif "stories" in link:
                await self._get_story(link)

            else:
                await self._get_post(link)
        if not self.result:
            raise self.get_info_fail(f"couldnt find anything")
        if not dont_download:
            filenames = await self._download_post()
            if handle_merge and self.result.get('music') and self.result.get('post') == 'image':
                process = await asyncio.subprocess.create_subprocess_exec("ffmpeg", *["-version"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                result = await process.wait()
                if result != 0:
                    self.logger.info(f"You dont have ffmpeg installed, can't merge image with music")
                    self.result['filenames'] = filenames
                    return
                self.logger.info(f"downloading music")
                clear = lambda x: "".join([i for i in x if i not in "\\/:*?<>|()"])
                filename = f"{clear(self.result['music']['title'])}-{int(datetime.now().timestamp())}.mp3"
                await self._downloader(filename, self.result['music'].get('url'))
                image = cv2.imread(filenames[0])
                height, width, _ = image.shape
                if height % 2 != 0:
                    height -= 1
                if width % 2 != 0:
                    width -= 1
                image = cv2.resize(image, (width, height))
                cv2.imwrite(filenames[0], image)
                process = await asyncio.create_subprocess_exec("ffmpeg", *["-loop", "1", "-r", "2", "-i", filenames[0], "-i", filename, "-ss", self.result['music'].get('start_time'), "-t",str(self.result['music']['duration']),"-c:a", "copy", filenames[0].replace('jpg', 'mp4'), '-v', 'error'])
                await process.wait()
                if os.path.exists(filenames[0].replace('jpg', 'mp4')):
                    filenames.append(filenames[0].replace('jpg', 'mp4'))
                os.remove(filename)
            self.result['filenames'] = filenames
    async def download(self, link: str, handle_merge: bool = True, public_only: bool = True, proxy: str = None, verbose: bool = False, dont_download: bool = False):
        if verbose:
            logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")
        self.logger = logging.getLogger(__name__)
        if not public_only:
            if not self.sessionid:
                self.get_credentials()
            else:
                self.cookies = {"sessionid": self.sessionid}
        else:
            self.cookies = {}
        self.headers = {
            'authority': 'www.instagram.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.7',
            'sec-fetch-mode': 'navigate',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        if not hasattr(self, "session"):
            async with aiohttp.ClientSession(connector=self.giveconnector(proxy)) as session:
                self.session = session
                await self._download(link, handle_merge, public_only, proxy, dont_download)
        else:
            await self._download(link, handle_merge, public_only, proxy, dont_download)
        return self.result
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='download instagram posts and reels')
    parser.add_argument("link", type=str, help='link to instagram post or reel')
    parser.add_argument("--handle-merge", "-m", action="store_true", help="whether to not merge and let you do it")
    parser.add_argument("--public-only", "-api", action="store_true", help="whether to use public api for posts")
    parser.add_argument("--proxy", "-p", type=str, help="proxy to use")
    parser.add_argument("--verbose", "-v", action="store_true", help="use verbose debugging")
    parser.add_argument("--no-download", "-nd", action="store_true", help="whether to not download the post and just return the data")
    args = parser.parse_args()
    if '?' in args.link:
        args.link = args.link
    insta = instadownloader()
    asyncio.run(insta.download(args.link, handle_merge=not args.handle_merge, public_only=args.public_only, proxy=args.proxy, verbose=args.verbose))
    if not insta.result:
        print('error occured')
    else:
        print('\n')
        print(json.dumps(insta.result, indent=4, ensure_ascii = False))
