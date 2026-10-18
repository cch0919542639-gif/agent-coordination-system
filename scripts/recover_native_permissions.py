"""Recover a stopped worker's temporary Antigravity grants without model calls."""
import json
from native_tools_worker import antigravity_grants

if __name__=='__main__':
    with antigravity_grants([],[],[]):
        pass
    print(json.dumps({'temporary_permissions':'recovered','workers_launched':0}))
