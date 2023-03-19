"""
utilities i find useful to be used across multiple functions
"""

import sys
from datetime import timedelta

def gapFinder(thisDf,timeColumn='timestamp',Debug=False):
    #print(sys.modules)
    #if 'numpy' not in sys.modules:
    import numpy as np
    #if 'pandas' not in sys.modules:
    import pandas as pd
    if Debug:
        print('finding gaps')
    #find datagaps
    redDf = thisDf.copy()
    redDf.reset_index(inplace=True)
    redDf = redDf[[timeColumn]]
    redDf.drop_duplicates(subset=[timeColumn],inplace=True)
    redDf.sort_values(by=[timeColumn],inplace=True)
    deltas = redDf[timeColumn].diff()[1:]
    gaps = deltas[deltas > timedelta(days=1)]
    fGapDf = pd.DataFrame(gaps)
    fGapDf['endDate'] = redDf[timeColumn][gaps.index]
    fGapDf.rename(columns = {timeColumn:'gapDays'}, inplace=True)

    fGapDf['startDate'] = fGapDf['endDate']-fGapDf['gapDays']
    fGapDf = fGapDf[['startDate','gapDays']]
    return fGapDf