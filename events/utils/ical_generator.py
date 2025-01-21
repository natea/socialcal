from icalendar import Calendar, Event as IcalEvent
from datetime import datetime
from typing import List

class ICalGenerator:
    @staticmethod
    def generate_ical(events: List[Event]) -> str:
        cal = Calendar()
        cal.add('prodid', '-//SocialCal Events//example.com//')
        cal.add('version', '2.0')

        for event in events:
            ical_event = IcalEvent()
            ical_event.add('summary', event.title)
            ical_event.add('description', event.description)
            ical_event.add('dtstart', event.start_datetime)
            ical_event.add('dtend', event.end_datetime)
            ical_event.add('location', event.location)
            cal.add_component(ical_event)

        return cal.to_ical().decode('utf-8')