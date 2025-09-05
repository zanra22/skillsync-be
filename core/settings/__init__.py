import os
from dotenv import load_dotenv

load_dotenv()


environment = os.getenv("ENVIRONMENT")
print(f"Current Environment: {environment}")
if environment == "development":
    from .dev import *
elif environment == "production":
    from .prod import *
else:
    from .base import *
