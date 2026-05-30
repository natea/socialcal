"""
Selenium-based usability tests for the SocialCal v0 design.

These tests drive a real (headless) browser against the running app to verify the
end-to-end usability of the redesigned UI: the persistent bottom navigation
(Calendar / Discover / Profile), the calendar week strip, onboarding, the event
detail page and the profile page.

They are intentionally defensive: if a browser/driver is not available (e.g. a CI
runner without Chrome), the whole module is skipped rather than failed, so the
normal test gate stays green everywhere. In CI, where Chromium is installed, they
run for real.
"""
import os
import unittest

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone

# --- Optional Selenium import (skip the module cleanly if unavailable) ---------
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
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


@unittest.skipUnless(SELENIUM_AVAILABLE, "selenium is not installed")
class DesignUsabilityTests(StaticLiveServerTestCase):
    """Drive the redesigned UI in a real browser."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = _build_chrome_driver()
        if cls.driver is None:
            raise unittest.SkipTest("No usable Chrome/Chromium browser available")
        cls.driver.set_page_load_timeout(30)

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
        self.driver.get(self.live_server_url + "/")
        self.driver.add_cookie(
            {"name": "sessionid", "value": cookie.value, "path": "/"}
        )

    def _go(self, path):
        self.driver.get(self.live_server_url + path)

    # -- tests -----------------------------------------------------------------
    def test_bottom_nav_present_and_navigates(self):
        """Authenticated users see the Calendar/Discover/Profile bottom nav."""
        self._login()
        self._go(reverse("calendar:index"))
        nav = self.driver.find_elements(By.CSS_SELECTOR, ".sc-bottom-nav .nav-link")
        labels = {el.text.strip() for el in nav}
        self.assertTrue({"Calendar", "Discover", "Profile"}.issubset(labels))

        # Clicking "Discover" should land on the events list.
        for el in nav:
            if el.text.strip() == "Discover":
                el.click()
                break
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
        day_columns = self.driver.find_elements(By.CSS_SELECTOR, ".day-column")
        self.assertEqual(len(day_columns), 7)

    def test_event_detail_has_action_controls(self):
        """The event detail page renders title and the bottom action controls."""
        self._login()
        self._go(reverse("events:detail", args=[self.event.pk]))
        self.assertIn("Usability Test Event", self.driver.page_source)
        controls = self.driver.find_elements(By.CSS_SELECTOR, ".bottom-navigation .nav-button")
        self.assertGreaterEqual(len(controls), 3)

    def test_onboarding_welcome_renders(self):
        """The onboarding welcome screen renders inside a card on the lavender bg."""
        self._go(reverse("onboarding:welcome"))
        containers = self.driver.find_elements(By.CSS_SELECTOR, ".onboarding-container")
        self.assertGreaterEqual(len(containers), 1)

    def test_profile_page_renders(self):
        """The profile page renders for the logged-in user."""
        self._login()
        self._go(reverse("profiles:detail", kwargs={"email": self.user.email}))
        self.assertEqual(self.driver.find_elements(By.CSS_SELECTOR, ".sc-bottom-nav").__len__(), 1)
