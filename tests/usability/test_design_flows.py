"""
Selenium-based usability tests for the SocialCal v0 design.

These tests drive a real (headless) browser against the running app to verify the
end-to-end usability of the redesigned UI: the persistent bottom navigation
(Calendar / Discover / Profile), the calendar week strip, onboarding, the event
detail page and the profile page.

They are intentionally defensive:

* If a browser/driver is not available (e.g. a CI runner without Chrome), the
  whole module is skipped rather than failed, so the normal test gate stays
  green everywhere. In CI, where Chromium is installed, they run for real.
* All interactions use explicit ``WebDriverWait`` conditions instead of bare
  reads, so they are robust against navigation/render races under load.
"""
import os
import unittest

import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone

# --- Optional Selenium import (skip the module cleanly if unavailable) ---------
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when selenium missing
    SELENIUM_AVAILABLE = False


def _build_chrome_driver():
    """Return a headless Chrome/Chromium driver, or None if one can't start."""
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=420,900")  # mobile-ish viewport
    # Return as soon as the DOM is ready instead of blocking on every
    # subresource (e.g. the external Spotify SDK script loaded in <head>),
    # which keeps the tests fast and robust against slow third-party loads.
    options.page_load_strategy = "eager"

    # Honour an explicitly provided Chrome/Chromium binary (e.g. the one
    # Playwright installs in CI via `playwright install chromium`).
    binary = os.environ.get("CHROME_BIN") or os.environ.get("CHROMIUM_BIN")
    if binary:
        options.binary_location = binary

    # Try Selenium Manager / system chromedriver first, then webdriver-manager.
    try:
        return webdriver.Chrome(options=options)
    except Exception:
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            return webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
            )
        except Exception:
            return None


@pytest.mark.flaky(reruns=2, reruns_delay=3)
@unittest.skipUnless(SELENIUM_AVAILABLE, "selenium is not installed")
class DesignUsabilityTests(StaticLiveServerTestCase):
    """Drive the redesigned UI in a real browser.

    Marked ``flaky`` (via pytest-rerunfailures) so a transient slow page load on
    a loaded CI runner is retried rather than failing the gate; the assertions
    themselves are deterministic.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = _build_chrome_driver()
        if cls.driver is None:
            raise unittest.SkipTest("No usable Chrome/Chromium browser available")
        cls.driver.set_page_load_timeout(45)
        cls.wait = WebDriverWait(cls.driver, 30)

    @classmethod
    def tearDownClass(cls):
        driver = getattr(cls, "driver", None)
        if driver is not None:
            driver.quit()
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="usabilityuser",
            email="usability@example.com",
            password="usabilitypass123",
        )
        from events.models import Event
        now = timezone.now()
        self.event = Event.objects.create(
            user=self.user,
            title="Usability Test Event",
            description="An event used by the usability suite.",
            start_time=now,
            end_time=now + timezone.timedelta(hours=2),
            venue_name="Test Hall",
        )

    # -- helpers ---------------------------------------------------------------
    def _login(self):
        """Log in by seeding the session cookie (faster than the login form)."""
        self.client.force_login(self.user)
        cookie = self.client.cookies["sessionid"]
        # Must be on the domain before a cookie can be added.
        self.driver.get(self.live_server_url + "/accounts/login/")
        self.driver.add_cookie(
            {"name": "sessionid", "value": cookie.value, "path": "/"}
        )

    def _go(self, path):
        self.driver.get(self.live_server_url + path)

    def _bottom_nav_links(self):
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".sc-bottom-nav"))
        )
        return self.driver.find_elements(By.CSS_SELECTOR, ".sc-bottom-nav .nav-link")

    # -- tests -----------------------------------------------------------------
    def test_bottom_nav_present_and_navigates(self):
        """Authenticated users see the Calendar/Discover/Profile bottom nav."""
        self._login()
        self._go(reverse("calendar:index"))
        nav = self._bottom_nav_links()
        labels = {el.text.strip() for el in nav}
        self.assertTrue(
            {"Calendar", "Discover", "Profile"}.issubset(labels),
            f"bottom nav labels were {labels}",
        )

        # Clicking "Discover" should land on the events list.
        for el in nav:
            if el.text.strip() == "Discover":
                el.click()
                break
        self.wait.until(EC.url_contains("/events"))
        self.assertIn("/events", self.driver.current_url)

    def test_calendar_week_strip_renders(self):
        """The calendar week view shows a 7-day strip of day columns."""
        self._login()
        today = timezone.localtime()
        self._go(
            reverse(
                "calendar:week",
                kwargs={"year": today.year, "month": today.month, "day": today.day},
            )
        )
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".day-column"))
        )
        day_columns = self.driver.find_elements(By.CSS_SELECTOR, ".day-column")
        self.assertEqual(len(day_columns), 7)

    def test_event_detail_has_action_controls(self):
        """The event detail page renders title and the bottom action controls."""
        self._login()
        self._go(reverse("events:detail", args=[self.event.pk]))
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bottom-navigation"))
        )
        self.assertIn("Usability Test Event", self.driver.page_source)
        controls = self.driver.find_elements(
            By.CSS_SELECTOR, ".bottom-navigation .nav-button"
        )
        self.assertGreaterEqual(len(controls), 3)

    def test_onboarding_welcome_renders(self):
        """The onboarding welcome screen renders inside a card on the lavender bg."""
        self._go(reverse("onboarding:welcome"))
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".onboarding-container"))
        )
        containers = self.driver.find_elements(
            By.CSS_SELECTOR, ".onboarding-container"
        )
        self.assertGreaterEqual(len(containers), 1)

    def test_profile_page_renders(self):
        """The profile page renders with the bottom nav for the logged-in user."""
        self._login()
        self._go(reverse("profiles:detail", kwargs={"email": self.user.email}))
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".sc-bottom-nav"))
        )
        self.assertEqual(
            len(self.driver.find_elements(By.CSS_SELECTOR, ".sc-bottom-nav")), 1
        )
