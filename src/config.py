from datetime import datetime

# SEASON INFO
CURRENT_DATE = datetime.now()
CURRENT_YEAR = CURRENT_DATE.year
CURRENT_MONTH = CURRENT_DATE.month
SEASON = CURRENT_YEAR if CURRENT_MONTH >= 7 else CURRENT_YEAR - 1
WEEKS_TOTAL = 38