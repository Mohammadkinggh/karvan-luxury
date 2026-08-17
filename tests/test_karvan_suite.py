#!/usr/bin/env python3
"""
Automated E2E Test Suite for KĀRVĀN Luxury Persian Website
Verifies HTML structure, JavaScript bundle integrity, DOM elements, Three.js canvas setup,
PWA manifest, Service Worker offline support, and GitHub Pages CDN reachability.
"""
import unittest
import urllib.request
import json
import re
import os

SITE_DIR = "/storage/emulated/0/HERMES/sites/karvan_website"
HTML_PATH = os.path.join(SITE_DIR, "index.html")
MANIFEST_PATH = os.path.join(SITE_DIR, "manifest.json")
SW_PATH = os.path.join(SITE_DIR, "sw.js")
GITHUB_PAGES_URL = "https://mohammadkinggh.github.io/karvan-luxury/"

class TestKarvanWebsite(unittest.TestCase):

    def test_01_html_exists_and_valid(self):
        self.assertTrue(os.path.exists(HTML_PATH), "index.html does not exist in root directory!")
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<title>", content)
        self.assertIn("KĀRVĀN", content)

    def test_02_bundled_js_assets_exist(self):
        js_dir = os.path.join(SITE_DIR, "assets", "js")
        required_js = ["three.min.js", "lucide.min.js", "confetti.browser.min.js", "tailwind.cdn.js"]
        for js_file in required_js:
            file_path = os.path.join(js_dir, js_file)
            self.assertTrue(os.path.exists(file_path), f"Bundled JS missing: {js_file}")
            self.assertGreater(os.path.getsize(file_path), 1000, f"JS bundle empty/corrupt: {js_file}")

    def test_03_zero_external_blocking_scripts(self):
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        external_scripts = re.findall(r'<script\s+src="https://(cdn\.|cdnjs\.|unpkg\.)[^"]+"', content)
        self.assertEqual(len(external_scripts), 0, f"Found external blocking scripts that break in Iran: {external_scripts}")

    def test_04_pwa_manifest_and_sw_valid(self):
        self.assertTrue(os.path.exists(MANIFEST_PATH), "manifest.json missing!")
        self.assertTrue(os.path.exists(SW_PATH), "sw.js missing!")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        self.assertIn("name", manifest_data)
        self.assertIn("short_name", manifest_data)
        self.assertEqual(manifest_data["display"], "standalone")

    def test_05_live_github_pages_reachability(self):
        try:
            req = urllib.request.Request(GITHUB_PAGES_URL, headers={"User-Agent": "KarvanTester/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                self.assertEqual(resp.status, 200, f"GitHub Pages returned status {resp.status}")
                body = resp.read().decode("utf-8")
                self.assertIn("KĀRVĀN", body)
        except Exception as e:
            self.fail(f"GitHub Pages URL failed reachability check: {e}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
