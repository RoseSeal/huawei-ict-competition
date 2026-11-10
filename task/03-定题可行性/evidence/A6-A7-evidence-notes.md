# A6/A7 取证索引

核查日期：2026-11-09（北京时间）。实际获取网页，不代表浏览器视觉核验或APP实测。原始HTML仅供本地核查，未确认公开再分发权利。

| 文件 | 来源URL | 方式与结果 |
|---|---|---|
| A6-cjmsa-home.html | https://cj.msa.gov.cn/ | web_fetch文本及Python urllib下载原始HTML成功 |
| A6-cjmsa-notices.html | https://cj.msa.gov.cn/xxgk/xxgkml/hxtg/ | 同上；列表包含2026-11-09条目 |
| A6-cjmsa-media.html | https://cj.msa.gov.cn/hdjl/zwxmtjz/ | 同上；明确并列长江e+官方微信和海事通APP |
| A7-cjmsa-disclaimer.html | https://cj.msa.gov.cn/xtwj/mzsm/ | 原始内容为脚本跳转，128字节 |
| A7-cjmsa-disclaimer-body.html | https://cj.msa.gov.cn/xtwj/mzsm/202409/t20240911_3274238.shtml | web_fetch正文与Python urllib原始HTML均成功 |
| A6-A7-fetch-manifest.json | 初次成功下载文件的URL、字节数、SHA-256 | 不包含后续独立下载的新媒体矩阵，完整哈希见A6-A7-sha256.json |

国家海事局 https://www.msa.gov.cn/html/cnmsa/hxaq/aqxx/index.html 的web_fetch成功返回导航：航行警告下有长江海事局，航行通告下另有长江海事局；Python urllib保存时返回HTTP403，因此没有伪造原始HTML文件。报告仅称获取栏目导航，没有宣称已完整核实两个链接的列表同步性。

## 工具限制和失败记录

- web_search返回HTTP401 Authentication Fails，未使用其生成任何事实。
- 浏览器技能已读取，但本会话没有Automation REPL/browser control可调用；未运行APP，未截图。
- 官网站内搜索返回客户端模板，未得到搜索结果；不能以此断言官方功能不存在。
- PowerShell Invoke-WebRequest出现“基础连接已经关闭: 接收时发生错误”；curl出现SEC_E_NO_CREDENTIALS。后改用已存在的Python urllib取得HTML，没有安装任何软件。
- 未收录第三方应用下载站版本号，避免误将旧包/第三方标签当作当前官方版本。
- 官网首页源代码中出现“长江e+官方微信”的HTML注释块；未将注释块视为用户可见入口，改为核验真实政务新媒体矩阵页面。

## 手机截图缺口

截图数量：0。版本页、通告列表、订阅设置、提醒记录、计划航线匹配结果均待真实设备补证。原始HTML不冒充截图，公众号矩阵不证明同名独立APP存在或不存在。

## 原始文件完整性

A6-A7-sha256.json记录本次保存HTML及伴航报道核验摘录的文件名、字节数和SHA-256。新增A6-伴航报道核验摘录.md的来源、实际HTTP结果和文件哈希另见A6-A7-supplement-manifest.json。此清单只证明本地文件在计算时的内容，不是来源站数字签名。
