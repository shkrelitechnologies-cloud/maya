import unittest

from publishing.discovery import RELEVANT_TERMS, SEARCH_ENGINES, merge_leads, parse_rss


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item><title>Fundraising submission guidelines</title><link>https://example.org/submit</link><description>Official\n guidelines</description></item>
<item><title>India facts</title><link>https://example.org/india</link><description>Country facts only</description></item>\n<item><title>Invalid link</title><link>javascript:alert(1)</link><description>fundraising</description></item>
</channel></rss>"""


class DiscoveryTests(unittest.TestCase):
    def test_parser_keeps_only_http_urls_and_marks_unverified(self):
        rows = parse_rss(RSS, "fundraising sites", "2026-11-19T00:00:00Z")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["domain"], "example.org")
        self.assertEqual(rows[0]["verification_status"], "UNVERIFIED_RESEARCH_LEAD")
        self.assertEqual(rows[0]["automation_permission"], "NOT_VERIFIED")

    def test_crypto_image_search_engines_are_configured(self):
        self.assertIn("mojeek", SEARCH_ENGINES)
        self.assertIn("startpage", SEARCH_ENGINES)
        self.assertIn("crypto donation", RELEVANT_TERMS)
        self.assertIn("bitcoin", RELEVANT_TERMS)

    def test_merge_deduplicates_urls(self):
        old = [{"url": "https://example.org/submit", "title": "fundraising site", "last_seen_utc": "old"}]
        new = [{"url": "https://example.org/submit", "title": "fundraising site", "last_seen_utc": "new"}]
        merged = merge_leads(old, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["last_seen_utc"], "new")


if __name__ == "__main__":
    unittest.main()
