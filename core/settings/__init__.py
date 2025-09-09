from .base import *


if ENVIRONMENT == "development":
    from .dev import *
elif ENVIRONMENT == "production":
    from .prod import *
else:
    from .base import *