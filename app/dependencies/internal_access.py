"""Just a simnple dependency for keeping access controlled until pub release """

import os 
from fastapi import Header, HTTPException, Depends

def internal_access(x_internal_key: str = Header(None)):
    if x_internal_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(
            status_code=403,
            detail="Access only to DEVS, Forbidden"
        )   
    

