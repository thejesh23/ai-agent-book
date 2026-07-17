import re
from typing import Dict, Union

def parse(line: str) -> Union[Dict[str, str], None]:
    pattern = r'\[(?P<timestamp>.*?)\] \((?P<level>\w+)\) <tool=(?P<tool>.*?)> \{latency_ms=(?P<latency_ms>\d+) status=(?P<status>\w+)\} :: (?P<message>.*)'
    match = re.match(pattern, line.strip())
    
    if match:
        return {
            'timestamp': match.group('timestamp'),
            'level': match.group('level'),
            'tool': match.group('tool'),
            'message': match.group('message')
        }
    
    return None