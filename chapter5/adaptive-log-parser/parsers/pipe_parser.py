import re

def parse(line: str) -> dict | None:
    pattern = r'^(?P<timestamp>\S+)\|(?P<level>\S+)\|(?P<module>\S+)\|step=(?P<step>\d+)\|(?P<message>.+)$'
    match = re.match(pattern, line.strip())
    if match:
        return match.groupdict()
    return None