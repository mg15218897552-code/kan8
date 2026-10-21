# -*- coding: utf-8 -*-
"""xsmt 直播插件
源：https://xsmt.ccwu.cc/xsmt/smt.php（M3U，596 台 / 17 組）
播放经 smt.php?id= 跳转到真实 m3u8，点播时由插件解析跳转"""
import re
import requests
from base.spider import Spider as BaseSpider

M3U_URL = "https://xsmt.ccwu.cc/xsmt/smt.php"
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"


class Spider(BaseSpider):
    def getName(self):
        return "py_xsmt"

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})
        self._groups = None  # {组名: [ {name,url,logo} ]}

    def isVideoFormat(self, url):
        return ".m3u8" in (url or "")

    def manualVideoCheck(self):
        return False

    def _load(self):
        if self._groups is not None:
            return self._groups
        groups = {}
        try:
            r = self.session.get(M3U_URL, timeout=20)
            r.encoding = "utf-8"
            cur = None
            for line in r.text.splitlines():
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    gm = re.search(r'group-title="([^"]*)"', line)
                    g = gm.group(1) if gm else "未分类"
                    lm = re.search(r'tvg-logo="([^"]*)"', line)
                    cur = {
                        "name": line.split(",")[-1].strip(),
                        "group": g,
                        "logo": lm.group(1) if lm else "",
                    }
                elif line and not line.startswith("#") and cur:
                    cur["url"] = line
                    groups.setdefault(cur["group"], []).append(cur)
                    cur = None
        except Exception:
            pass
        self._groups = groups
        return groups

    def homeContent(self, filter):
        groups = self._load()
        return {"class": [{"type_id": g, "type_name": g} for g in groups.keys()]}

    def categoryContent(self, tid, pg, filter, extend):
        groups = self._load()
        videos = [{
            "vod_id": c["url"],
            "vod_name": c["name"],
            "vod_pic": c["logo"],
            "vod_remarks": tid,
        } for c in groups.get(tid, [])]
        return {"list": videos, "page": 1, "pagecount": 1,
                "limit": len(videos), "total": len(videos)}

    def detailContent(self, ids):
        url = ids[0]
        name, logo = url, ""
        for lst in self._load().values():
            for c in lst:
                if c["url"] == url:
                    name, logo = c["name"], c["logo"]
                    break
        return {"list": [{
            "vod_id": url,
            "vod_name": name,
            "vod_pic": logo,
            "vod_play_from": "直播",
            "vod_play_url": f"{name}${url}",
        }]}

    def playerContent(self, flag, id, vipFlags):
        # smt.php?id= 会 302 跳转，先解析出真实地址
        try:
            r = self.session.get(id, timeout=15, allow_redirects=False)
            loc = r.headers.get("Location")
            if loc:
                return {"parse": 0, "url": loc,
                        "header": {"User-Agent": UA}}
        except Exception:
            pass
        # 解析失败就直接返回原地址，让播放器自己跟跳转
        return {"parse": 0, "url": id,
                "header": {"User-Agent": UA}}

    def searchContent(self, key, quick):
        videos = []
        kl = key.lower()
        for lst in self._load().values():
            for c in lst:
                if kl in c["name"].lower():
                    videos.append({
                        "vod_id": c["url"],
                        "vod_name": c["name"],
                        "vod_pic": c["logo"],
                    })
        return {"list": videos}
