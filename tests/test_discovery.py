import unittest

from publishing.discovery import merge_leads, parse_rss


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item><title>Fundraising submission guidelines</title><link>https://example.org/submit</link><description>Official\n guidelines</description></item>
<item><title>Invalid link</title><link>javascript:alert(1)</link><description>ignore</description></item>
</channel></rss>"""


class DiscoveryTests(unittest.TestCase):
    def test_parser_keeps_only_http_urls_and_marks_unverified(self):
        rows = parse_rss(RSS, "fundraising sites", "2026-11-19T00:00:00Z")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["domain"], "example.org")
        self.assertEqual(rows[0]["verification_status"], "UNVERIFIED_RESEARCH_LEAD")
        self.assertEqual(rows[0]["automation_permission"], "NOT_VERIFIED")

    def test_merge_deduplicates_urls(self):
        old = [{"url": "https://example.org/submit", "last_seen_utc": "old"}]
        new = [{"url": "https://example.org/submit", "last_seen_utc": "new"}]
        merged = merge_leads(old, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["last_seen_utc"], "new")


if __name__ == "__main__":
    unittest.main()
