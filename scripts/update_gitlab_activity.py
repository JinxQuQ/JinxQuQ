"""Render only daily event counts using the local glab login; no credentials exported."""
import collections
import datetime as dt
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HOST = 'git.17zjh.com'
USER = 'lihui'
ZONE = ZoneInfo('Asia/Shanghai')


def api(endpoint):
    result = subprocess.run(['glab', 'api', '--hostname', HOST, endpoint],
                            check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def main():
    today = dt.datetime.now(ZONE).date()
    start = today - dt.timedelta(days=364)
    identity = api('user')
    if identity['username'] != USER:
        raise RuntimeError('The local GitLab account does not match the profile.')
    counts = collections.Counter()
    seen = set()
    for page in range(1, 501):
        events = api(f'users/{identity["id"]}/events?after={start - dt.timedelta(days=1)}&before={today + dt.timedelta(days=1)}&per_page=100&page={page}')
        if not isinstance(events, list):
            raise RuntimeError('Unexpected events response')
        for event in events:
            if event['author_id'] != identity['id'] or event['id'] in seen:
                raise RuntimeError('Unexpected author or duplicate pagination')
            seen.add(event['id'])
            day = dt.datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')).astimezone(ZONE).date()
            if start <= day <= today:
                counts[day] += 1
        if len(events) < 100:
            break
    else:
        raise RuntimeError('Pagination limit reached; preserving the existing graph')
    if not counts:
        raise RuntimeError('Empty activity response; preserving the existing graph')

    first = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    colors = ['#ebedf0', '#d5dcff', '#9aaaff', '#6576dc', '#343568']
    total = sum(counts.values())
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="232" viewBox="0 0 900 232" role="img" aria-labelledby="title desc">',
             '<title id="title">GitLab activity — lihui</title>',
             f'<desc id="desc">{total} activity events in the past 365 days. Daily totals only; includes pushes, merge requests, issues and comments.</desc>',
             '<rect width="900" height="232" rx="12" fill="#ffffff" stroke="#d8dee4"/>',
             '<g font-family="Arial, sans-serif" fill="#24292f">',
             '<text x="24" y="30" font-size="18" font-weight="600">GitLab activity</text>',
             f'<text x="876" y="30" text-anchor="end" font-size="13">{total:,} events · {len(counts)} active days</text>']
    for row, label in [(1, 'Mon'), (3, 'Wed'), (5, 'Fri')]:
        parts.append(f'<text x="24" y="{77 + row * 15}" font-size="11" fill="#656d76">{label}</text>')
    for offset in range((today - first).days + 1):
        day = first + dt.timedelta(days=offset)
        col, row = divmod(offset, 7)
        x, y = 70 + col * 15, 65 + row * 15
        if day < start:
            continue
        if day.day == 1:
            parts.append(f'<text x="{x}" y="54" font-size="11" fill="#656d76">{day.strftime("%b")}</text>')
        n = counts[day]
        level = 0 if n == 0 else 1 if n <= 5 else 2 if n <= 15 else 3 if n <= 30 else 4
        parts.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" fill="{colors[level]}"><title>{day}: {n} events</title></rect>')
    parts.append(f'<text x="24" y="193" font-size="12" fill="#656d76">{start} — {today} · UTC+08:00 · Updated {today}</text>')
    parts.append('<text x="24" y="215" font-size="11" fill="#656d76">Pushes, merge requests, issues &amp; comments · Daily event totals, not commit counts</text>')
    parts.append('<text x="735" y="193" font-size="11" fill="#656d76">Less</text>')
    for i, color in enumerate(colors):
        parts.append(f'<rect x="{764 + i * 15}" y="182" width="12" height="12" rx="2" fill="{color}"/>')
    parts.extend(['<text x="846" y="193" font-size="11" fill="#656d76">More</text>', '</g></svg>'])
    target = ROOT / 'assets/gitlab-activity.svg'
    temp = target.with_suffix('.tmp')
    temp.write_text('\n'.join(parts) + '\n')
    temp.replace(target)
    print(f'Updated {target.name}: {total} events, {len(counts)} active days, {page} pages')


if __name__ == '__main__':
    main()
