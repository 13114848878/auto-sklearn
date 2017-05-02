# -*- encoding: utf-8 -*-
from autosklearn.util import dependencies
from autosklearn.__version__ import __version__


__MANDATORY_PACKAGES__ = '''
numpy>=1.9
scikit-learn==0.18.1
smac==0.4.0
lockfile>=0.10
ConfigSpace>=0.3.3,<0.4
pyrfr==0.2.0
xgboost==0.6a2
'''

dependencies.verify_packages(__MANDATORY_PACKAGES__)
