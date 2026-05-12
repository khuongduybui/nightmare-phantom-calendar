# Phantom Calendar — MVP 2 Build Plan
*Mac desktop app. Self-contained. Build this without referring to anything else.*

---

## What MVP 2 Is

A Mac menu bar app that:
1. Runs silently in the background on startup
2. At 7pm every weekday, reads your MSI Work calendar and Personal Google Calendar
3. Computes the correct alarm time for tomorrow's first meeting
4. Shows a confirmation popup — you approve or adjust
5. Writes the alarm event to your Personal Google Calendar
6. Sleep as Android reads it overnight

Same logic as MVP 1 (Claude doing it manually), automated.

---

## Tech Stack

| Library | Purpose | Install |
|---|---|---|
| `rumps` | Mac menu bar app framework | `pip install rumps` |
| `google-api-python-client` | Google Calendar + Drive API | `pip install google-api-python-client` |
| `google-auth-oauthlib` | Google OAuth flow | `pip install google-auth-oauthlib` |
| `google-auth-httplib2` | HTTP transport for Google auth | `pip install google-auth-httplib2` |
| `APScheduler` | Schedule 7pm daily job | `pip install apscheduler` |
| `tkinter` | Confirmation popup window | Included in Python stdlib |
| `PyInstaller` | Package as `.app` bundle | `pip install pyinstaller` |

Python version: **3.11+**

---

## Project Structure

```
phantom_calendar/
├── main.py                  # Entry point — starts menu bar app + scheduler
├── app.py                   # rumps menu bar app class
├── scheduler.py             # APScheduler — triggers 7pm job
├── calendar_reader.py       # Reads MSI + Personal Google Calendar
├── calendar_writer.py       # Writes alarm event to Personal calendar
├── drive_config.py          # Reads/writes config from Google Drive
├── compute.py               # Alarm time computation logic
├── popup.py                 # tkinter confirmation window
├── auth.py                  # Google OAuth flow + token management
├── credentials.json         # Google Cloud OAuth client credentials (never commit)
├── token.json               # Stored OAuth token (auto-generated, never commit)
├── .gitignore               # Exclude credentials.json, token.json
└── requirements.txt         # All pip dependencies
```

---

## Step 1 — Google Cloud Console Setup

Do this once before writing any code.

### 1.1 Create a project
1. Go to https://console.cloud.google.com
2. Click "New Project" → name it "Phantom Calendar" → Create

### 1.2 Enable APIs
1. Go to "APIs & Services" → "Enable APIs and Services"
2. Enable **Google Calendar API**
3. Enable **Google Drive API**

### 1.3 Create OAuth credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**
4. Name: "Phantom Calendar Desktop"
5. Download the JSON → save as `credentials.json` in your project root

### 1.4 Configure OAuth consent screen
1. Go to "APIs & Services" → "OAuth consent screen"
2. User type: **External**
3. App name: "Phantom Calendar"
4. Add your Gmail as a test user
5. Scopes to add:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/drive.file`

### 1.5 Calendar IDs
- **Personal calendar:** `duykbui1989@gmail.com`
- **MSI Work calendar:** `duy.bui@motorolasolutions.com`
- **Personal calendar (write target):** `duykbui1989@gmail.com`

---

## Step 2 — Auth Module

**`auth.py`** — handles OAuth flow and token refresh.

```python
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file',
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds


def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())


def get_drive_service():
    return build('drive', 'v3', credentials=get_credentials())
```

**First run:** the OAuth flow opens a browser window for the user to sign in. After that, `token.json` is stored and auto-refreshed silently.

---

## Step 3 — Config Module

**`drive_config.py`** — reads and writes config from Google Drive.

```python
import io
from auth import get_drive_service

CONFIG_FILE_ID = '1nZ8-G5vwi9O8r4hAmbBS9zl55cVVjXz6'


def read_config() -> str:
    """Read raw markdown config text from Google Drive."""
    service = get_drive_service()
    request = service.files().get_media(fileId=CONFIG_FILE_ID)
    content = request.execute()
    if isinstance(content, bytes):
        return content.decode('utf-8')
    return content


def write_config(new_content: str):
    """Write updated config back to Google Drive."""
    service = get_drive_service()
    media = io.BytesIO(new_content.encode('utf-8'))
    service.files().update(
        fileId=CONFIG_FILE_ID,
        media_body=build_media(media)
    ).execute()


def build_media(stream):
    from googleapiclient.http import MediaIoBaseUpload
    return MediaIoBaseUpload(stream, mimetype='text/plain')


def parse_config(raw: str) -> dict:
    """
    Parse the markdown config into a structured dict.
    Returns:
    {
        'personal_calendar_id': str,
        'msi_calendar_id': str,
        'baseline_event_id': str,
        'recurring_meetings': [
            {'name': str, 'start': 'HH:MM', 'end': 'HH:MM', 'days': [str], 'prep_minutes': int}
        ],
        'default_prep_minutes': 30,
        'locations': {name: travel_minutes},
        'client_overrides': {client: prep_minutes},
    }
    """
    config = {
        'personal_calendar_id': 'duykbui1989@gmail.com',
        'msi_calendar_id': 'duy.bui@motorolasolutions.com',
        'baseline_event_id': 'l13abvd0p0vkphit24u6bkhuf8',
        'recurring_meetings': [],
        'default_prep_minutes': 30,
        'locations': {},
        'client_overrides': {},
    }

    # Parse recurring meetings table
    # Lines like: | AERSS Standup | 9:30–9:45 AM | Mon–Fri | 5 min | ... |
    import re
    for line in raw.splitlines():
        if '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) < 4:
            continue
        name, time_range, days_str, prep_str = parts[0], parts[1], parts[2], parts[3]
        # Skip header rows
        if name in ('Logical name', '---', '') or '---' in name:
            continue
        # Parse time range e.g. "9:30–9:45 AM"
        time_match = re.match(r'(\d+:\d+)[–-](\d+:\d+)\s*(AM|PM)?', time_range)
        if not time_match:
            continue
        start_time = time_match.group(1)
        end_time = time_match.group(2)
        am_pm = time_match.group(3) or 'AM'
        # Parse prep time e.g. "5 min"
        prep_match = re.search(r'(\d+)\s*min', prep_str)
        if not prep_match:
            continue
        prep_minutes = int(prep_match.group(1))
        config['recurring_meetings'].append({
            'name': name,
            'start': f"{start_time} {am_pm}",
            'end': f"{end_time} {am_pm}",
            'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],  # default weekdays
            'prep_minutes': prep_minutes,
        })

    return config
```

---

## Step 4 — Calendar Reader

**`calendar_reader.py`** — reads both calendars for tomorrow.

```python
from datetime import datetime, timedelta, timezone
import pytz
from auth import get_calendar_service

LOCAL_TZ = pytz.timezone('America/New_York')  # adjust to your timezone

PERSONAL_CALENDAR_ID = 'duykbui1989@gmail.com'
MSI_CALENDAR_ID = 'duy.bui@motorolasolutions.com'


def get_tomorrow_range():
    """Returns (start, end) as RFC3339 strings for tomorrow in local time."""
    now = datetime.now(LOCAL_TZ)
    tomorrow = now.date() + timedelta(days=1)
    start = LOCAL_TZ.localize(datetime.combine(tomorrow, datetime.min.time()))
    end = LOCAL_TZ.localize(datetime.combine(tomorrow, datetime.max.time()))
    return start.isoformat(), end.isoformat()


def get_events(calendar_id: str) -> list:
    """Get all events for tomorrow from a given calendar."""
    service = get_calendar_service()
    start, end = get_tomorrow_range()
    result = service.events().list(
        calendarId=calendar_id,
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime',
    ).execute()
    return result.get('items', [])


def get_msi_time_blocks() -> list:
    """
    Returns list of time blocks from MSI calendar.
    Each block: {'start': datetime, 'end': datetime}
    Titles are not visible (freeBusyReader access).
    """
    events = get_events(MSI_CALENDAR_ID)
    blocks = []
    for event in events:
        start = event.get('start', {}).get('dateTime')
        end = event.get('end', {}).get('dateTime')
        if start and end:
            blocks.append({
                'start': datetime.fromisoformat(start),
                'end': datetime.fromisoformat(end),
            })
    return sorted(blocks, key=lambda x: x['start'])


def get_personal_events() -> list:
    """Returns personal calendar events for tomorrow with title and time."""
    events = get_events(PERSONAL_CALENDAR_ID)
    result = []
    for event in events:
        start = event.get('start', {}).get('dateTime')
        end = event.get('end', {}).get('dateTime')
        summary = event.get('summary', 'Untitled')
        if start:
            result.append({
                'title': summary,
                'start': datetime.fromisoformat(start),
                'end': datetime.fromisoformat(end) if end else None,
            })
    return sorted(result, key=lambda x: x['start'])
```

---

## Step 5 — Compute Module

**`compute.py`** — matches time blocks to meetings and computes alarm time.

```python
from datetime import datetime, timedelta


def match_block_to_meeting(block: dict, recurring_meetings: list) -> dict | None:
    """
    Try to match an MSI time block to a known recurring meeting.
    Match is based on start time (within 5 minute tolerance).
    Returns the matched meeting config or None.
    """
    import re
    block_start = block['start']
    for meeting in recurring_meetings:
        # Parse meeting start time e.g. "9:30 AM"
        t = datetime.strptime(meeting['start'], '%I:%M %p') if ':' in meeting['start'] else None
        if not t:
            # Try 24h format
            try:
                t = datetime.strptime(meeting['start'], '%H:%M')
            except:
                continue
        meeting_start = block_start.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        delta = abs((block_start - meeting_start).total_seconds())
        if delta <= 300:  # within 5 minutes
            return meeting
    return None


def compute_alarm(
    msi_blocks: list,
    personal_events: list,
    config: dict,
) -> dict:
    """
    Find the first meeting of the day and compute alarm time.
    Returns:
    {
        'first_meeting_name': str,
        'first_meeting_time': datetime,
        'prep_minutes': int,
        'alarm_time': datetime,
        'is_baseline': bool,  # True if alarm matches existing 9:25 standup
        'all_meetings': list,  # summary of all meetings for display
        'unknown_blocks': list,  # MSI blocks we couldn't identify
    }
    """
    candidates = []
    unknown_blocks = []

    # Process MSI blocks
    for block in msi_blocks:
        matched = match_block_to_meeting(block, config['recurring_meetings'])
        if matched:
            candidates.append({
                'name': matched['name'],
                'time': block['start'],
                'prep_minutes': matched['prep_minutes'],
                'source': 'msi_known',
            })
        else:
            unknown_blocks.append(block)
            candidates.append({
                'name': 'Unknown MSI meeting',
                'time': block['start'],
                'prep_minutes': config['default_prep_minutes'],
                'source': 'msi_unknown',
            })

    # Process personal events (skip existing alarm events)
    for event in personal_events:
        if 'Alarm' in event['title'] or 'Standup Alarm' in event['title']:
            continue
        candidates.append({
            'name': event['title'],
            'time': event['start'],
            'prep_minutes': 10,  # default for personal events
            'source': 'personal',
        })

    if not candidates:
        return {
            'first_meeting_name': None,
            'first_meeting_time': None,
            'prep_minutes': 0,
            'alarm_time': None,
            'is_baseline': True,
            'all_meetings': [],
            'unknown_blocks': unknown_blocks,
        }

    # Sort by time, pick first
    candidates.sort(key=lambda x: x['time'])
    first = candidates[0]
    alarm_time = first['time'] - timedelta(minutes=first['prep_minutes'])

    # Check if alarm matches baseline (9:25 AM = AERSS standup at 9:30 - 5 min)
    is_baseline = (
        first['name'] == 'AERSS Standup'
        and alarm_time.hour == 9
        and alarm_time.minute == 25
    )

    return {
        'first_meeting_name': first['name'],
        'first_meeting_time': first['time'],
        'prep_minutes': first['prep_minutes'],
        'alarm_time': alarm_time,
        'is_baseline': is_baseline,
        'all_meetings': candidates,
        'unknown_blocks': unknown_blocks,
    }
```

---

## Step 6 — Calendar Writer

**`calendar_writer.py`** — writes the alarm event to Personal calendar.

```python
from datetime import timedelta
from auth import get_calendar_service

PERSONAL_CALENDAR_ID = 'duykbui1989@gmail.com'
BASELINE_EVENT_ID = 'l13abvd0p0vkphit24u6bkhuf8'


def write_alarm_event(alarm_time, meeting_name: str) -> str:
    """
    Write alarm event to Personal calendar.
    Returns the created event ID.
    """
    service = get_calendar_service()
    event = {
        'summary': f'⏰ Alarm — {meeting_name}',
        'description': f'Auto-generated by Phantom Calendar. Prep for: {meeting_name}',
        'start': {
            'dateTime': alarm_time.isoformat(),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': (alarm_time + timedelta(minutes=5)).isoformat(),
            'timeZone': 'America/New_York',
        },
        'reminders': {'useDefault': False, 'overrides': []},
    }
    created = service.events().insert(
        calendarId=PERSONAL_CALENDAR_ID,
        body=event,
    ).execute()
    return created['id']


def delete_alarm_event(event_id: str):
    """Delete a previously written alarm event."""
    service = get_calendar_service()
    service.events().delete(
        calendarId=PERSONAL_CALENDAR_ID,
        eventId=event_id,
    ).execute()


def get_existing_alarm_for_tomorrow(tomorrow_date) -> dict | None:
    """
    Check if there's already a non-baseline alarm event for tomorrow.
    Returns the event dict or None.
    """
    service = get_calendar_service()
    from datetime import datetime
    import pytz
    LOCAL_TZ = pytz.timezone('America/New_York')
    start = LOCAL_TZ.localize(datetime.combine(tomorrow_date, datetime.min.time()))
    end = LOCAL_TZ.localize(datetime.combine(tomorrow_date, datetime.max.time()))
    result = service.events().list(
        calendarId=PERSONAL_CALENDAR_ID,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        q='Alarm —',  # search for events written by this system
    ).execute()
    events = result.get('items', [])
    # Exclude the baseline recurring event
    for event in events:
        if event.get('id') != BASELINE_EVENT_ID:
            return event
    return None
```

---

## Step 7 — Confirmation Popup

**`popup.py`** — tkinter window shown at 7pm for user confirmation.

```python
import tkinter as tk
from tkinter import ttk
from datetime import datetime


class ConfirmationPopup:
    def __init__(self, result: dict):
        self.result = result
        self.confirmed = False
        self.user_alarm_override = None  # if user manually changes alarm time

    def show(self) -> dict:
        """
        Show confirmation window. Returns:
        {'confirmed': bool, 'alarm_time': datetime or None, 'skip': bool}
        """
        self.root = tk.Tk()
        self.root.title('Phantom Calendar — Nightly Sync')
        self.root.geometry('420x320')
        self.root.resizable(False, False)
        self.root.lift()
        self.root.attributes('-topmost', True)

        # Header
        tk.Label(
            self.root,
            text='Tomorrow\'s Alarm',
            font=('SF Pro Display', 16, 'bold'),
            pady=12
        ).pack()

        # Meeting info
        frame = tk.Frame(self.root, padx=20)
        frame.pack(fill='x')

        if self.result['first_meeting_name']:
            tk.Label(
                frame,
                text=f"First meeting: {self.result['first_meeting_name']}",
                font=('SF Pro Text', 12),
                anchor='w'
            ).pack(fill='x', pady=2)
            tk.Label(
                frame,
                text=f"Meeting time: {self.result['first_meeting_time'].strftime('%I:%M %p')}",
                font=('SF Pro Text', 12),
                anchor='w'
            ).pack(fill='x', pady=2)
            tk.Label(
                frame,
                text=f"Prep time: {self.result['prep_minutes']} min",
                font=('SF Pro Text', 12),
                anchor='w',
                fg='gray'
            ).pack(fill='x', pady=2)

            # Alarm time (editable)
            alarm_frame = tk.Frame(frame)
            alarm_frame.pack(fill='x', pady=8)
            tk.Label(
                alarm_frame,
                text='Alarm time:',
                font=('SF Pro Text', 13, 'bold'),
            ).pack(side='left')
            self.alarm_var = tk.StringVar(
                value=self.result['alarm_time'].strftime('%I:%M %p')
            )
            alarm_entry = tk.Entry(
                alarm_frame,
                textvariable=self.alarm_var,
                font=('SF Pro Text', 13, 'bold'),
                width=10,
                justify='center'
            )
            alarm_entry.pack(side='left', padx=8)

            # Unknown blocks warning
            if self.result['unknown_blocks']:
                tk.Label(
                    frame,
                    text=f"⚠️ {len(self.result['unknown_blocks'])} unknown MSI meeting(s) — defaulted to 30 min prep",
                    font=('SF Pro Text', 11),
                    fg='orange',
                    anchor='w'
                ).pack(fill='x', pady=4)

            if self.result['is_baseline']:
                tk.Label(
                    frame,
                    text='✓ Matches baseline — no new event needed',
                    font=('SF Pro Text', 11),
                    fg='green',
                    anchor='w'
                ).pack(fill='x', pady=4)
        else:
            tk.Label(
                frame,
                text='No meetings found for tomorrow.',
                font=('SF Pro Text', 12),
                fg='gray'
            ).pack(fill='x', pady=8)

        # Buttons
        btn_frame = tk.Frame(self.root, pady=16)
        btn_frame.pack()

        if not self.result['is_baseline'] and self.result['alarm_time']:
            tk.Button(
                btn_frame,
                text='Write to Calendar',
                command=self._confirm,
                bg='#007AFF',
                fg='white',
                font=('SF Pro Text', 13),
                padx=16, pady=6,
                relief='flat',
                cursor='hand2'
            ).pack(side='left', padx=8)

        tk.Button(
            btn_frame,
            text='Skip',
            command=self._skip,
            font=('SF Pro Text', 13),
            padx=16, pady=6,
            relief='flat',
            cursor='hand2'
        ).pack(side='left', padx=8)

        self.root.mainloop()

        return {
            'confirmed': self.confirmed,
            'alarm_time': self._parse_alarm_override() if self.confirmed else None,
            'skip': not self.confirmed,
        }

    def _confirm(self):
        self.confirmed = True
        self.root.destroy()

    def _skip(self):
        self.confirmed = False
        self.root.destroy()

    def _parse_alarm_override(self):
        """Parse the alarm time entry field — user may have edited it."""
        try:
            from datetime import datetime
            import pytz
            LOCAL_TZ = pytz.timezone('America/New_York')
            t = datetime.strptime(self.alarm_var.get().strip(), '%I:%M %p')
            base = self.result['alarm_time']
            result = base.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            return LOCAL_TZ.localize(result.replace(tzinfo=None))
        except:
            return self.result['alarm_time']
```

---

## Step 8 — Sync Job

**`sync_job.py`** — the function that runs at 7pm.

```python
from datetime import datetime, timedelta
import pytz
from calendar_reader import get_msi_time_blocks, get_personal_events
from calendar_writer import write_alarm_event, get_existing_alarm_for_tomorrow, delete_alarm_event
from drive_config import read_config, parse_config
from compute import compute_alarm
from popup import ConfirmationPopup

LOCAL_TZ = pytz.timezone('America/New_York')


def run_nightly_sync():
    """Main sync job — called at 7pm every weekday."""
    print(f"[{datetime.now()}] Running nightly sync...")

    # Load config
    raw_config = read_config()
    config = parse_config(raw_config)

    # Read calendars
    msi_blocks = get_msi_time_blocks()
    personal_events = get_personal_events()

    # Compute alarm
    result = compute_alarm(msi_blocks, personal_events, config)

    # Show confirmation popup
    popup = ConfirmationPopup(result)
    response = popup.show()

    if response['skip']:
        print("User skipped — no changes made.")
        return

    if result['is_baseline']:
        print("Alarm matches baseline 9:25 standup — no new event needed.")
        return

    # Delete any existing non-baseline alarm for tomorrow
    tomorrow = (datetime.now(LOCAL_TZ) + timedelta(days=1)).date()
    existing = get_existing_alarm_for_tomorrow(tomorrow)
    if existing:
        delete_alarm_event(existing['id'])
        print(f"Deleted existing alarm event: {existing.get('summary')}")

    # Write new alarm event
    alarm_time = response['alarm_time']
    event_id = write_alarm_event(alarm_time, result['first_meeting_name'])
    print(f"Written alarm at {alarm_time.strftime('%I:%M %p')} → event ID: {event_id}")
```

---

## Step 9 — Scheduler

**`scheduler.py`** — runs the sync job at 7pm every weekday.

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sync_job import run_nightly_sync


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_nightly_sync,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=19,
            minute=0,
            timezone='America/New_York'
        ),
        id='nightly_sync',
        replace_existing=True,
    )
    scheduler.start()
    print("Scheduler started — nightly sync at 7:00 PM Mon–Fri")
    return scheduler
```

---

## Step 10 — Menu Bar App

**`app.py`** — rumps menu bar app.

```python
import rumps
from scheduler import start_scheduler
from sync_job import run_nightly_sync


class PhantomCalendarApp(rumps.App):
    def __init__(self):
        super().__init__(
            name='Phantom Calendar',
            icon=None,  # use default or set path to .icns file
            title='⏰',  # shown in menu bar
            quit_button='Quit'
        )
        self.scheduler = start_scheduler()
        self.menu = [
            rumps.MenuItem('Run now', callback=self.run_now),
            rumps.MenuItem('Status: Running', callback=None),
            None,  # separator
        ]

    @rumps.clicked('Run now')
    def run_now(self, _):
        run_nightly_sync()

    def __del__(self):
        if self.scheduler:
            self.scheduler.shutdown()


def main():
    PhantomCalendarApp().run()
```

---

## Step 11 — Entry Point

**`main.py`**

```python
from auth import get_credentials
from app import main

if __name__ == '__main__':
    # Trigger OAuth flow on first run if no token exists
    get_credentials()
    main()
```

---

## Step 12 — Requirements File

**`requirements.txt`**

```
google-api-python-client==2.126.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
APScheduler==3.10.4
rumps==0.4.0
pytz==2024.1
pyinstaller==6.6.0
```

Install all: `pip install -r requirements.txt`

---

## Step 13 — .gitignore

```
credentials.json
token.json
__pycache__/
*.pyc
dist/
build/
*.spec
```

---

## Step 14 — First Run

```bash
# 1. Clone/create project folder
cd phantom_calendar

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place credentials.json in project root (downloaded from Google Cloud Console)

# 4. Run
python main.py
# → Browser opens for Google sign-in (first time only)
# → Menu bar icon ⏰ appears
# → App runs, scheduler starts
```

---

## Step 15 — Package as Mac App

```bash
# Build .app bundle
pyinstaller \
  --onefile \
  --windowed \
  --name "PhantomCalendar" \
  --add-data "credentials.json:." \
  main.py

# Output: dist/PhantomCalendar.app
```

Move `dist/PhantomCalendar.app` to `/Applications`.

**Add to Login Items** (runs on Mac startup):
1. System Settings → General → Login Items
2. Click `+` → select `PhantomCalendar.app`

---

## Known Limitations (same as MVP 1)

- MSI calendar is freeBusyReader only — meeting titles not visible, matched by time block
- Unknown MSI blocks default to 30 min prep time — user sees a warning in popup
- Mid-cycle changes (new meeting after 7pm) require manually clicking "Run now" from menu bar
- Travel time is config-based, not live Maps API

---

## Future Improvements (MVP 3+)

- Replace tkinter popup with native SwiftUI notification (cleaner Mac UX)
- Google Maps API for live travel time
- Watch for calendar change events and auto-recompute
- Config editor UI inside the app (instead of editing Google Drive directly)
- Support for multiple time zones
