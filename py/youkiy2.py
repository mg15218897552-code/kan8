# -*- coding: utf-8 -*-
# youkiy2 (https://84d9yt.youkiy2.cyou) - TVBox py 源
# 结构实测（2026-10-27，浏览器只读结构检查，未登录、未付费、未下载视频、未点击播放）：
#   首页直接展示视频列表分区与分类入口，未见登录墙、付费墙、拦截式年龄门；
#   顶部仅有登录/注册入口链接，浏览列表与详情无需登录
#   导航：主页 /、视频 /videos、精选 /recommendation、未审查 /uncensored、
#         审查 /censored、类别总页 /categories
#   分类列表：/videos/<英文slug>（如 /videos/homemade-selfie）
#   列表卡片：同一详情地址的两个链接——封面链接内含 img，另一下方标题文本链接；
#             封面 img src 形如 https://imgos.cctvm.xyz/media/videos/tmb3/<数字ID>/1.jpg
#   详情即播放页：/video/<数字ID>/<连字符slug>，不是按剧集/线路组织的站，
#                 未见多源切换器、分集列表或独立 /play/ 地址；下方仅为推荐列表
#   搜索：/search/videos/<关键词>（直接访问已确认可加载并回显关键词）
#   播放：详情页标题下方直接呈现内置播放器控件，站内直接播放而非跳转独立播放页；
#         可读视图中的 iframe 均为广告位，未见正片外部播放 iframe；
#         本次未提取、未下载任何可播放地址，也未点击播放，故实际可播地址未验证
#   未验证：分类翻页形态、搜索翻页形态、播放页直链字段（playerContent 先扫直链，
#           扫不到交壳内嗅探，不编假直链）
import re
import time
import ssl
import urllib.request
import urllib.parse
import html as html_mod
from http.cookiejar import CookieJar

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):
    def __init__(self):
        self.site_url = "https://84d9yt.youkiy2.cyou"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Redmi K70) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.site_url + "/",
        }
        self._cj = CookieJar()
        self._last = 0.0

    def init(self, extend=""):
        pass

    def getName(self):
        return "youkiy2"

    def _fetch(self, url, timeout=12):
        gap = time.time() - self._last
        if gap < 0.5:
            time.sleep(0.5 - gap)
        self._last = time.time()
        try:
            ctx = ssl._create_unverified_context()
        except Exception:
            ctx = None
        try:
            req = urllib.request.Request(url, headers=self.headers)
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx),
                urllib.request.HTTPCookieProcessor(self._cj))
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                enc = (resp.headers.get("Content-Encoding", "") or "").lower()
                if "gzip" in enc or raw[:2] == b"\x1f\x8b":
                    import gzip
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _abs(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        if path.startswith("//"):
            return "https:" + path
        return urllib.parse.urljoin(self.site_url + "/", path)

    @staticmethod
    def _clean(text):
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", html_mod.unescape(text)).strip()

    def _parse_cards(self, html_data):
        cards, seen = [], set()
        if not html_data:
            return cards
        for m in re.finditer(r'href="(/video/(\d+)/[^"]+)"', html_data, re.I):
            link, vid = m.group(1), m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            title, pic = "", ""
            win = html_data[m.start():m.start() + 3000]
            # 标题：同一详情地址的纯文本标题链接
            for tm in re.finditer(r'<a[^>]*href="/video/%s/[^"]*"[^>]*>(.*?)</a>' % re.escape(vid), win, re.S | re.I):
                t = self._clean(tm.group(1))
                if t:
                    title = t
                    break
            if not title:
                am = re.search(r'<img[^>]+alt="([^"]+)"', win, re.I)
                if am:
                    title = self._clean(am.group(1))
            im = re.search(r'<img[^>]+src="([^"]+)"', win, re.I)
            if im:
                pic = self._abs(im.group(1))
            if not title:
                continue
            cards.append({"vod_id": link, "vod_name": title,
                          "vod_pic": pic, "vod_remarks": ""})
        return cards

    def homeContent(self, filter):
        # 导航 4 类 + /categories 总页实测 30 类（2026-10-27 浏览器滚动到底部确认，
        # 该页无分页、滚动后未新增类别；类别名与路径均按卡片原样）
        cats = [
            {"type_id": "/videos", "type_name": "视频"},
            {"type_id": "/recommendation", "type_name": "精选视频"},
            {"type_id": "/uncensored", "type_name": "未审查"},
            {"type_id": "/censored", "type_name": "审查视频"},
            {"type_id": "/videos/5XSQ members original works", "type_name": "5X社区会员原创作品"},
            {"type_id": "/videos/Pacopacomama", "type_name": "Paco"},
            {"type_id": "/videos/sm", "type_name": "SM性虐"},
            {"type_id": "/videos/Tertiary film", "type_name": "三级片"},
            {"type_id": "/videos/Tokyo Hot", "type_name": "东京热"},
            {"type_id": "/videos/Pantyhose temptation", "type_name": "丝袜诱惑"},
            {"type_id": "/videos/Chinese subtitle", "type_name": "中文字幕"},
            {"type_id": "/videos/Public places and outdoors", "type_name": "公众场所及户外"},
            {"type_id": "/videos/Caribbeancom", "type_name": "加勒比"},
            {"type_id": "/videos/Cumshot", "type_name": "口爆颜射"},
            {"type_id": "/videos/Masturbation", "type_name": "器具自慰"},
            {"type_id": "/videos/homemade-selfie", "type_name": "国产AV"},
            {"type_id": "/videos/10musume", "type_name": "天然素人"},
            {"type_id": "/videos/Lesbian", "type_name": "女同"},
            {"type_id": "/videos/Small format synthesis", "type_name": "小格式综合"},
            {"type_id": "/videos/Sex party", "type_name": "性party"},
            {"type_id": "/videos/Adult Anime", "type_name": "成人动漫"},
            {"type_id": "/videos/chinese-anchor", "type_name": "成人直播&主播福利"},
            {"type_id": "/videos/tanhua-god", "type_name": "探花大神"},
            {"type_id": "/videos/reducing-mosaic", "type_name": "无码破解"},
            {"type_id": "/videos/Japan Uncensored", "type_name": "日本无码"},
            {"type_id": "/videos/Japan Coded", "type_name": "日本有码"},
            {"type_id": "/videos/pondo", "type_name": "本道"},
            {"type_id": "/videos/The Complete Works of Li Zongrui", "type_name": "李宗瑞全集"},
            {"type_id": "/videos/Europe and America", "type_name": "欧美"},
            {"type_id": "/videos/Squirting", "type_name": "潮吹"},
            {"type_id": "/videos/Anal sex", "type_name": "肛交"},
            {"type_id": "/videos/Korean female anchor series", "type_name": "韩国女主播系列"},
            {"type_id": "/videos/Korea General", "type_name": "韩国综合"},
            {"type_id": "/videos/HD", "type_name": "高清"},
        ]
        return {"class": cats, "filters": {}}

    def homeVideoContent(self):
        html_data = self._fetch(self.site_url + "/")
        return {"list": self._parse_cards(html_data)[:28]}

    def _list_url(self, tid, pg):
        base = str(tid or "/videos").strip()
        if not base.startswith("/"):
            base = "/videos/" + base
        base = base if base.endswith("/") else base + "/"
        # 类别路径含空格与大写字母时按 %20 编码后请求
        base = urllib.parse.quote(base, safe="/")
        if pg <= 1:
            return self.site_url + base
        # 翻页形态未实测：先按 /{页}/ 尝试，空结果时需按实测形态修正
        return self.site_url + base + "%d/" % pg

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        html_data = self._fetch(self._list_url(tid, pg))
        cards = self._parse_cards(html_data)
        return {"list": cards, "page": pg,
                "pagecount": pg + 1 if cards else pg,
                "limit": len(cards), "total": 0}

    def detailContent(self, ids):
        vid = str(ids[0]).strip() if ids else ""
        shell = {"vod_id": vid, "vod_name": "", "vod_pic": "",
                 "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""}
        if not vid:
            return {"list": [shell]}
        url = vid if vid.startswith("http") else self._abs(vid)
        html_data = self._fetch(url)
        if not html_data:
            return {"list": [shell]}
        # 标题：详情页标题元素（h1 优先，其次 title 标签）
        tm = re.search(r"<h1[^>]*>(.*?)</h1>", html_data, re.S | re.I)
        if tm:
            shell["vod_name"] = self._clean(tm.group(1))
        if not shell["vod_name"]:
            tm = re.search(r"<title>(.*?)</title>", html_data, re.S | re.I)
            if tm:
                shell["vod_name"] = self._clean(tm.group(1))
        # 封面：详情页内与本视频 ID 对应的 tmb 图片，其次第一个视频封面 img
        pm = None
        vid_num = re.search(r"/video/(\d+)/", vid)
        if vid_num:
            pm = re.search(r'<img[^>]+src="([^"]*tmb3/%s/[^"]*)"' % re.escape(vid_num.group(1)), html_data, re.I)
        if not pm:
            pm = re.search(r'<img[^>]+src="([^"]+)"', html_data, re.I)
        if pm:
            shell["vod_pic"] = self._abs(pm.group(1))
        # 详情即播放页：播放地址即详情地址本身，playerContent 再扫直链
        shell["vod_play_from"] = "在线播放"
        shell["vod_play_url"] = "正片$%s" % vid
        return {"list": [shell]}

    def _scan_media(self, html_data):
        cands = []
        for pat in (r'<source[^>]+src="([^"]+)"', r'<video[^>]+src="([^"]+)"'):
            cands += re.findall(pat, html_data, re.I)
        cands += re.findall(r'"(https?://[^"]+\.(?:m3u8|mp4)[^"]*)"', html_data, re.I)
        cands += re.findall(r"'(https?://[^']+\.(?:m3u8|mp4)[^']*)'", html_data, re.I)
        seen = set()
        for cand in cands:
            cand = cand.strip().replace("\\/", "/")
            low = cand.lower()
            if cand in seen or any(k in low for k in ("preview", "sample", "trailer", "thumb")):
                continue
            seen.add(cand)
            return self._abs(cand)
        return ""

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or "").strip()
        if "$" in raw:
            raw = raw.rsplit("$", 1)[-1].strip()
        header = {"User-Agent": self.headers["User-Agent"],
                  "Referer": self.site_url + "/"}
        if raw.lower().startswith("http") and (".m3u8" in raw.lower() or ".mp4" in raw.lower()):
            return {"parse": 0, "playUrl": "", "url": raw, "header": header}
        url = raw if raw.startswith("http") else self._abs(raw)
        html_data = self._fetch(url)
        play = self._scan_media(html_data)
        if play:
            return {"parse": 0, "playUrl": "", "url": play,
                    "header": {"User-Agent": self.headers["User-Agent"], "Referer": url}}
        # 扫不到直链：详情即播放页，交壳内嗅探内置播放器，不编假直链
        return {"parse": 1, "playUrl": "", "url": url, "header": header}

    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        kw = urllib.parse.quote(str(key))
        if pg <= 1:
            url = "%s/search/videos/%s" % (self.site_url, kw)
        else:
            # 搜索翻页形态未实测，先按 /{页}/ 尝试
            url = "%s/search/videos/%s/%d" % (self.site_url, kw, pg)
        html_data = self._fetch(url)
        cards = self._parse_cards(html_data)
        return {"list": cards, "page": pg,
                "pagecount": pg + 1 if cards else pg,
                "limit": len(cards), "total": 0}

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return u.endswith(".m3u8") or ".m3u8?" in u or u.endswith(".mp4") or ".mp4?" in u

    def localProxy(self, params):
        return [200, "text/plain;charset=utf-8", ""]

    def action(self, action):
        return None

    def liveContent(self):
        return {}


if __name__ == "__main__":
    sp = Spider()
    html_data = ('<a href="/video/118431/test-slug"><img src="https://imgos.cctvm.xyz/media/videos/tmb3/118431/1.jpg" alt="测"></a>'
                 '<a href="/video/118431/test-slug">测</a>')
    print(sp._parse_cards(html_data))
    print(sp._list_url("/videos", 2))
