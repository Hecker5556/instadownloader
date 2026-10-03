import aiohttp
from aiohttp_socks import ProxyConnector
import aiofiles
import asyncio
import json
import traceback
import re
import os
import logging
import mimetypes
from datetime import datetime

class InstagramDownloader:
    def __init__(self, session: aiohttp.ClientSession = None, cookies: dict[str, str] = None, 
                 proxy: str = None, ffmpeg_path: str = None, fileLock: asyncio.Lock = asyncio.Lock()):
        self.session = session
        self.cookies = cookies
        self.csrf = None
        if (self.cookies is not None and 'csrftoken' in self.cookies):
            self.csrf = True
        self.proxy = proxy
        self.closeSession: bool = False
        self.pageResponse: str  = None
        self.logger = logging.getLogger(__name__)
        self.debug = False
        self.lock = fileLock
        self.ffmpeg_path = "ffmpeg" if ffmpeg_path is None else ffmpeg_path
    @staticmethod
    def make_file_name(filename):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    async def __aenter__(self):
        if (self.session is None):
            self.session = aiohttp.ClientSession(connector=ProxyConnector.from_url(self.proxy) if self.proxy is not None else aiohttp.TCPConnector())
            self.closeSession = True
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            "accept-Encoding": "gzip, deflate",
            'accept-language': 'en-US,en;q=0.6',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="136", "Brave";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-full-version-list': '"Chromium";v="136.0.0.0", "Brave";v="136.0.0.0", "Not.A/Brand";v="99.0.0.0"',
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
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        }
        return self
    async def __aexit__(self, exc, b, tb):
        if self.closeSession:
            await self.session.close()
        if (exc):
            traceback.print_exception(exc, b, tb)
    async def fetchCSRF(self, link: str = "https://instagram.com"):
        async with self.session.get(link, headers=self.headers, cookies=self.cookies) as r:
            task = asyncio.create_task(self.handleRequest(r))
            if r.cookies.get("csrftoken") is not None and len(r.cookies.get("csrftoken").value) > 0:
                if link != "https://instagram.com":
                    self.pageResponse = await r.text("utf-8")
                # await task
                return r.cookies.get("csrftoken").value
            else:
                csrfPattern = r"{\"csrf_token\":\"(.*?)\"}"
                data = await r.text("utf-8")
                if link != "https://instagram.com":
                    self.pageResponse = data
                csrfMatch = await asyncio.to_thread(re.search, csrfPattern, data)
                if (csrfMatch):
                    # await task
                    return csrfMatch.group(1)
                else:
                    # await task
                    return None
            
    async def getCSRF(self, link: str = None, ignoreCache: bool = False):
        await self.lock.acquire()
        if not os.path.exists(self.make_file_name("csrf_token")) or ignoreCache:
            csrf = await self.fetchCSRF(link)
            if not csrf:
                self.lock.release()
                return None
        else:
            
            async with aiofiles.open(self.make_file_name("csrf_token"), "r") as f1:
                try:
                    mapping: dict[str, str] = await asyncio.to_thread(json.loads, await f1.read())
                except:
                    mapping = {}
            if self.proxy:
                csrf = mapping.get(self.proxy)
                if not csrf:
                    csrf = await self.fetchCSRF(link)
                else:
                    self.lock.release()
                    return csrf
            else:
                csrf = mapping.get("B")
                if not csrf:
                    csrf = await self.fetchCSRF(link)
                else:
                    self.lock.release()
                    return csrf
        async with aiofiles.open(self.make_file_name("csrf_token"), "w") as f1:
            if self.proxy:
                await f1.write(json.dumps({self.proxy: csrf}))
            else:
                await f1.write(json.dumps({"B": csrf}))
        self.lock.release()
        return csrf
    async def _updateCSRF(self, r: aiohttp.ClientResponse):
        if r.cookies.get("csrftoken") is not None and len(r.cookies.get("csrftoken").value) > 0:
            await self.lock.acquire()
            async with aiofiles.open(self.make_file_name("csrf_token"), "r") as f1:
                data = await asyncio.to_thread(json.loads, await f1.read())
            if self.proxy:
                data[self.proxy] = r.cookies.get("csrftoken").value
            else:
                data["B"] = r.cookies.get("csrftoken").value
            if self.cookies is not None:
                self.cookies.update({"csrftoken": r.cookies.get("csrftoken").value})
            async with aiofiles.open(self.make_file_name("csrf_token"), "w") as f1:
                await f1.write(await asyncio.to_thread(json.dumps, data))
            self.lock.release()
        new_cookies = {key: morsel.value for key, morsel in r.cookies.items()}
        if self.cookies is not None:
            self.cookies.update(new_cookies)
    def logRequest(self, r: aiohttp.ClientResponse):
        self.logger.debug(f"Sent a {r.method} request to {r.request_info.url} ({r.url}), status: {r.status}")
        self.logger.debug(f"Headers sent:\n{json.dumps(dict(r.request_info.headers), indent=4)}")
        self.logger.debug(str(r.cookies))
    async def handleRequest(self, r: aiohttp.ClientResponse):
        await asyncio.gather(*[self._updateCSRF(r), asyncio.to_thread(self.logRequest, r)])
    @staticmethod
    def make_cookie_string(cookies: dict):
        cookie = ""
        for key, value in cookies.items():
            cookie += f"{key}={value}; "
        return cookie
    async def graphQLFetch(self, shortCode: str):
        data = {
            '__d': 'www',
            '__a': '1',

            'variables': '{"shortcode":"%s"}' % shortCode,
            'doc_id': '10015901848480474'
            }
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'priority': 'u=1, i',
            'referer': f'https://www.instagram.com/p/{shortCode}',
            'sec-ch-ua': '"Brave";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Brave";v="149.0.0.0", "Chromium";v="149.0.0.0", "Not)A;Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
            'x-csrftoken': self.headers.get('x-csrftoken', self.cookies.get('csrftoken') if self.cookies is not None else None),
            'x-ig-app-id': '936619743392459',
            "cookie": self.make_cookie_string(self.cookies),
        }
        async with self.session.post("https://www.instagram.com/graphql/query", data=data, headers=headers) as r:
            task = asyncio.create_task(self.handleRequest(r))
            response = await r.text("utf-8")
            try:
                responseJson: dict = await asyncio.to_thread(json.loads, response)
                if self.debug:
                    await self.lock.acquire()
                    async with aiofiles.open(self.make_file_name("graphql.json"), "w", encoding="utf-8") as f1:
                        await f1.write(await asyncio.to_thread(json.dumps, responseJson, ensure_ascii=False))
                    self.lock.release()
                    self.logger.debug(f"Wrote graphql json to {self.make_file_name('graphql.json')}")
                if responseJson.get('data') is None or not responseJson['data'].get("xdt_shortcode_media") or responseJson.get("status") == "fail":
                    self.logger.debug("Couldnt find media in graphql response")
                    return -1
                return responseJson
            except json.JSONDecodeError:
                self.logger.debug(f"Failed to json load graphql response")
                if self.debug:
                    await self.lock.acquire()
                    async with aiofiles.open(self.make_file_name("graphql"), "w", encoding="utf-8") as f1:
                        await f1.write(response)
                    self.lock.release()
                    self.logger.debug(f"Wrote bad graphql response to {self.make_file_name('graphql')}")
                return -1
    @staticmethod
    def find(obj, searchedKey: str):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == searchedKey:
                    return value
                result = InstagramDownloader.find(value, searchedKey)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for i in obj:
                result = InstagramDownloader.find(i, searchedKey)
                if result is not None:
                    return result
        return None
    @staticmethod
    def findCaption(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "caption" and value is not None and value.get("text") is not None and value.get("pk") is not None:
                    return value
                result = InstagramDownloader.findCaption(value)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for i in obj:
                result = InstagramDownloader.findCaption(i)
                if result is not None:
                    return result
        return None
    @staticmethod
    def graphQLExtract(graphQLResponse: dict, h264Only: bool = False):
        data = {
            "username": None,
            "caption": None,
            "datePosted": None,
            "profilePicture": None,
            "likes": None,
            "comments": None,
            "media": [],
            "music": None,
            "type": None,
        }
        if (sidecar := InstagramDownloader.find(graphQLResponse, "edge_sidecar_to_children")):
            data['type'] = 'multiple'
            for index, slide in enumerate(sidecar.get("edges")):
                data['media'].append(InstagramDownloader.makeMediaItem(slide['node'], h264Only))
        else:
            data['media'].append(InstagramDownloader.makeMediaItem(graphQLResponse['data']['xdt_shortcode_media'], h264Only))
            data['type'] = data['media'][0]['type']
        if (ownerInfo := InstagramDownloader.find(graphQLResponse, "owner")):
            data['username'] = ownerInfo.get('username')
            data['profilePicture'] = ownerInfo.get('profile_pic_url')
        if (captionText := InstagramDownloader.find(graphQLResponse, "text")):
            data['caption'] = captionText
        if (datePosted := InstagramDownloader.find(graphQLResponse, "taken_at_timestamp")):
            data['datePosted'] = datePosted
        if (likes := InstagramDownloader.find(graphQLResponse, "edge_liked_by")):
            data['likes'] = likes.get('count')
        elif (likes := InstagramDownloader.find(graphQLResponse, "edge_media_preview_like")):
            data['likes'] = likes.get('count')
        if (comments := InstagramDownloader.find(graphQLResponse, "edge_media_to_comment")):
            data['comments'] = comments.get('count')
        if (music := InstagramDownloader.find(graphQLResponse, "clips_music_attribution_info")):
            data['music'] = {
                'id': music['audio_id'],
                'title': music['song_name'],
                'artist': music['artist_name'],
            }
        return data
    async def sourceFetch(self, link: str, shortCode: str):
        scriptsPattern = r"<script[^>]*>((?:.*?)" +  f"(?:{shortCode})?" + r"(?:image_versions|video_versions)(?:.*?)" + f"(?:{shortCode})?" + r"(?:.*?))</script>"
        if self.pageResponse is None:
            self.headers["cookie"] = self.make_cookie_string(self.cookies)
            async with self.session.get(link, headers=self.headers) as r:
                task = asyncio.create_task(self.handleRequest(r))
                self.pageResponse = await r.text("utf-8")
        script = await asyncio.to_thread(re.search, scriptsPattern, self.pageResponse)

        await self.lock.acquire()
        async with aiofiles.open(self.make_file_name("source"), "w", encoding="utf-8") as f1:
            await f1.write(self.pageResponse)
        self.lock.release()
        self.logger.debug("Written to source")
        if not script:
            self.logger.debug(f"Couldnt find post info in source")
            return -1
        script = script.group(1)
        try:
            infoJson = await asyncio.to_thread(json.loads, script)
        except json.JSONDecodeError as e:
            self.logger.debug(f"Failed to decode json: {e}")
            await self.lock.acquire()
            async with aiofiles.open(self.make_file_name("source"), "w", encoding="utf-8") as f1:
                await f1.write(self.pageResponse)
            self.lock.release()
            self.logger.debug(f"Written to {self.make_file_name('source')}")
            return -1
        if self.debug:
            await self.lock.acquire()
            async with aiofiles.open(self.make_file_name("source.json"), "w", encoding="utf-8") as f1:
                await f1.write(await asyncio.to_thread(json.dumps, infoJson, ensure_ascii=False))
            self.lock.release()
            self.logger.debug(f"Written to {self.make_file_name('source.json')}")
        return infoJson
    @staticmethod
    def makeMediaItem(item: dict, h264Only: bool = False):
        dashPattern = r"bandwidth=\"(\d+)\" codecs=\"(.*?)\"(?:.*?)FBContentLength=\"(\d+)\"(?:.*?)FBQualityLabel=\"(\d+p)\"><BaseURL>(.*?)</BaseURL>"
        audioPattern = r"contentType=\"audio\"(?:.*?)bandwidth=\"(\d+)\" codecs=\"(.*?)\"(?:.*?)FBContentLength=\"(\d+)\"(?:.*?)<BaseURL>(.*?)</BaseURL>"
        if (item.get("is_video") is not None and item.get("is_video") == False) or (item.get("video_url") is None and item.get("video_versions") is None):
            if item.get("image_versions2") is not None:
                return {
                    'url': item['image_versions2']['candidates'][0]['url'],
                    'type': 'image'
                }
            else:
                return {
                    'url': item['display_resources'][-1]['src'],
                    'type': 'image',
                }
        else:
            if (item.get('video_dash_manifest') or item.get("dash_info")) and not h264Only:
                if item.get("video_dash_manifest"):
                    item['video_dash_manifest'] = re.sub(r"\&amp;", "&", item['video_dash_manifest'])
                else:
                    item['video_dash_manifest'] = re.sub(r"\&amp;", "&", item['dash_info']['video_dash_manifest'])
                videoFormatMatches = re.findall(dashPattern, item['video_dash_manifest'])
                dashInfo = {
                    'type': 'dash',
                    'videos': [],
                    'audio': {},
                }
                for bandwidth, codec, contentLength, quality, url in videoFormatMatches:
                    dashInfo['videos'].append({
                        'bitrate': bandwidth,
                        'codec': codec,
                        'contentLength': contentLength,
                        'quality': quality,
                        'url': url,
                    })
                dashInfo['videos'] = list(sorted(dashInfo['videos'], key=lambda x: int(x['contentLength']), reverse=True))
                audioMatch = re.search(audioPattern, item['video_dash_manifest'])
                if audioMatch:
                    dashInfo['audio'] = {
                        'bitrate': audioMatch.group(1),
                        'codec': audioMatch.group(2),
                        'contentLength': audioMatch.group(3),
                        'url': audioMatch.group(4),
                    }
                return dashInfo
            else:
                if item.get("video_versions"):
                    return {
                        'url': item['video_versions'][0]['url'],
                        'type': 'video',
                    }
                else:
                    return {
                        'url': item['video_url'],
                        'type': 'video',
                    }
    @staticmethod
    def sourceExtract(source: dict, h264Only: bool = False):
        data = {
            "username": None,
            "caption": None,
            "datePosted": None,
            "profilePicture": None,
            "likes": None,
            "comments": None,
            "media": [],
            "type": None,
        }
        
        if userInfo := InstagramDownloader.find(source, "user"):
            data['username'] = userInfo.get("username")
            data['profilePicture'] = userInfo.get("profile_pic_url")
        if captionText := InstagramDownloader.findCaption(source):
            data['caption'] = captionText.get("text")
        if datePosted := InstagramDownloader.find(source, "taken_at"):
            data['datePosted'] = datePosted
        if likes := InstagramDownloader.find(source, "like_count"):
            data['likes'] = likes
        if comments := InstagramDownloader.find(source, "comment_count"):
            data['comments'] = comments
        if carouselMedia := InstagramDownloader.find(source, "carousel_media"):
            data['type'] = 'multiple'
            for item in carouselMedia:
                data['media'].append(InstagramDownloader.makeMediaItem(item, h264Only))
        else:
            media = InstagramDownloader.find(source, "media")
            if media:
                data['media'].append(InstagramDownloader.makeMediaItem(media, h264Only))
                data['type'] = data['media'][0]['type']
            else:

                items = InstagramDownloader.find(source, "items")
                if items:
                    data['media'].append(InstagramDownloader.makeMediaItem(items[0], h264Only))
                    data['type'] = data['media'][0]['type']
                else:
                    gated = InstagramDownloader.find(source, "if_not_gated_logged_out")
                    data['media'].append(InstagramDownloader.makeMediaItem(gated, h264Only))
                    data['type'] = data['media'][0]['type']
        if (musicAssetInfo := InstagramDownloader.find(source, "music_asset_info")):
            data['music'] = {
                'id': musicAssetInfo['audio_cluster_id'],
                'title': musicAssetInfo['title'],
                'artist': musicAssetInfo['display_artist']
            }
        return data

    async def embedFetch(self, shortCode):
        headers = {
            'authority': 'www.instagram.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'max-age=0',
            'referer': f'https://www.instagram.com/p/{shortCode}/embed/captioned/',
            'sec-fetch-mode': 'navigate',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            "cookie": self.make_cookie_string(self.cookies),
        }
        async with self.session.get(f'https://www.instagram.com/p/{shortCode}/embed/captioned/', headers=headers) as r:
            task = asyncio.create_task(self.handleRequest(r))
            text = await r.text("utf-8")
            if self.debug:
                await self.lock.acquire()
                async with aiofiles.open(self.make_file_name("embed_captioned"), "w", encoding="utf-8") as f1:
                    await f1.write(text)
                self.lock.release()
        return text
    @staticmethod
    def embedExtract(embed):
        data = {
            "username": None,
            "caption": None,
            "datePosted": None,
            "profilePicture": None,
            "likes": None,
            "comments": None,
            "media": [],
            "type": None,
            'music': {},
        }
        contextJsonPattern = r"\"contextJSON\":\"\{.*?\}\""
        contextJson = re.search(contextJsonPattern, embed)
        found = False
        if (contextJson is not None):
            text = "{" + contextJson.group() + "}"
            first = json.loads(text)
            second = json.loads(first['contextJSON'])
            if (musicInfo := InstagramDownloader.find(second, "clips_music_attribution_info")):
                
                data['music'] = {
                    'id': musicInfo['audio_id'],
                    'title': musicInfo['song_name'],
                    'artist': musicInfo['artist_name']
                }
            if second['context']['media'] is not None:
                found = True
                if (owner := second['context']['media'].get("owner")):
                    data['username'] = owner.get("username")
                    data['profilePicture'] = owner.get("profile_pic_url")
                data['likes'] = second['context']['media']['edge_liked_by'].get('count')
                data['comments'] = second['context']['media']['edge_media_to_comment'].get('count')
                data['caption'] = second['context']['caption']
                data['datePosted'] = second['context']['media']['taken_at_timestamp']
                if (second['context']['media']['is_video']):
                    data['media'].append({
                        'type': 'video',
                        'url': second['context']['media']['video_url']
                    })
                    data['type'] = 'video'
                else:
                    data['media'].append({
                        'type': 'image',
                        'url': second['context']['media']['display_resources'][-1]['src']
                    })
                    data['type'] = 'image'
            elif (second.get('gql_data') is not None) and second['gql_data'].get("shortcode_media") is not None:
                found = True
                if (owner := second['gql_data']['shortcode_media'].get('owner')):
                    data['username'] = owner.get('username')
                    data['profilePicture'] = owner.get("profile_pic_url")
                data['likes'] = second['gql_data']['shortcode_media']["edge_liked_by"].get("count")
                data['comments'] = second['gql_data']['shortcode_media']["edge_media_to_comment"].get("count")
                data['caption'] = second['gql_data']['shortcode_media']["edge_media_to_caption"]["edges"][0]["node"].get("text")
                data['datePosted'] = second['gql_data']['shortcode_media']['taken_at_timestamp']
                if (second['gql_data']['shortcode_media']['is_video']):
                    data['media'].append({
                        'type': 'video',
                        'url': second['gql_data']['shortcode_media']['video_url'],
                    })
                    data['type'] = 'video'
                else:
                    data['media'].append({
                        'type': 'image',
                        'url': second['gql_data']['shortcode_media']['display_resources'][-1]['src']
                    })
                    data['type'] = 'image'
            
        if not found:
            if username := (re.search(r"username=(.*?)\&", embed)):
                data['username'] = username.group(1)
            if img := (re.search(r"srcset=\"((?:.*?))\" /></a>", embed)):
                data['media'].append({
                    'type': 'image',
                    'url': img.group(1).split(",")[-1].split(" ")[0]
                })
            if caption := (re.search(r"<br />(.*?)<div class=\"CaptionComments\">", embed)):
                data['caption'] = caption.group(1)
        
        return data
    async def getMusicUrl(self, musicID: str):
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Brave";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Brave";v="149.0.0.0", "Chromium";v="149.0.0.0", "Not)A;Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
            "cookie": self.make_cookie_string(self.cookies),
        }
        data = f'audio_cluster_id={musicID}&max_id&original_sound_audio_asset_id={musicID}&__d=www&__a=1'
        async with self.session.post("https://www.instagram.com/api/v1/clips/music/", headers=headers, data=data) as r:
            text = await r.text("utf-8")
            info = await asyncio.to_thread(json.loads, text[len('for (;;);"')-1:])
            
        return await asyncio.to_thread(self.find, info, 'progressive_download_url')
    async def _downloadWorker(self, url, filename):
        async with aiofiles.open(filename, 'wb') as f1:
            self.headers['cookie'] = self.make_cookie_string(self.cookies)
            async with self.session.get(url, headers=self.headers) as r:
                task = asyncio.create_task(self.handleRequest(r))
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                ext = mimetypes.guess_extension(r.headers.get("content-type"))
        return ext
    async def _downloadPost(self, data: dict):
        now = str(int(datetime.now().timestamp()))
        if data['type'] == 'multiple':
            if os.path.exists(data['shortCode']) is False:
                os.mkdir(data['shortCode'])
            filename = os.path.join(data['shortCode'], f"{data['username']}-{now}")
        else:
            filename = f"{data['username']}-{now}"
        for idx, i in enumerate(data['media']):
            if i['type'] == 'image' or i['type'] == 'video':
                ext = await self._downloadWorker(i['url'], filename + f'-{idx}')
                if not ext and i['type'] == 'image':
                    ext = ".jpg"
                elif not ext and i['type'] == 'video':
                    ext = ".mp4"
                os.rename(filename + f'-{idx}', filename + f'-{idx}' + ext)
                data['filenames'].append(filename + f'-{idx}' + ext)
            elif i['type'] == 'dash':
                if i.get('audio'):
                    await asyncio.gather(*[self._downloadWorker(i['videos'][0]['url'], filename + f"-{idx}-video"), self._downloadWorker(i['audio'].get('url'), filename + f"-{idx}-audio")])
                    command = ["-i", filename + f"-{idx}-video", "-i", filename + f"-{idx}-audio", "-c", "copy", "-v", "error", filename + f"-{idx}.mp4"]
                    process = await asyncio.subprocess.create_subprocess_exec(self.ffmpeg_path, *command, stderr=asyncio.subprocess.PIPE)
                    await process.wait()
                    if (process.returncode != 0):
                        self.logger.info(f"FFmpeg errored combining video and audio stream\n{(await process.stderr.read()).decode()}")
                    os.remove(filename + f"-{idx}-video")
                    os.remove(filename + f"-{idx}-audio")
                else:
                    await self._downloadWorker(i['videos'][-1]['url'], filename + f"-{idx}.mp4")
                data['filenames'].append(filename + f"-{idx}.mp4")
    async def download(self, link: str, returnInfo: bool = False, h264Only: bool = False):
        """
        Args:
            link (str): link to a post
            returnInfo (bool): skip downloading the post and just return the data, default: False
            h264Only (bool): if true, get default h264 video instead of merging dash streams
        Returns:
            dict
        """
        if not self.csrf:
            csrf = await self.getCSRF(link)
            if csrf is None:
                raise Exception("Couldnt get csrftoken")
            if self.cookies is not None:
                self.cookies['csrftoken'] = csrf
            self.headers['x-csrftoken'] = csrf
        patternshortcode = r"https?://(?:www\.)?instagram\.com/(?:\S+/)?(?:reels|p|stories|reel|story|tv)/([^/?#]+)/?"
        if self.pageResponse:
            shortCode = (await asyncio.to_thread(re.search, r"\"shortcode\":\"(.*?\")", self.pageResponse))
            if shortCode is None:
                shortCode = await asyncio.to_thread(re.search, patternshortcode, link)
            shortCode = shortCode.group(1)
        else:
            shortCode = await asyncio.to_thread(re.search, patternshortcode, link)
            shortCode = shortCode.group(1)
        graphQL = await self.graphQLFetch(shortCode)
        if graphQL != -1:
            data = await asyncio.to_thread(InstagramDownloader.graphQLExtract, graphQL, h264Only)
        else:
            sourceJson = await self.sourceFetch(link, shortCode)
            if sourceJson != -1:
                data = await asyncio.to_thread(self.sourceExtract, sourceJson, h264Only)
            else:
                embedCaptioned = await self.embedFetch(shortCode)
                data = await asyncio.to_thread(self.embedExtract, embedCaptioned)
        if data.get('music'):
            data['music']['url'] = await self.getMusicUrl(data['music']['id'])
        
        data['filenames'] = []
        data['shortCode'] = shortCode
        if returnInfo:
            return data
        await self._downloadPost(data)
        return data

async def async_main(link, proxy, nodownload, no_h264, potential_cookies: list[str]):
    cookies = {}
    if potential_cookies[0] is not None:
        async with aiofiles.open(potential_cookies[0], "r") as f1:
            cookies_json = await asyncio.to_thread(json.loads, await f1.read())
            for cookie in cookies_json:
                if 'instagram.com' in cookie.get('domain', 'instagram.com'):
                    cookies[cookie['name']] = cookie['value']
    elif potential_cookies[1] is not None:
        async with aiofiles.open(potential_cookies[1], "r") as f1:
            text = await f1.read()
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                info = line.split("\t")
                if 'instagram.com' in info[0]:
                    cookies[info[5]] = info[6]
    elif potential_cookies[2] is not None:
        async with aiofiles.open(potential_cookies[2], "r") as f1:
            text = await f1.read()
            for cookie in text.split(";"):
                name, value = cookie.strip().split("=", 1)
                cookies[name] = value
    async with InstagramDownloader(
        proxy=proxy,
        cookies=cookies.copy() if len(cookies) > 0 else None,
    ) as insta:
        insta.debug = True
        data = await insta.download(link, nodownload, no_h264)
        print(json.dumps(data, indent=4, ensure_ascii=False))
        for key, value in insta.cookies.items():
            if cookies.get(key) != value:
                insta.logger.debug(f"{key} cookie has been updated")
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("link", help="Link to post")
    parser.add_argument("--proxy", "-p", help="proxy to use in all the requests")
    parser.add_argument("--no-download", "-n", help="prints just the post and doesn't download the post's media", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-h264", "-d", action="store_true", help="Ignore dash formats and download default h264 format")
    parser.add_argument("--cookies-json", help="Provide cookies in JSON format")
    parser.add_argument("--cookies-netscape", help="Provide cookies in netscape format")
    parser.add_argument("--cookies-headerstring", help="Provide cookies in header-string format")
    args = parser.parse_args()

    handler = logging.StreamHandler()
    if args.verbose:
        handler.setLevel(logging.DEBUG)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
        logging.getLogger(__name__).setLevel(logging.INFO)
    logging.getLogger(__name__).addHandler(handler)
    asyncio.run(async_main(args.link, args.proxy, args.no_download, args.no_h264, [args.cookies_json, args.cookies_netscape, args.cookies_headerstring]))
    
if __name__ == "__main__":
    main()